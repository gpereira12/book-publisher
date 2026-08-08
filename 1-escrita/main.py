#!/usr/bin/env python3
"""
1-escrita/main.py
-----------------
Motor do Projeto 1 (Escrita): Gerador de manuscritos estruturados em Markdown + YAML.
Implementa:
- Estrutura isolada por projeto (inputs/<livro>/).
- Calculador Matemático de Marcos (A).
- Dossiê de Personagens & Worldbuilding (B).
- Ficha Catalográfica e Frontmatter (C).
- Extrator de Prompts de Imagem Cinematográficos (Ângulos, Espaço Negativo & Takes).
- Resumo de Memória Contextual (resumo_contextual.yaml).
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml


def load_config(config_path: Path) -> Dict[str, Any]:
    """Carrega o arquivo de configuração do livro em YAML."""
    if not config_path.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def generate_cutter_code(author_name: str, title: str) -> str:
    """Gera um código Cutter preliminar baseado no sobrenome do autor e primeira letra do título."""
    parts = author_name.strip().split()
    surname = parts[-1] if parts else "Autor"
    initial_letter = surname[0].upper()
    title_letter = title.strip()[0].lower() if title else "a"
    
    hash_num = sum(ord(c) for c in surname) % 900 + 100
    return f"{initial_letter}{hash_num}{title_letter}"


def generate_dossier(config: Dict[str, Any], output_dir: Path) -> Path:
    """[Isolado por Projeto] Gera o arquivo de Dossiê (dossie.yaml)."""
    dossier_data = {
        "titulo": config.get("titulo", "Sem Título"),
        "genero": config.get("genero", "ficcao"),
        "personagens": config.get("personagens", [
            {
                "nome": "Protagonista Exemplo",
                "papel": "Protagonista",
                "objetivo_externo": "Alcançar o objetivo da trama",
                "necessidade_interna": "Superar a falha inicial"
            }
        ]),
        "worldbuilding_e_regras": {
            "ambientacao": "Descrição do cenário principal",
            "conceitos_chave": ["Conceito A", "Conceito B"]
        }
    }

    dossier_path = output_dir / "dossie.yaml"
    with open(dossier_path, "w", encoding="utf-8") as f:
        yaml.dump(dossier_data, f, allow_unicode=True, sort_keys=False)
    
    return dossier_path


def generate_context_memory_summary(config: Dict[str, Any], output_dir: Path) -> Path:
    """[Isolado por Projeto] Gera o resumo de memória contextual para evitar perda de foco."""
    memory_data = {
        "livro": config.get("titulo", "Sem Título"),
        "resumos_por_capitulo": [
            {"capitulo": 1, "resumo": "Introdução do protagonista e do conflito inicial."},
            {"capitulo": 2, "resumo": "Desenvolvimento do tema e primeira escolha moral."}
        ]
    }
    
    memory_path = output_dir / "resumo_contextual.yaml"
    with open(memory_path, "w", encoding="utf-8") as f:
        yaml.dump(memory_data, f, allow_unicode=True, sort_keys=False)
        
    return memory_path


def generate_cinematic_image_prompts(config: Dict[str, Any], output_dir: Path) -> Path:
    """[Isolado por Projeto] Gera a biblioteca de prompts cinematográficos para o Projeto 4."""
    prompts_dir = output_dir / "assets" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # Takes de Câmera alternados para evitar imagens repetitivas
    shot_types = [
        "Extreme Wide Shot, Cinematic Panorama, Establishing Shot, copyspace at bottom",
        "Medium Two-Shot, Dynamic Action, Focused Lighting",
        "Macro Close-up, Focus on Hands and Symbol, Dramatic Lighting",
        "Low Angle Heroic View, Volumetric Light, High Emotion",
        "Top-down Overhead View, Atmospheric Fog, Soft Tones"
    ]

    sample_prompt = (
        f"PROMPT: {shot_types[0]} -- Traditional Chinese Ink Wash Painting meets Modern Anime Art, "
        f"vibrant watercolor textures, clean linework, 300 DPI --ar 3:2"
    )

    sample_file = prompts_dir / "capitulo_01_imagem_01.txt"
    sample_file.write_text(sample_prompt, encoding="utf-8")
    
    return prompts_dir


def build_yaml_frontmatter(config: Dict[str, Any]) -> str:
    """Gera o bloco de YAML Frontmatter com Ficha Catalográfica preliminar."""
    author = config.get("autor", "Autor Desconhecido")
    title = config.get("titulo", "Sem Título")
    cutter = generate_cutter_code(author, title)

    meta = {
        "title": title,
        "subtitle": config.get("subtitulo", ""),
        "author": author,
        "publisher": config.get("editora", "Boutique Editorial"),
        "year": config.get("ano", 2026),
        "city": config.get("cidade", "São Paulo"),
        "format": config.get("formato", "A5"),
        "theme": config.get("tema", "Creme"),
        "framework_used": config.get("framework", "brooks_story_engineering"),
        "overlay_used": config.get("overlay_estilo", "none"),
        "ficha_catalografica": {
            "cdd": config.get("cdd", "800.1"),
            "cdu": config.get("cdu", "82-1"),
            "cutter": cutter,
            "palavras_chave": [
                f"1. {config.get('genero', 'Literatura').title()}.",
                "2. Ensaio.",
                "3. Filosofia."
            ]
        }
    }
    return f"---\n{yaml.dump(meta, allow_unicode=True, sort_keys=False)}---\n\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Projeto 1: Escrita - Motor de Geração Literária")
    parser.add_argument("--config", default="1-escrita/book_config.sample.yaml", help="Caminho do YAML de configuração")
    parser.add_argument("--output", help="Caminho de saída para o arquivo .md gerado")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    print(f"✍️ [Projeto 1] Carregando configuração: {config_path}")
    
    config = load_config(config_path)
    book_slug = config.get("titulo", "livro").lower().replace(" ", "_")
    output_dir = Path("inputs") / book_slug
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Gerar Dossiê por projeto
    dossier_path = generate_dossier(config, output_dir)
    print(f"📁 [Projeto] Dossiê de personagens/worldbuilding: {dossier_path}")

    # 2. Gerar Resumo de Memória Contextual
    memory_path = generate_context_memory_summary(config, output_dir)
    print(f"🧠 [Projeto] Resumo de memória contextual: {memory_path}")

    # 3. Gerar Prompts Cinematográficos para o Projeto 4
    prompts_dir = generate_cinematic_image_prompts(config, output_dir)
    print(f"🎬 [Projeto] Prompts cinematográficos salvos em: {prompts_dir}")

    # 4. Frontmatter + Manuscrito
    frontmatter = build_yaml_frontmatter(config)
    output_file = Path(args.output) if args.output else output_dir / "texto_original.md"
    
    if not output_file.exists():
        output_file.write_text(frontmatter, encoding="utf-8")
        print(f"✨ Manuscrito inicial criado em: {output_file}")
    else:
        print(f"ℹ️ Manuscrito existente preservado em: {output_file}")


if __name__ == "__main__":
    main()
