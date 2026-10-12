import os, io, zipfile
from PIL import Image

THEMES = {
    "#f1c40f": ("Cannelloni Gold", 241, 196, 15),
    "#e74c3c": ("Tomato Red", 231, 76, 60),
    "#2ecc71": ("Basil Green", 46, 204, 113),
    "#3498db": ("Sky Blue", 52, 152, 219),
    "#9b59b6": ("Amethyst Purple", 155, 89, 182),
    "#e67e22": ("Carrot Orange", 230, 126, 34),
    "#ffffff": ("Pasta White", 255, 255, 255),
}

# 1. Extract pristine white assets from upstream base.zip
pristine_assets = {}
with zipfile.ZipFile('build_release/temp/base.zip') as base_z:
    with zipfile.ZipFile(io.BytesIO(base_z.read('MinUI.zip'))) as mz:
        for name in mz.namelist():
            if name.startswith('.system/res/assets@') and name.endswith('.png'):
                bname = os.path.basename(name)
                pristine_assets[bname] = mz.read(name)

print("Extracted pristine assets:", list(pristine_assets.keys()))

def tint_image(img_data, tr, tg, tb):
    im = Image.open(io.BytesIO(img_data)).convert("RGBA")
    w, h = im.size
    pixels = im.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a > 0:
                # Tint white/light-gray pixels
                if r > 180 and g > 180 and b > 180 and abs(r - g) < 30 and abs(g - b) < 30:
                    nr = (r * tr) // 255
                    ng = (g * tg) // 255
                    nb = (b * tb) // 255
                    pixels[x, y] = (nr, ng, nb, a)
    out_buf = io.BytesIO()
    im.save(out_buf, format="PNG")
    return out_buf.getvalue()

# 2. Generate theme directories
themes_dir = "skeleton/SYSTEM/res/themes"
os.makedirs(themes_dir, exist_ok=True)

for hex_code, (name, r, g, b) in THEMES.items():
    theme_path = os.path.join(themes_dir, hex_code)
    os.makedirs(theme_path, exist_ok=True)
    for bname, raw_png in pristine_assets.items():
        if hex_code == "#ffffff":
            tinted = raw_png
        else:
            tinted = tint_image(raw_png, r, g, b)
        target = os.path.join(theme_path, bname)
        with open(target, 'wb') as f:
            f.write(tinted)
    print(f"Generated theme {name} ({hex_code})")

# 3. Also update default skeleton/SYSTEM/res/assets@*.png with Cannelloni Gold (#f1c40f)
gold_theme_dir = os.path.join(themes_dir, "#f1c40f")
for bname in pristine_assets.keys():
    with open(os.path.join(gold_theme_dir, bname), 'rb') as f:
        data = f.read()
    with open(os.path.join("skeleton/SYSTEM/res", bname), 'wb') as f:
        f.write(data)

print("Default assets in skeleton/SYSTEM/res updated to Cannelloni Gold!")
