"""Preflight e preparação não destrutiva de ilustrações para impressão."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
from typing import Any, Iterable

from PIL import Image, ImageCms, ImageStat


MM_PER_INCH = 25.4
SUPPORTED_FORMATS = {"JPEG", "PNG", "TIFF"}
EXTENSIONS = {"JPEG": {".jpg", ".jpeg"}, "PNG": {".png"}, "TIFF": {".tif", ".tiff"}}


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    fixable: bool = False
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssetReport:
    scene_id: str
    path: str
    kind: str
    expected_px: tuple[int, int]
    expected_mm: tuple[float, float]
    exists: bool
    width_px: int | None = None
    height_px: int | None = None
    format: str | None = None
    mode: str | None = None
    effective_dpi_x: float | None = None
    effective_dpi_y: float | None = None
    has_icc_profile: bool | None = None
    center_seam_score: float | None = None
    issues: list[Issue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _srgb_profile_bytes() -> bytes:
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def _center_seam_score(image: Image.Image) -> float:
    """Mede uma linha fina na medianiz em relação à variação local.

    O detector apenas avisa. A remoção exige também autorização no manifesto,
    pois uma coluna arquitetônica verdadeira não pode ser apagada automaticamente.
    """
    gray = image.convert("L")
    width, height = gray.size
    if width < 32 or height < 32:
        return 0.0
    x = width // 2
    sample = gray.resize((width, min(height, 512)), Image.Resampling.BILINEAR)

    def delta(a: int, b: int) -> float:
        left = sample.crop((a, 0, a + 1, sample.height))
        right = sample.crop((b, 0, b + 1, sample.height))
        diff = Image.new("L", left.size)
        lp, rp, dp = left.load(), right.load(), diff.load()
        for y in range(sample.height):
            dp[0, y] = abs(lp[0, y] - rp[0, y])
        return ImageStat.Stat(diff).mean[0]

    center = (delta(x - 1, x) + delta(x, x + 1)) / 2
    local = (delta(x - 5, x - 4) + delta(x + 4, x + 5)) / 2
    return round(center / max(local, 0.75), 2)


def inspect_asset(
    scene_id: str,
    path: Path,
    kind: str,
    expected_px: tuple[int, int],
    expected_mm: tuple[float, float],
    seam_fix_authorized: bool = False,
) -> AssetReport:
    report = AssetReport(scene_id, str(path), kind, expected_px, expected_mm, path.exists())
    if not path.exists():
        report.issues.append(Issue("error", "missing_file", f"Arquivo não encontrado: {path}"))
        return report

    try:
        with Image.open(path) as image:
            width, height = image.size
            actual_format = image.format
            report.width_px, report.height_px = width, height
            report.format, report.mode = actual_format, image.mode
            report.has_icc_profile = bool(image.info.get("icc_profile"))
            report.effective_dpi_x = round(width / (expected_mm[0] / MM_PER_INCH), 1)
            report.effective_dpi_y = round(height / (expected_mm[1] / MM_PER_INCH), 1)
            report.center_seam_score = _center_seam_score(image) if kind == "spread" else None

            if actual_format not in SUPPORTED_FORMATS:
                report.issues.append(Issue("error", "unsupported_format", f"Formato {actual_format!r} não suportado"))
            elif path.suffix.lower() not in EXTENSIONS[actual_format]:
                report.issues.append(Issue(
                    "warning", "extension_format_mismatch",
                    f"A extensão {path.suffix} não corresponde ao conteúdo {actual_format}", True,
                ))

            if image.mode not in {"RGB", "CMYK"}:
                report.issues.append(Issue("warning", "unexpected_color_mode", f"Modo de cor {image.mode}; esperado RGB ou CMYK", True))
            if not report.has_icc_profile:
                report.issues.append(Issue("warning", "missing_icc_profile", "A imagem não possui perfil ICC incorporado", True))

            expected_ratio = expected_px[0] / expected_px[1]
            ratio_delta = abs((width / height) / expected_ratio - 1)
            if ratio_delta > 0.001:
                report.issues.append(Issue(
                    "warning", "aspect_ratio_adjustment",
                    f"A proporção exige reenquadramento de {ratio_delta * 100:.2f}% para o suporte final", True,
                    {"actual_ratio": round(width / height, 5), "expected_ratio": round(expected_ratio, 5)},
                ))

            if width < expected_px[0] or height < expected_px[1]:
                scale = max(expected_px[0] / width, expected_px[1] / height)
                report.issues.append(Issue(
                    "warning", "upscale_required",
                    f"Ampliação real de {scale:.3f}× necessária para {expected_px[0]} × {expected_px[1]} px", True,
                    {"scale": round(scale, 4)},
                ))
            elif (width, height) != expected_px:
                report.issues.append(Issue(
                    "info", "downscale_or_crop_required",
                    f"Reamostragem/recorte necessário para {expected_px[0]} × {expected_px[1]} px", True,
                ))

            if min(report.effective_dpi_x, report.effective_dpi_y) < 300:
                report.issues.append(Issue(
                    "warning", "below_300_effective_dpi",
                    f"Resolução efetiva mínima de {min(report.effective_dpi_x, report.effective_dpi_y):.1f} dpi; alvo: 300 dpi", True,
                ))

            if report.center_seam_score is not None and report.center_seam_score >= 1.8:
                report.issues.append(Issue(
                    "warning", "possible_center_seam",
                    f"Possível linha artificial na medianiz (índice {report.center_seam_score:.2f})",
                    seam_fix_authorized,
                    {"authorized_in_manifest": seam_fix_authorized},
                ))
    except OSError as exc:
        report.issues.append(Issue("error", "unreadable_image", str(exc)))
    return report


def _remove_center_seam(image: Image.Image, band_px: int = 3, sample_gap_px: int = 5) -> Image.Image:
    """Substitui apenas uma faixa central fina por interpolação lateral suave."""
    result = image.copy()
    width, height = result.size
    center = width // 2
    half = max(1, band_px // 2)
    left_x = max(0, center - sample_gap_px)
    right_x = min(width - 1, center + sample_gap_px)
    px = result.load()
    for y in range(height):
        left = px[left_x, y]
        right = px[right_x, y]
        for x in range(center - half, center + half + 1):
            t = (x - (center - half) + 1) / (2 * half + 2)
            px[x, y] = tuple(round((1 - t) * a + t * b) for a, b in zip(left, right))
    return result


def _cover_resize(image: Image.Image, expected_px: tuple[int, int]) -> Image.Image:
    target_w, target_h = expected_px
    scale = max(target_w / image.width, target_h / image.height)
    scaled = image.resize(
        (math.ceil(image.width * scale), math.ceil(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = max(0, (scaled.width - target_w) // 2)
    top = max(0, (scaled.height - target_h) // 2)
    return scaled.crop((left, top, left + target_w, top + target_h))


def prepare_asset(
    source: Path,
    destination: Path,
    backup_root: Path,
    expected_px: tuple[int, int],
    remove_center_seam: bool = False,
) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / source.name
    if not backup.exists():
        shutil.copy2(source, backup)

    with Image.open(source) as opened:
        image = opened.convert("RGB")
        if remove_center_seam:
            image = _remove_center_seam(image)
        image = _cover_resize(image, expected_px)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(
            destination,
            format="PNG",
            dpi=(300, 300),
            icc_profile=_srgb_profile_bytes(),
            optimize=True,
        )
    return destination


def report_payload(book: str, assets: Iterable[AssetReport]) -> dict[str, Any]:
    reports = list(assets)
    issues = [issue for asset in reports for issue in asset.issues]
    errors = sum(issue.severity == "error" for issue in issues)
    warnings = sum(issue.severity == "warning" for issue in issues)
    return {
        "book": book,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "passed_with_warnings" if warnings else "passed",
        "summary": {"errors": errors, "warnings": warnings, "assets": len(reports)},
        "assets": [asset.to_dict() for asset in reports],
    }


def save_report(payload: dict[str, Any], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
