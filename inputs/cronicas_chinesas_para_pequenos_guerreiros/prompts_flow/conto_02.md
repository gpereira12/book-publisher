# Google Flow — Conto 2: A Espada que Permaneceu na Bainha

> Fonte estruturada: `conto_02.yaml`. Este pacote gera somente prompts; nenhuma arte é produzida pelo motor.

## Ordem de uso

1. Use a abertura aprovada do Conto 1, assets/interior/c01_s01_abertura.png, como ingrediente @Book_Style_Master. Ela fixa apenas pintura, textura, paleta, luz e acabamento; não reutilize Sai Weng nem os cavalos.
2. Se o Conto 2 estiver em outro projeto do Flow, envie também um spread aprovado do Conto 1 como segunda referência puramente estilística.
3. Gere e aprove @Han_Market_Style antes dos personagens; ele transporta a linguagem visual da coleção para o novo ambiente histórico.
4. Para criar @Han_Xin_Young, anexe somente @Han_Market_Style. Não anexe @Book_Style_Master nem qualquer personagem do Conto 1, pois essas referências podem contaminar rosto, cabelo e figurino.
5. Crie e aprove @Han_Xin_Young, @Market_Butcher e @Han_Xin_Sword antes das cenas da juventude.
6. Derive @Han_Xin_General de @Han_Xin_Young e @Butcher_Old de @Market_Butcher; não crie os personagens maduros do zero.
7. Gere a abertura e depois os três spreads no mesmo projeto, sempre anexando somente as referências citadas em cada prompt.
8. Após aprovar o spread do desafio, mantenha-o disponível como @C02_Challenge_Approved e anexe-o ao spread da humilhação somente como referência de eixo, posições relativas e direção de movimento.
9. Não anexe referências de personagens do Conto 1 às cenas do Conto 2.
10. Não peça ao Flow que desenhe título ou texto; o espaço editorial, o degradê e a tipografia pertencem ao Layout.
11. Exporte a melhor variação sem redimensionar nem recortar; o preflight posterior fará upscale, corte para sangria e conferência de coerência entre arte e texto.

## Prompts de referência

### style_bridge_market — Ponte de estilo — mercado da China antiga

- Tipo: `style_reference`
- Proporção sugerida: `4:3`
- Objetivo: Transportar exatamente o acabamento aprovado do Conto 1 para o ambiente do Conto 2, sem herdar seus personagens.
- Nome a cadastrar no Flow: `Han_Market_Style`

```text
Using @Book_Style_Master strictly as the collection's painting, paper texture, palette, lighting and finish reference, create a character-free environment reference for an early imperial Chinese market town. Do not reproduce, reinterpret or include Sai Weng, either horse or any other recognizable figure from the source image.

Show one coherent market street made of packed earth, timber stalls, woven-fiber awnings, rough plaster walls, wooden shutters, baskets, plain ceramics, rope, linen and aged bronze or iron tools. Include a modest butcher's stall as part of the environment, but no meat close-up, gore or prominent weapon. Use only a few tiny anonymous silhouettes in the far background so that no character identity is established.

Preserve the approved collection language: sophisticated digital gouache and watercolor on subtly textured paper, organic shapes, soft handcrafted edges, translucent washes, selective opaque brushwork, restrained detail, elegant silhouettes and poetic atmospheric depth. Maintain warm earth, aged parchment, charcoal, muted jade, dusty blue-gray, restrained mineral red and small touches of weathered gold. Use motivated late-morning light, colored shadows and a light dusty haze that unifies foreground, buildings and distant hills.

Make the setting historically plausible and visually specific without decorative clichés or a random mixture of dynasties. The environment must feel inhabited, tactile and continuous rather than like separate cutout elements. No main character, horse, readable signage, text, letters, calligraphy, logo, watermark, border, page mockup, anime, glossy 3D, photorealism, generic vector art, neon color, plastic or excessive micro-detail.
```

### character_han_xin_young — Ficha visual de Han Xin jovem

- Tipo: `character_reference`
- Proporção sugerida: `3:4`
- Objetivo: Fixar identidade, postura digna, roupas pobres e aparência do protagonista jovem.
- Nome a cadastrar no Flow: `Han_Xin_Young`

```text
Using @Han_Market_Style only as the exact painting, paper texture, palette and historical-material reference, design a completely new full-body character for young Han Xin on a plain warm parchment background. Do not use @Book_Style_Master or any previously created character as an identity reference. Han Xin must be immediately distinguishable from every young man created for the previous story. Show one person only in a relaxed three-quarter standing pose, with both hands visible and clear empty space around the silhouette.

Han Xin is approximately twenty-two years old, notably tall, long-limbed and lean, with narrow shoulders and wiry strength from disciplined training rather than farm labor or exaggerated muscle. Give him a distinctive long diamond-shaped face, pronounced high cheekbones, a narrower pointed chin, slightly hooded observant dark-brown eyes, long gently arched eyebrows and a prominent straight nose. His clean-shaven expression combines restraint, strategic intelligence, wounded pride and quiet inner fire. His posture is unusually erect and composed even though he is poor.

Create a hairstyle clearly different from a round high topknot: his black hair is center-parted, drawn tightly back along the temples and tied into a low compact knot at the nape, with one restrained loose strand beside the right cheek. This low silhouette must remain visible in later scenes.

Do not give him a blue tunic, brown sleeveless vest, loose brown cropped trousers or wrapped calves. Instead, dress him in one long, worn smoke-gray cross-collar robe reaching just below the knees, split subtly at the sides for movement, over a narrow desaturated celadon inner collar and straight charcoal trousers. Use a faded mineral-red cloth sash as his identifying color accent and plain dark cloth shoes. The robe is patched once near the lower left hem and lightly frayed, but clean. The long vertical robe, low hair knot and red sash must create a silhouette unique to Han Xin. He carries no jewelry, armor or aristocratic decoration. Do not include the sword in this character sheet; it will be supplied as a separate strict object reference.

Sophisticated children's editorial illustration, digital gouache and watercolor on textured paper, handcrafted edges, restrained detail and natural anatomy. Preserve this exact face, apparent age, hairstyle, body proportions, garments and colors in every youth scene.

No scenery, extra person, sword, horse, text, labels, calligraphy, decorative frame, photorealism, anime, glossy 3D, modern clothing, imperial costume or exaggerated heroic musculature. No high topknot, blue tunic, brown sleeveless vest, loose brown cropped trousers, wrapped calves, round face, broad farm-worker build or resemblance to a previously generated character.
```

### character_market_butcher — Ficha visual do açougueiro

- Tipo: `character_reference`
- Proporção sugerida: `3:4`
- Objetivo: Fixar o antagonista jovem sem caricatura, violência gráfica ou aparência genérica.
- Nome a cadastrar no Flow: `Market_Butcher`

```text
Using @Book_Style_Master and @Han_Market_Style only as exact style, palette and historical-material references, create one full-body character reference of the market butcher on a plain warm parchment background. Show one person only in a grounded three-quarter pose, with both hands visible and room around his silhouette.

He is approximately thirty-eight years old, exceptionally broad and powerful from physical labor, with thick forearms, a heavy neck and a stable stance. He has a square face, strong jaw, broad nose, heavy straight eyebrows, small dark watchful eyes, short black hair tied back and rough dark stubble. His expression conveys swagger, insecurity and habitual intimidation rather than monstrous evil.

He wears a rolled-sleeve rust-brown rough-linen tunic, dark umber trousers, a charcoal cloth belt, sturdy work shoes and a faded brown protective apron with subtle work wear. The apron may have restrained darkened marks from daily labor, but no wet blood or gore. He carries no weapon in the canonical sheet.

Sophisticated children's editorial illustration, digital gouache and watercolor on textured paper, soft handcrafted edges and anatomically natural hands. Preserve this exact face, build, hairstyle, apparent age, clothing and palette in all later appearances.

No scenery, extra person, knife, cleaver, meat, gore, text, labels, calligraphy, decorative frame, photorealism, anime, glossy 3D, fantasy-villain armor, caricature or grotesque anatomy.
```

### object_han_xin_sword — Espada antiga de Han Xin

- Tipo: `object_reference`
- Proporção sugerida: `3:4`
- Objetivo: Fixar a espada embainhada como símbolo narrativo e impedir variações de forma ou ornamento.
- Nome a cadastrar no Flow: `Han_Xin_Sword`

```text
Using @Book_Style_Master as the exact painting and material reference, create one clean object sheet of Han Xin's old Chinese straight double-edged jian, shown fully sheathed in three-quarter view on a plain warm parchment background. Include one small secondary detail view of the simple hilt only, without labels or diagram lines.

The sword has a worn dark-wood scabbard, restrained aged-bronze fittings, a plain oval guard, a wrapped charcoal-gray grip and a short muted red-brown cord. It is old, sharp and carefully maintained, valuable because of its craftsmanship rather than decoration. The design must be plausible for an early imperial Chinese setting, practical and austere, never magical or imperial.

Preserve the exact length, scabbard color, guard, grip and cord in every scene. The canonical state is fully sheathed. Sophisticated digital gouache and watercolor on textured paper, controlled highlights on aged metal and clear readable silhouette.

One sword only; no person, hand, scenery, readable marks, inscription, calligraphy, blood, floating blade, fantasy glow, jewel, ornate dragon decoration, text, logo, frame, photorealism, anime or glossy 3D.
```

### character_han_xin_general — Han Xin como grande general

- Tipo: `character_age_variant`
- Proporção sugerida: `3:4`
- Objetivo: Envelhecer o protagonista preservando sua identidade visual para o reencontro.
- Nome a cadastrar no Flow: `Han_Xin_General`

```text
Using @Han_Xin_Young as the strict identity reference and @Han_Market_Style as the exact illustration, paper texture and palette reference, create one full-body age-and-status variant of the same Han Xin on a plain warm parchment background. Use @Han_Xin_Sword as a strict object reference. He is now approximately thirty-four years old. This must be the same man, naturally aged by about twelve years, not a newly designed warrior.

Preserve the exact long diamond-shaped facial structure, pronounced high cheekbones, narrow pointed chin, slightly hooded dark-brown eyes, long gently arched eyebrows, prominent straight nose, hairline and clean-shaven identity of @Han_Xin_Young. Mature him only through a slightly firmer jaw, subtle lines beside the eyes and greater composure. Preserve his notably tall, lean, long-limbed silhouette and narrow shoulders; armor must not turn him into a broad or stocky man.

Preserve his canonical hairstyle exactly: black hair center-parted, drawn tightly back along the temples and tied into a low compact knot at the nape, with one restrained loose strand beside the right cheek. The low nape knot is an essential identity marker. Never give him a high topknot or change his hair silhouette.

His expression conveys strategic intelligence, earned authority and self-command rather than coldness. He wears historically plausible layered dark-charcoal and umber lamellar armor over a muted mineral-red under-robe, with aged-bronze fittings, a dark cloth belt and practical boots. The armor is refined but restrained, with no imperial crown, fantasy spikes or excessive ornament. Add @Han_Xin_Sword fully sheathed at his side, preserving its exact scabbard, fittings, grip and cord.

Show one person only in a calm three-quarter pose, both hands visible. Sophisticated children's editorial illustration, digital gouache and watercolor on textured paper, natural anatomy and restrained detail. Preserve this mature identity and costume for the final scene.

No scenery, soldiers, throne, extra person, text, labels, calligraphy, decorative frame, photorealism, anime, glossy 3D, fantasy armor, emperor costume, oversized weapon or aggressive battle pose. No high topknot, broad face, square jaw, shortened body, bulky heroic proportions, new facial identity or redesigned sword.
```

### character_butcher_old — Açougueiro envelhecido

- Tipo: `character_age_variant`
- Proporção sugerida: `3:4`
- Objetivo: Envelhecer o açougueiro sem perder a identificação com o antagonista do mercado.
- Nome a cadastrar no Flow: `Butcher_Old`

```text
Using @Market_Butcher as the strict identity reference and @Book_Style_Master as the exact illustration reference, create one full-body age variant of the same man on a plain warm parchment background. He is now approximately fifty-eight years old. Preserve the exact square facial structure, broad nose, eyebrow shape, eye color and general body proportions of @Market_Butcher. Age him naturally: gray at the temples, shorter gray-black stubble, deeper expression lines, slightly reduced bulk and a more guarded posture. Do not create a different person.

He now wears a plain faded umber cross-collar robe, charcoal trousers, a modest cloth belt and simple work shoes. His former swagger has softened into uncertainty and remorse. Show one person only in a neutral three-quarter standing pose with both hands visible; do not show him kneeling in the canonical sheet.

Sophisticated children's editorial illustration, digital gouache and watercolor on textured paper, soft handcrafted edges, restrained detail and natural anatomy. Preserve this identity, age and costume for the reunion scene.

No scenery, extra person, apron, weapon, meat, gore, text, labels, calligraphy, decorative frame, photorealism, anime, glossy 3D, grotesque aging or caricature.
```


## Prompts das cenas

### c02_s01_abertura_flow — Abertura — Han Xin atravessa o mercado

- Tipo: `chapter_opener`
- Proporção sugerida: `3:4`
- Objetivo: Apresentar Han Xin, sua pobreza digna e a espada ainda embainhada, com espaço editorial superior.
- Páginas: `13`
- Diagramação: Título e primeiro trecho no alto; arte narrativa nos 52–57% inferiores; preservar 5% para corte e sangria. Alvo final: 1547 × 2197 px a 300 dpi.

```text
Create a standalone vertical children's editorial illustration for the opening of a premium printed storybook chapter. Use @Book_Style_Master and @Han_Market_Style as strict references for painting, paper texture, palette, historical materials, atmosphere and finish. Use @Han_Xin_Young and @Han_Xin_Sword as strict identity and object references. Do not reproduce any character or horse from the previous chapter.

Young Han Xin walks diagonally through a busy early imperial Chinese market street. He is poor and plainly dressed, yet upright, observant and dignified. His old jian remains fully sheathed at his left waist, attached to his cloth belt through a historically plausible Han-era scabbard slide; the scabbard hangs low and angles gently backward along his left hip for a right-handed draw. It is clearly visible without becoming oversized. Merchants and townspeople move around him, some glancing at the sword and his unusual bearing. Hanging woven awnings lift gently in the breeze, loose fabric and dust catch the light and the market aisle leads toward distant hazy roofs. The moment should feel alive and anticipatory, as if the crowd is flowing around one still inner center.

Compose for a right-hand chapter-opening page with a 50 mm visual feeling, child-eye-level camera, three-quarter environmental portrait and three clear depth planes. Keep Han Xin moving rather than posing frontally. Place him below and slightly off center, with his face, both hands and sword fittings away from the page edges. Concentrate important narrative content within the lower 52–57% of the canvas.

Keep the upper 38–43% pale, calm and low-detail for the chapter title and opening text. Build that space from light awning fabric, warm atmospheric sky and subtle paper texture; keep it free from faces, signs, roof peaks, weapons and high-contrast clouds. Allow a natural soft transition into the illustration, not a hard digital gradient. Preserve at least 5% crop tolerance on every outer edge for bleed and final aspect adjustment.

Motivated late-morning light enters from one side and consistently illuminates Han Xin, people, dust and architecture. Use restrained warm earth, parchment, charcoal, muted indigo, jade and dusty blue-gray. The protagonist, crowd and setting must share the same brushwork, edge softness, light direction and atmospheric depth; no pasted-on character effect.

No generated text, title, letters, calligraphy, readable signs, page number, logo, watermark, border or page mockup. No drawn gradient, anime, photorealism, glossy 3D, generic vector style, modern objects, frozen lineup, duplicated people, malformed hands, unsheathed blade, sword across the back or over the shoulder, or important detail near the trim edges.
```

### c02_s02_desafio_flow — Spread 1 — o desafio no mercado

- Tipo: `spread`
- Proporção sugerida: `4:3`
- Objetivo: Encenar a ameaça e o instante de escolha antes de Han Xin soltar o punho da espada.
- Páginas: `14, 15`
- Diagramação: Confronto em diagonal; rostos e punho fora da medianiz; texto nas áreas superiores externas. Alvo final: 3024 × 2197 px a 300 dpi.

```text
Create one continuous landscape double-page children's editorial illustration. Use @Book_Style_Master and @Han_Market_Style as strict style and environment references. Use @Han_Xin_Young, @Market_Butcher and @Han_Xin_Sword as strict identity and object references. Preserve every canonical face, body proportion, garment color and sword detail.

In the same market street, the massive butcher steps across Han Xin's path and blocks it with a wide, intimidating stance. He leans forward and points down between his separated feet, issuing a cruel public challenge. Han Xin stands at a tense diagonal opposite him. His jian remains attached at his left waist through a Han-era scabbard slide, hanging low and angled gently backward. His right hand grips the hilt so firmly that the fingers whiten while the blade remains completely inside the scabbard; his other hand remains controlled at his side. His face shows anger, calculation and the exact instant before self-command wins. A curved ring of market witnesses recoils and leans inward, creating social pressure without turning into a static lineup.

Use a cinematic 35 mm visual feeling from a low but respectful three-quarter angle near the edge of the crowd. Let the butcher dominate the near right plane without appearing monstrous; let Han Xin occupy the left-middle plane with a clear readable face. Use the aisle, awning ropes, pointing arm and crowd eyelines as converging diagonals. Add motivated movement through a shifting apron, lifted awning edges, interrupted foot traffic and a small swirl of dust. Avoid frontal symmetry and theatrical posing.

Protect the middle 12% gutter zone: no face, pointing hand, sword hilt, blade, feet or essential gesture may cross it. Reserve low-detail text-safe regions in the upper outer left awnings and the upper outer right plaster wall or pale sky. Keep those regions free from heads, signs, ropes and strong shadows. Preserve at least 5% crop tolerance around all outer edges for bleed and final aspect adjustment.

Use consistent late-morning directional light so the crowd, protagonists and architecture belong to one continuous space. Sophisticated digital gouache and watercolor on textured paper, handcrafted edges, selective focus through detail hierarchy and emotionally clear gestures.

No generated text, calligraphy, readable signs, border, visible page division, page mockup, blood, gore, drawn sword, detached scabbard, sword across the back or over the shoulder, attack, slapstick, sexualized framing, voyeuristic angle, anime, photorealism, glossy 3D, modern objects, duplicated figures, malformed hands or essential content in the gutter.
```

### c02_s03_humilhacao_flow — Spread 2 — o preço da escolha

- Tipo: `spread`
- Proporção sugerida: `4:3`
- Objetivo: Mostrar o instante posterior à passagem, concentrando-se no custo emocional do autocontrole em vez da mecânica humilhante da ação.
- Páginas: `16, 17`
- Diagramação: Plano lateral baixo e mais fechado; Han Xin e o açougueiro formam um único núcleo próximo no terço direito, separados por menos de meio corpo; Han ainda com uma mão e um joelho no chão e avançando para a direita; multidão dispersa à esquerda; somente os 12% centrais ficam livres para a medianiz. Alvo final: 3024 × 2197 px a 300 dpi.

```text
Create one continuous landscape double-page children's editorial illustration. Use @Book_Style_Master and @Han_Market_Style as strict references for the approved watercolor-gouache painting language, paper texture, palette, architecture and historical materials. Use @Han_Xin_Young, @Market_Butcher and @Han_Xin_Sword as strict identity and object references. Use @C02_Challenge_Approved only to preserve the established camera axis and Han Xin's left-to-right direction of travel. Do not copy its staging.

Show the quiet but emotionally charged fraction of a second as Han Xin finishes emerging from the butcher's stance. Do not show a frontal or vulgar view beneath the body. Han Xin's head, shoulders, hands and leading knee have cleared the butcher and continue toward the right outer edge, while his trailing lower leg and robe hem remain immediately beside the butcher's boots, completing the exit. He remains very low: one knee and one open hand still touch the dusty ground while the other foot plants forward and his torso begins to rise. His red sash trails behind him, and a compact wake of displaced dust records his movement from left to right.

Place Han Xin large in the foreground of the right page, seen in a low lateral three-quarter profile from near ground level. His head, chest, planted foot and intended path all point toward the right. His face must communicate the cost of the choice: lowered eyes, clenched jaw, tight brow, controlled breathing, wounded dignity and anger held firmly inside. He is neither defeated nor victorious. He must not smile, pose heroically, look relaxed, stare proudly upward or make eye contact with the crowd.

Immediately behind him and slightly to the left, still entirely on the right page, the butcher stands with his boots apart. Keep both men inside one compact action cluster: the butcher's nearest boot is only a handspan behind Han Xin's trailing knee, and the visual gap between their bodies is less than half a body width. Do not place the butcher several meters away or reduce him to a background figure. Show his full recognizable face above Han Xin, wearing a small self-satisfied smirk and relaxed superiority because he falsely believes he has won. Avoid a theatrical laugh, pointing gesture, crossed-arm victory pose or confused expression. His presence should feel physically close and heavy but emotionally secondary to Han Xin's interior struggle.

Keep @Han_Xin_Sword completely sheathed and attached to the belt through its Han-era scabbard slide, shifted toward the rear of Han Xin's left hip. It follows the line of his body and movement without touching the gutter or appearing strapped to his shoulder. The blade is never visible.

On the left page, scatter a small group of witnesses at different depths instead of arranging them as a semicircle or audience lineup. Two people laugh and point with restrained gestures, one watches uncomfortably without laughing, and others turn from their market tasks. Use overlapping bodies, partial foreground shoulders and varied attention to make the street feel caught in a real moment rather than staged for a performance.

Keep only the central 12% of the canvas clear as a narrow gutter-safe strip of pale market road and dust. Do not expand this into a broad empty avenue or use it to push the protagonists toward the distant edge. No face, hand, foot, sword, pointing gesture or essential narrative detail may enter this narrow strip. Maintain the same side of the cinematic axis as @C02_Challenge_Approved: Han Xin entered from the left and must continue unmistakably toward the right.

Use a tighter cinematic 50 mm visual feeling from a camera approximately forty centimeters above the ground. The Han Xin-and-butcher action cluster should fill roughly 40–45% of the total canvas width on the right page, large enough for both facial expressions and Han Xin's grounded hand to remain legible in print. The witnesses occupy the left page at a smaller but still readable scale, with only the narrow gutter strip between the groups. A band of motivated late-morning light falls immediately ahead of Han Xin while the space behind him remains slightly cooler, suggesting movement from public humiliation toward an unknown future without becoming symbolic fantasy. Use detail hierarchy and atmospheric softness, not photographic blur.

Reserve a naturally pale low-detail facade and awning area in the upper outer left page for editable text. Reserve a second calm area of pale plaster and atmospheric sky in the upper outer right page, above the characters, for another text block. These must be organic parts of the painting, never white rectangles, panels or digital gradients. Preserve at least 5% crop tolerance around every outer edge for bleed and final aspect adjustment.

Sophisticated children's editorial illustration, digital gouache and watercolor on subtly textured paper, handcrafted edges, restrained warm earth, smoke gray, celadon, mineral red and dusty blue-gray palette, consistent directional light and emotionally precise natural gestures.

No generated text, calligraphy, readable signs, border, visible page division, page mockup, literal frontal under-the-legs view, crotch emphasis, centered protagonists, broad empty avenue, large physical separation between Han Xin and the butcher, distant or tiny butcher, Han Xin moving or looking left, camera-axis reversal, smiling or heroic Han Xin, confused butcher, broad theatrical grin, audience lineup, synchronized laughter, slapstick, gore, exposed blade, sword on the back, fantasy symbolism, anime, photorealism, glossy 3D, modern objects, malformed hands or essential content in the gutter.
```

### c02_s04_reencontro_flow — Spread 3 — o general oferece a mão

- Tipo: `spread`
- Proporção sugerida: `4:3`
- Objetivo: Resolver a história com perdão, autocontrole e inversão visual do antigo desequilíbrio de poder.
- Páginas: `18, 19`
- Diagramação: Han Xin desce em diagonal e oferece a mão; mãos e rostos fora da medianiz; texto em parede iluminada e piso externo. Alvo final: 3024 × 2197 px a 300 dpi.

```text
Create one continuous landscape double-page children's editorial illustration. Use @Book_Style_Master as the exact collection style and use the approved Conto 2 images as continuity references for brushwork, palette and facial identity. Use @Han_Xin_General, @Butcher_Old and @Han_Xin_Sword as strict identity and object references. Han Xin and the older butcher must be unmistakably the naturally aged versions of the two men from the market scenes.

Years later, inside a restrained military audience courtyard or open timber command hall, the celebrated general Han Xin steps down from a low platform and reaches out to the older butcher, who kneels anxiously before him. Han Xin's open hand offers help rather than punishment. His face is calm and humane, with no triumph. The butcher looks upward in disbelief, remorse and relief. A small formation of soldiers and attendants watches silently from the middle distance, their disciplined stillness contrasting with Han Xin's gentle forward movement.

Use a cinematic 50 mm visual feeling from a slightly elevated three-quarter viewpoint. Build a diagonal from the low platform through Han Xin's descending step to the offered hand and the butcher's upward gaze. Echo the earlier imbalance of height without repeating or humiliating the old composition: the emotional climax is the instant equality is restored. Use moving robe hems, Han Xin's shifted weight, the butcher beginning to rise and a narrow shaft of warm light to keep the scene alive. Avoid a frontal ceremonial lineup.

Keep both faces, the offered and receiving hands, knees, sword and platform edge outside the middle 12% gutter zone. Reserve a broad softly illuminated plaster-wall area on one outer page and a calm low-detail floor or open-air haze area on the opposite outer page for editable text. Preserve at least 5% crop tolerance on all outer edges for bleed and final aspect adjustment.

Use one motivated late-afternoon light source with warm highlights and muted cool shadows across every figure and architectural surface. The characters and environment must share identical paper texture, edge treatment and atmospheric depth. Sophisticated digital gouache and watercolor, restrained historical materials and child-accessible emotional clarity.

No generated text, calligraphy, readable banners, logo, watermark, border, visible page division, page mockup, execution scene, threat, drawn sword, emperor throne, fantasy palace, gloating pose, excessive kneeling humiliation, anime, photorealism, glossy 3D, modern military objects, pasted-on figures, duplicated soldiers, malformed hands or essential content in the gutter.
```
