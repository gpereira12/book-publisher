# Google Flow — Conto 4: O General e a Chama da Última Alvorada

> Fonte estruturada: `conto_04.yaml`. Este pacote gera somente prompts; nenhuma arte é produzida pelo motor.

## Ordem de uso

1. Use uma arte aprovada do Conto 1, 2 ou 3 como @Book_Style_Master. Ela fixa somente a técnica pictórica (guache digital/aquarela sobre papel texturizado), acabamento editorial e atmosfera cromática geral; não transporte rostos, trajes ou cenários específicos de outros contos.
2. Gere e aprove primeiro @Northern_Mountain_Pass_Style, sem personagens. Ele estabelece o desfiladeiro nevado, a rocha escarpada, os pinheiros de montanha e o vilarejo distante no vale sob o céu noturno e a alvorada.
3. Crie @General_Wen anexando somente @Northern_Mountain_Pass_Style. Defina sua identidade de guerreiro maduro, armadura de batalha funcional, lança chinesa (qiang) e porte nobre e protetor.
4. Crie @Zhang_Immortal anexando @Northern_Mountain_Pass_Style. Garanta a aparência predatória, pele de porcelana imaculada, cabelos negros longos, manto de seda fluida e o frasco de jade translúcido.
5. Crie @Wen_Old_Master anexando @Northern_Mountain_Pass_Style para fixar a fisionomia acolhedora e venerável do mestre de artes marciais para a visão do último spread.
6. Gere a abertura e os três spreads previstos no mesmo projeto do Flow, anexando em cada cena as referências de estilo e personagens indicadas.
7. Depois de aprovar a abertura, mantenha-a como @C04_Opener_Approved para reforçar a consistência de armadura, rosto, ferimentos e iluminação noturna.
8. Depois de aprovar o primeiro spread, mantenha-o como @C04_Elixir_Approved para assegurar a continuidade espacial do passo e do frasco de jade.
9. Não solicite ao motor que gere títulos, textos, legendas, onomatopeias, números de página ou degradês artificiais. As áreas seguras de texto devem ser compostas por elementos naturais da pintura (céu, névoa, neve suave).
10. Exporte na resolução máxima nativa sem corte. O pipeline de preflight aplicará sangria de 3 mm, corte e verificação da medianiz (gutter 12%).

---

## Prompts de referência

### style_bridge_mountain_pass — Ponte de estilo — Passo da Montanha Gelada do Norte

- Tipo: `style_reference`
- Proporção sugerida: `4:3`
- Objetivo: Fixar a cenografia de montanhas escarpadas, neve, rochas de ardósia, pinheiros retorcidos e o vale protegido, sem personagens.
- Nome a cadastrar no Flow: `Northern_Mountain_Pass_Style`

```text
Using @Book_Style_Master strictly as the collection's painting technique, paper texture, lighting quality and finish reference, create a character-free environment reference for a high mountain pass in ancient northern China. Do not reproduce, reinterpret or include any recognizable person, horse, market, rice paddy or building from previous stories.

Show one cohesive mountain landscape: a narrow stony pass between towering dark slate cliffs covered with fresh snow drifts, ancient twisted pine trees clinging to frozen rock faces, scattered boulders and gravel, whistling winter mist, and a breathtaking overlook gazing down into a distant sheltered valley below where tiny rooftops and faint chimney smoke of a peaceful village can be glimpsed. Include transitions between deep indigo night with crisp starlight and the warm amber promise of early dawn. Keep the geography austere, ancient, strategic and atmospheric. No high-tech structures, grand castles or fantasy clichés. Include no main characters and no distracting foreground objects.

Preserve the approved collection language: sophisticated children's editorial illustration, digital gouache and watercolor on subtly textured paper, organic shapes, soft handcrafted edges, translucent washes, selective opaque brushwork, restrained detail, elegant silhouettes and poetic atmospheric depth. Use a palette of midnight indigo, charcoal slate, cold misty blue, crisp chalk-white snow, weathered stone, muted jade and accents of warm amber-gold light.

Design the landscape so it supports both vertical chapter opening composition and wide horizontal double-page spreads. Include calm low-detail areas in the snowy terrain, cloudy skies and distant mist suitable for future typography. No text, letters, calligraphy, signs, logo, watermark, border, page mockup, visible fold, photorealism, anime, glossy 3D, neon color or excessive digital noise.
```

---

### character_general_wen — Ficha visual do General Wen

- Tipo: `character_reference`
- Proporção sugerida: `3:4`
- Objetivo: Fixar a identidade heróica, nobre e calejada do General Wen, seu traje militar e sua lança de combate.
- Nome a cadastrar no Flow: `General_Wen`

```text
Using @Northern_Mountain_Pass_Style only as the exact painting, paper texture, palette and historical-material reference, design a completely new full-body character reference for General Wen on a plain warm parchment background. Do not use any character from previous stories. Show one person only in a dignified three-quarter standing martial stance with both hands visible and clear empty space around his silhouette.

Wen is a seasoned military commander in his mid-forties, tall, broad-shouldered and physically powerful, bearing the calm dignity of a devoted protector. Give him a strong angular jaw, prominent cheekbones, deeply set dark brown eyes filled with resolve and quiet nobility, and slight weathering and faint battle marks on his tan skin without grotesque injury. He is clean-shaven except for short neatly kept warrior stubble. His coarse black hair has early silver streaks at the temples and is tied up into a strict military warrior topknot secured with an unpolished bronze pin.

Dress him in authentic ancient Chinese lamellar armor: dark lacquered leather and weathered iron plates over a heavy desaturated mineral-red cross-collar tunic, worn charcoal-gray trousers, leather forearm bracers with metal studs, and sturdy cold-weather studded boots. A weathered smoke-gray wool travel cloak is clasped at his shoulders and draped back. In his right hand, he holds a traditional Chinese spear (qiang) with a solid dark oak shaft, a hand-forged steel spearhead showing battle nicks, and a faded red horsehair tassel at the collar.

Sophisticated children's editorial illustration, digital gouache and watercolor on textured paper, handcrafted edges, restrained detail, natural heroic anatomy and historically grounded materials. Preserve this exact face, age, armor, spear design and color scheme across all scenes.

No scenery, extra person, shield, helmet, fantasy glowing spikes, modern military uniform, anime aesthetic, glossy 3D, comic caricature, grotesque gore or facial resemblance to previous story characters.
```

---

### character_zhang_immortal — Ficha visual de Zhang, o Imortal

- Tipo: `character_reference`
- Proporção sugerida: `3:4`
- Objetivo: Fixar a identidade etérea, predatória e imaculada de Zhang, o Imortal, seu manto de seda e o frasco de jade.
- Nome a cadastrar no Flow: `Zhang_Immortal`

```text
Using @Northern_Mountain_Pass_Style only as the exact painting, paper texture, palette and historical-material reference, design a completely new full-body character reference for Zhang the Immortal on a plain warm parchment background. Show one person only in an elegant, predatory three-quarter standing posture with both hands visible.

Zhang possesses an ageless appearance frozen around twenty-eight years old, slender and graceful with unnervingly flawless porcelain-white skin without a single blemish, scar or trace of exhaustion. He has refined aristocratic features: sharp high cheekbones, thin pale lips curved into a faint calculating smile, and piercing cold dark eyes that reflect predatory fascination rather than brute malice. His waist-length, jet-black hair is glossy and immaculate, partially flowing freely in the wind and partially held by a minimalist dark jade hairpin.

Dress him in an exquisite layered robe of midnight-indigo and deep teal fine silk with subtle desaturated silver embroidery along the lapels, completely untouched by dirt or snow. A dark silk sash with an uncarved nephrite jade ring hangs at his waist. In one elegant hand, he holds a small, carved translucent pale-celadon jade flask that emits a faint, cool lunar glow.

Sophisticated children's editorial illustration, digital gouache and watercolor on textured paper, handcrafted edges, refined anatomy, poetic and mysterious presence. Preserve this exact face, hair, immaculate dark robes and jade flask design in all scenes.

No scenery, extra person, monster features, demonic horns, wings, fiery neon effects, western fantasy wizard robes, grotesque horror, anime styling or 3D render look.
```

---

### character_master_spirit — Ficha visual do Velho Mestre de Wen

- Tipo: `character_reference`
- Proporção sugerida: `3:4`
- Objetivo: Fixar a identidade do sábio e acolhedor mestre de artes marciais para a visão do clímax na alvorada.
- Nome a cadastrar no Flow: `Wen_Old_Master`

```text
Using @Northern_Mountain_Pass_Style as the illustration, paper texture and palette reference, design a full-body character reference for General Wen's deceased martial arts Master on a plain warm parchment background. Show one person in a gentle, poised three-quarter stance with a welcoming presence.

The Master is an ancient martial sage around seventy-two years old, with a kind, deeply lined face, warm crinkling dark eyes full of paternal pride and wisdom, and a short neat white beard and mustache. His snow-white hair is tied in a simple traditional topknot. He radiates serenity, mastery and profound warmth.

Dress him in humble, well-worn traditional martial robes of undyed raw cotton and muted ochre, bound by a simple woven hemp sash and cloth slippers. His hands are weathered and strong, held in a relaxed, open gesture of blessing and pride.

Sophisticated children's editorial illustration, digital gouache and watercolor on textured paper, soft edges, ethereal warmth. Preserve this exact face, expression and humble attire for his spiritual manifestation.

No scenery, weapon, aggressive martial arts pose, opulent silk, decorative fantasy halos, caricature, anime or 3D CGI.
```

---

## Prompts das cenas

### c04_s01_abertura_flow — Abertura — O Guardião do Passo e a Sombra Imortal

- Tipo: `chapter_opener`
- Proporção sugerida: `3:4`
- Objetivo: Apresentar o General Wen exausto mas inabalável no passo gelado e Zhang surgindo da névoa noturna, reservando o topo para título e texto.
- Páginas: `29`
- Diagramação: Título do capítulo e abertura no terço superior (38–42%); Wen no terço inferior direito; Zhang à meia distância no terço médio esquerdo; margem de 5% para corte e sangria. Alvo: 1547 × 2197 px a 300 dpi.

```text
Create a standalone vertical children's editorial illustration for the chapter opening of a premium printed storybook. Use @Northern_Mountain_Pass_Style as the strict environment, painting technique, paper texture and color palette reference. Use @General_Wen as the strict character reference for Wen, and @Zhang_Immortal as the strict reference for Zhang. If available, use @Book_Style_Master only to confirm the collection's artistic finish.

On a bitterly cold, wind-swept mountain pass at deep midnight, General Wen stands as an unyielding sentinel guarding the rocky threshold. Exhausted after three sleepless nights of battle, his breath steaming into the icy air and blood faintly dried along a cut on his forehead, Wen grips his traditional spear firmly with both hands, grounded in a defensive stance. In the mid-ground across the snowy pass, emerging silently from the swirling nocturnal mist and dark rocky shadows, appears Zhang the Immortal—graceful, upright, and clad in immaculate midnight-indigo silk without a speck of snow. In the far distance below the precipice, warm faint points of chimney smoke and lanterns from the sheltered village are visible.

Compose for a right-hand chapter-opening page with a 50 mm lens feel and clear three-plane depth. Position General Wen in the lower-right third, large enough to read his fatigue and fierce determination. Keep his face, spearhead, and body safely clear of outer trim margins. Position Zhang in the middle-left ground, creating a tense diagonal eye-line between them.

Keep the upper 38–42% calm, soft, and low-detail for the future chapter title and opening text, constructed naturally from deep midnight indigo sky, mountain mist, and distant snowy peaks without artificial blocks or hard gradients. Reserve at least 5% crop tolerance on all edges for bleed.

Use cool moonlit blue-gray light with sharp rim highlights on the snow and armor, contrasted with the subtle warm glow of the distant village below. Ensure unified digital gouache and watercolor brushwork on textured paper.

No generated text, title, letters, calligraphy, page numbers, border, page mockup, photorealism, anime, 3D render, modern weaponry, glowing magic circles or essential details at the bleed edges.
```

---

### c04_s02_elixir_flow — Spread 1 — A Oferta do Elixir de Jade

- Tipo: `spread`
- Proporção sugerida: `4:3`
- Objetivo: Dramatizar o dilema moral entre a promessa egoísta de imortalidade e o dever sacrificial de proteger a aldeia.
- Páginas: `30, 31`
- Diagramação: Zhang na página esquerda estendendo o frasco; Wen na página direita ajoelhado na neve olhando para a aldeia abaixo; medianiz de 12% livre de mãos, rostos e frasco. Alvo: 3024 × 2197 px a 300 dpi.

```text
Create one continuous horizontal double-page children's editorial illustration. Use @Northern_Mountain_Pass_Style as the strict environment and style reference, @General_Wen and @Zhang_Immortal as strict character references, and @C04_Opener_Approved for costume, lighting, and battle-worn details.

Under the pale midnight moon on the mountain pass, Zhang the Immortal stands on the outer left page, poised and tempting, with one arm extended forward offering a small, luminous carved jade flask on his open palm. The flask casts a soft, eerie moonlit emerald glow across his porcelain face and silk sleeve. On the outer right page, General Wen is momentarily brought down to one knee upon the snow, bracing himself on his spear shaft. His body aches with exhaustion and cracked armor, but his head turns away from the tempting flask to gaze tenderly down at the valley below, where the humble lights and cozy chimney smoke of the sleeping village shine in the dark.

Cinematic 35–40 mm lens feel from a grounded viewpoint. Zhang commands the left page while Wen anchors the right page, establishing an emotionally charged psychological tension across the spread. Let the snowy ground, mountain ridge, and sweeping wind lines guide the reader's eye naturally from left to right.

Strictly protect the central 12% gutter zone: only continuous snow drifts, distant misty mountain ridges, and dark textured rock may cross the book fold. No face, hand, spearhead, jade flask, or key gesture may touch the center fold. Reserve a calm low-detail text area in the upper night sky on the left page and another in the soft snowy slope or valley mist on the lower right page. Preserve at least 5% crop tolerance on all outer edges.

Lighting balances cold moonlit cyan and deep indigo on the left with subtle warm golden tones rising from the distant village on the right. Maintain sophisticated watercolor-gouache texture, soft edges, and atmospheric perspective.

No generated text, calligraphy, page numbers, border, visible page seam, text panel overlay, centered characters in the gutter, anime tropes, glowing magical lasers, gore, photorealism or 3D CGI.
```

---

### c04_s03_batalha_flow — Spread 2 — A Alma em Chamas e a Lança Partida

- Tipo: `spread`
- Proporção sugerida: `4:3`
- Objetivo: Expressar o clímax do combate sacrificial: a manifestação da aura dourada de Wen, a quebra da lança e a luta implacável com punhos nus.
- Páginas: `32, 33`
- Diagramação: Wen com aura dourada avançando da direita; Zhang esquivando veloz à esquerda; ponta da lança quebrada na neve em primeiro plano; medianiz de 12% livre de corpos e golpes. Alvo: 3024 × 2197 px a 300 dpi.

```text
Create one continuous horizontal double-page children's editorial illustration capturing the intense climax of the battle in the dead of night. Use @Northern_Mountain_Pass_Style and @C04_Elixir_Approved as strict environment, style, and character consistency references.

In the frozen mountain pass, the battle has reached its peak. General Wen, pushing past mortal exhaustion, ignites his soul with an inner spiritual fire: a radiant, warm golden-amber aura emanates from his body, melting the frost beneath his boots and casting brilliant solar warmth across the snow. His spear shaft has shattered against Zhang's lightning speed—the broken spearhead lies embedded in the foreground snow—yet Wen charges fiercely forward with bare clenched fists in a master martial arts strike. On the left page, Zhang the Immortal recoils with wide, startled eyes and billowing indigo robes, caught off-guard by the sheer heat and unyielding courage of the human general. Golden embers, flying snow crystals, and wind ribbons swirl dynamically between them.

Use a dynamic 35 mm low-angle action framing. Wen powers the outer right page moving forcefully leftward; Zhang reacts on the outer left page. The collision of hot golden light and freezing midnight mist creates high-contrast compositional vectors that propel the narrative without chaos.

Protect the central 12% gutter zone: only sweeping trails of wind, drifting sparks, and blurred snow particles may cross the center fold. Both warriors, their faces, hands, and impact points must remain completely outside the central gutter. Reserve organic low-detail text-safe areas in the dark stormy sky at the upper left and the snowbank at the lower right. Preserve 5% crop tolerance on outer borders.

Color palette dramatizes the clash between cold midnight slate/indigo and radiant solar gold/mineral amber. Digital gouache and watercolor on textured paper with handcrafted dry-brush energy and poetic fluidity.

No generated text, calligraphy, page numbers, comic speed lines, western magic circles, fireballs, blood/gore, superhero costumes, anime styling, 3D rendering or essential elements across the fold.
```

---

### c04_s04_alvorada_flow — Spread 3 — A Última Alvorada e a Presença do Mestre

- Tipo: `spread`
- Proporção sugerida: `4:3`
- Objetivo: Resolver a história com a fuga de Zhang nas sombras, a postura triunfante de Wen banhada pela alvorada e a visão serena de seu velho mestre.
- Páginas: `34, 35`
- Diagramação: Zhang recuando para as cavernas à esquerda; Wen de pé em guarda na alvorada à direita com a presença sutil do Velho Mestre; vale ensolarado ao fundo; medianiz de 12% livre. Alvo: 3024 × 2197 px a 300 dpi.

```text
Create one continuous horizontal double-page children's editorial illustration resolving the story at sunrise. Use @Northern_Mountain_Pass_Style as the strict style reference, and @General_Wen, @Zhang_Immortal, and @Wen_Old_Master as strict character references.

The first rays of a magnificent golden dawn break over the eastern mountain ridges, flooding the snowy pass with rich amber, peach, and warm morning light. On the far left page, Zhang the Immortal retreats in defeat, shielding his blistered face with his dark silk sleeve from the burning sunlight as he flees into the deep black shadows of a mountain cavern. On the outer right page, General Wen stands victorious and unwavering in a classic martial guard stance, his broken spear absent, hands loosely poised. His eyes are gently closed with a peaceful, serene smile on his weathered face. Bathed in the warm sunbeams beside Wen, a soft, translucent, ethereal manifestation of his beloved Old Master appears, smiling with boundless paternal pride. In the sun-drenched valley far below, the village wakes up safe and peaceful under the morning light.

Panoramic 35 mm lens feel with luminous atmospheric depth. The eye travels from the retreat in the dark shadows on the left, across the sunlit snowy ridge, to Wen's peaceful vigil and the spiritual warmth of his Master on the right.

Strictly protect the central 12% gutter zone: only the sun-drenched snowy mountain ridge and open sky cross the book fold. Keep Zhang, Wen, and the Master's figure safely situated on their respective page halves. Reserve clear low-detail text areas in the golden morning sky on the upper left and the calm snowbank on the lower right. Preserve 5% bleed tolerance.

Palette transitions from lingering indigo-charcoal shadows in the cave on the left into glorious radiant gold, warm vermilion, soft peach, and sparkling white snow on the right. Sophisticated digital watercolor and gouache on textured paper with luminous, poetic finish.

No generated text, calligraphy, page numbers, border, ghost caricatures, photorealism, anime, 3D CGI, horror elements or critical content in the gutter or bleed.
```
