import os, shutil

src = 'build_release/temp/nds_dleicht/NDS.pak'
dst = 'skeleton/EXTRAS/Emus/miyoomini/NDS-Drastic.pak'

os.makedirs(dst, exist_ok=True)
for item in os.listdir(src):
    s = os.path.join(src, item)
    d = os.path.join(dst, item)
    if os.path.isdir(s):
        if os.path.exists(d):
            shutil.rmtree(d)
        shutil.copytree(s, d)
    else:
        shutil.copy2(s, d)

print(f"Copied all files from {src} to {dst}")
print("Contents of NDS-Drastic.pak:", os.listdir(dst))
print("Libs in NDS-Drastic.pak/libs:", os.listdir(os.path.join(dst, 'libs')))
