import os
import shutil

nds_dir = 'skeleton/SYSTEM/miyoomini/paks/Emus/NDS.pak'
drastic_dir = 'skeleton/EXTRAS/Emus/miyoomini/NDS-Drastic.pak'

# Move DraStic files to NDS-Drastic.pak in EXTRAS
if os.path.isfile(os.path.join(nds_dir, 'drastic')):
    os.makedirs(drastic_dir, exist_ok=True)
    for item in os.listdir(nds_dir):
        s = os.path.join(nds_dir, item)
        d = os.path.join(drastic_dir, item)
        if os.path.exists(d):
            if os.path.isdir(d):
                shutil.rmtree(d)
            else:
                os.remove(d)
        shutil.move(s, d)

# Recreate clean NDS.pak in SYSTEM
os.makedirs(nds_dir, exist_ok=True)
cfg_content = "bind Up = UP\nbind Down = DOWN\nbind Left = LEFT\nbind Right = RIGHT\nbind Select = SELECT\nbind Start = START\nbind Y Button = Y\nbind X Button = X\nbind B Button = B\nbind A Button = A\nbind L Button = L1\nbind R Button = R1\nbind L2 Button = L2\nbind R2 Button = R2\n"
with open(os.path.join(nds_dir, 'default.cfg'), 'w', newline='\n') as f:
    f.write(cfg_content)

from pathlib import Path
from update_nds_launchers import write_launchers

# Ensure the launcher exists before regenerating all platform copies.
Path(nds_dir, 'launch.sh').touch()
write_launchers()

# Also update skeleton/EXTRAS/Emus/miyoomini/NDS.pak
nds_extras_dir = 'skeleton/EXTRAS/Emus/miyoomini/NDS.pak'
if os.path.isdir(nds_extras_dir):
    shutil.rmtree(nds_extras_dir)
shutil.copytree(nds_dir, nds_extras_dir)

print('Clean NDS.pak libretro configuration restored and NDS-Drastic.pak created!')
