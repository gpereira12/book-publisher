import tempfile
import unittest
from pathlib import Path

from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from image_preflight import inspect_asset, prepare_asset


class ImagePreflightTest(unittest.TestCase):
    def test_warns_before_fixing_small_unprofiled_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scene.png"
            Image.new("RGB", (100, 75), "white").save(path)
            report = inspect_asset("scene", path, "spread", (200, 145), (256, 186))
            codes = {issue.code for issue in report.issues}
            self.assertIn("upscale_required", codes)
            self.assertIn("missing_icc_profile", codes)
            with Image.open(path) as unchanged:
                self.assertEqual(unchanged.size, (100, 75))

    def test_prepare_preserves_original_and_writes_print_png(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "scene.jpg"
            destination = root / "scene.png"
            backup = root / "originals"
            Image.new("RGB", (120, 90), "#c9b28c").save(source, quality=90)
            prepare_asset(source, destination, backup, (200, 145))
            self.assertTrue(source.exists())
            self.assertTrue((backup / source.name).exists())
            with Image.open(destination) as image:
                self.assertEqual(image.size, (200, 145))
                self.assertEqual(image.format, "PNG")
                self.assertTrue(image.info.get("icc_profile"))
                self.assertAlmostEqual(image.info["dpi"][0], 300, delta=0.1)


if __name__ == "__main__":
    unittest.main()
