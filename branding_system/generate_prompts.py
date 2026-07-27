import json
import os

prompts_dir = "/Users/gabrielpereira/Desktop/Projetos/Livros/branding_system/prompts/"

# (day, theme, subject, is_saint)
themes = [
    (1, "A Fortaleza", "the Virgin Mary standing firm and tall in 'Stabat Mater' pose, representing the Pillar of Strength and maternal resolve", True),
    (2, "A Meditação", "a single lit beeswax candle inside a heavy iron holder resting on a dark rustic wooden table", False),
    (3, "Preparo da Oração", "the joined hands of Santa Teresa de Calcutá, wearing her iconic blue and white sari texture, in a moment of prayer", True),
    (4, "Devoção", "a sacred heart wrapped in a crown of thorns with a small, steady flame rising from the top", False),
    (5, "Adoração", "Santa Clara de Assis holding a minimalist golden Monstrance at a medieval stone gate", True),
    (6, "Recolhimento", "Conchita's 'Cela Interior': a simple wooden cross hanging on a rough wall next to a kitchen shelf", False),
    (7, "Atenção", "Santa Joana de Chantal's wooden desk with a stack of paper, a quill, and a brass nautical compass", True),
    (8, "Louvor por Fórmulas", "Santa Teresa d'Ávila's open ancient prayer book with 'Pai Nosso' in elegant calligraphy", True),
    (9, "Louvor pelo Canto", "Santa Teresinha's rustic laundry basket with white linens and a single red rose on top", True),
    (10, "Petição e Intercessão", "Santa Zélia Martin's lace bobbins (bilros) and a wooden rosary on a lace-covered table", True),
    (11, "Pilar do Jejum", "a simple, heavy wooden yoke (jugo) resting against a whitewashed stone wall", False),
    (12, "Abstinência de Conforto", "Santa Teresinha's simple wooden chair with no backrest standing on a cold stone floor", True),
    (13, "Abstinência de Descanso", "an hourglass with golden sand next to a small window where a rising sun is visible", False),
    (14, "Abstinência de Alimentos", "a simple hand-carved wooden bowl containing a single crust of dark bread", False),
    (15, "O Jejum Estrito", "a rustic stone water pitcher and a small whole wheat loaf of bread on a bare table", False),
    (16, "A Vigília", "an old iron lantern with a bright flame lighting up a dark navy blue corner", False),
    (17, "O Silêncio", "a finger over lips with an abandoned modern smartphone blurred in the background", False),
    (18, "O Retiro", "Santa Catarina de Sena's kitchen corner with a hidden crucifix among copper pots and pans", True),
    (19, "Pilar da Esmola", "an open weathered hand extending a glowing golden coin towards the viewer", False),
    (20, "Dar de Comer e Beber", "Santa Isabel da Hungria's woven basket with bread transforming into minimalist golden roses", True),
    (21, "Vestir os Nus", "a simple, clean tunic folded neatly on a rustic wooden bench in a humble room", False),
    (22, "Dar Pousada", "an open heavy wooden door at night with a warm, welcoming golden light glowing from inside", False),
    (23, "Visitar os Enfermos", "Santa Zélia Martin's hand holding a ceramic jar of holy oil near a bed with lace trim", True),
    (24, "Visitar os Presos", "Santa Francisca Romana leaving a pile of clothes to attend to a person in need", True),
    (25, "Remir os Cativos", "an empty iron cage with the door wide open and a white dove flying upwards", False),
    (26, "Sepultar os Mortos", "four small white lilies representing Santa Zélia's children in heaven, resting on a stone base", False),
    (27, "Dar Bom Conselho", "Santa Mônica's silhouette whispering words of wisdom to a sleeping child by a lamp", True),
    (28, "Ensinar os Ignorantes", "Santa Edith Stein's open philosophical book with a wooden cross as a bookmark", True),
    (29, "Corrigir os que Erram", "a shepherd's wooden crook (cajado) with a golden tip resting against a door", False),
    (30, "Consolar os Aflitos", "the large blue mantle of the Virgin Mary opened wide to offer refuge and peace", True),
    (31, "Perdoar as Ofensas", "a white dove being released from both palms into a bright, sunlit sky", False),
    (32, "Suportar com Paciência", "a figure carrying a heavy, rough-hewn wooden cross-beam across their shoulders", False),
    (33, "Rezar pelos Vivos e Mortos", "a star in the dark sky and a mound of earth, connected by a path of golden light", False)
]

base_prompt_template = (
    "Cinematic photorealistic image of {subject}. "
    "{halo}"
    "The scene is framed by an intricate, heavy carved gold and dark wood arabesque border as a core design element. "
    "The scene features dramatic lighting, 8k resolution, ultra-detailed textures, and a profound religious fine art atmosphere. "
    "The Alchemist style, focusing on authority, tradition, and rustic textures. "
    "At the bottom, a dark rustic wood texture plaque featuring the serif typography text 'Dia {day}: {theme}' engraved in gold. "
    "--ar 2:3 --v 6.0"
)

for day, theme, subject, is_saint in themes:
    halo_text = "The figure has a subtle, thin golden halo (aureola) glowing softly behind their head. " if is_saint else ""
    prompt_content = base_prompt_template.format(day=day, theme=theme, subject=subject, halo=halo_text)
    data = {
        "day": day,
        "theme": theme,
        "prompt": prompt_content,
        "metadata": {
            "archetype": "The Alchemist (Realistic)",
            "style": "Photorealistic Cinematic",
            "core_elements": ["Arabesque Frame", "Wood Title Plaque", "Halo" if is_saint else "Symbolic Object"]
        }
    }
    filename = f"day_{day:02d}.json"
    with open(os.path.join(prompts_dir, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Correctly regenerated 33 JSON files in {prompts_dir}")
