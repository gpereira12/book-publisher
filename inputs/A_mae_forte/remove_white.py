from PIL import Image

def make_white_transparent(image_path, output_path):
    img = Image.open(image_path).convert("RGBA")
    datas = img.getdata()

    newData = []
    # threshold for white (e.g., > 240,240,240)
    for item in datas:
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)

    img.putdata(newData)
    img.save(output_path, "PNG")

make_white_transparent("assets/arabesco_inferior.png", "assets/arabesco_inferior.png")
