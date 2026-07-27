from playwright.sync_api import sync_playwright
import os

html_content = """
<!DOCTYPE html>
<html>
<head>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    <style>
        body {
            margin: 0;
            padding: 0;
            width: 1600px;
            height: 2300px;
            background-image: url('file:///Users/gabrielpereira/Desktop/Projetos/Livros/inputs/A_mae_forte/assets/Capa_livro.jpeg');
            background-size: cover;
            background-position: center;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-items: center;
            box-sizing: border-box;
            padding-top: 250px;
            padding-bottom: 120px;
        }
        .title-container {
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-top: 100px;
        }
        .title {
            font-family: 'Cinzel', serif;
            font-size: 180px;
            color: #f7ecd5; /* warm ivory/gold */
            text-shadow: 0px 10px 30px rgba(0,0,0,0.9), 0px 2px 5px rgba(0,0,0,0.7);
            margin: 0;
            line-height: 1.1;
            font-weight: 700;
        }
        .subtitle {
            font-family: 'Playfair Display', serif;
            font-size: 60px;
            color: #dbb666; /* gold matching the logo */
            letter-spacing: 12px;
            margin-top: 50px;
            text-shadow: 0px 5px 20px rgba(0,0,0,0.9);
            text-transform: uppercase;
        }
        .author-container {
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .author {
            font-family: 'Cinzel', serif;
            font-size: 75px;
            color: #f7ecd5;
            letter-spacing: 8px;
            margin-bottom: 80px;
            text-shadow: 0px 5px 20px rgba(0,0,0,0.9);
        }
        .logo {
            width: 180px;
            filter: drop-shadow(0px 5px 15px rgba(0,0,0,0.9));
        }
    </style>
</head>
<body>
    <div class="title-container">
        <div class="title">A Mãe Forte</div>
        <div class="subtitle">Um Itinerário de 33 Dias</div>
    </div>
    
    <div class="author-container">
        <div class="author">Carolina Cordaro</div>
        <img class="logo" src="file:///Users/gabrielpereira/Desktop/Projetos/Livros/resources/logos/ilios/logo.svg" />
    </div>
</body>
</html>
"""

html_path = "/Users/gabrielpereira/Desktop/Projetos/Livros/inputs/A_mae_forte/cover_temp.html"
with open(html_path, "w") as f:
    f.write(html_content)

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 2300})
        page.goto(f"file://{html_path}")
        page.evaluate('document.fonts.ready')
        
        # Give it a tiny bit of time for background images just in case
        page.wait_for_timeout(1000)
        
        output_path = "/Users/gabrielpereira/Desktop/Projetos/Livros/inputs/A_mae_forte/Capa_Digital_Final.jpeg"
        page.screenshot(path=output_path, type="jpeg", quality=100)
        browser.close()

run()
