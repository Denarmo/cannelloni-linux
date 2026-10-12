import os
from PIL import Image

GOLD_R, GOLD_G, GOLD_B = 241, 196, 15  # #f1c40f

res_dir = "skeleton/SYSTEM/res"
png_files = [f for f in os.listdir(res_dir) if f.startswith("assets@") and f.endswith(".png")]

for f in png_files:
    path = os.path.join(res_dir, f)
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    pixels = im.load()
    changed = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a > 0:
                # Check if pixel is white / light-tinted white
                if r > 180 and g > 180 and b > 180 and abs(r - g) < 30 and abs(g - b) < 30:
                    nr = (r * GOLD_R) // 255
                    ng = (g * GOLD_G) // 255
                    nb = (b * GOLD_B) // 255
                    pixels[x, y] = (nr, ng, nb, a)
                    changed += 1
    im.save(path, format="PNG")
    print(f"Updated {f}: {changed} pixels tinted to #f1c40f")

print("All assets successfully tinted to Cannelloni Gold!")
