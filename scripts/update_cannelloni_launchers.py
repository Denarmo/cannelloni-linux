import glob
import re

platforms = [
    'gkdpixel', 'm17', 'magicmini', 'miyoomini', 'my282', 'my355',
    'rg35xx', 'rg35xxplus', 'rgb30', 'tg5040', 'trimuismart', 'zero28'
]

for p in platforms:
    path = f"skeleton/SYSTEM/{p}/paks/Cannelloni.pak/launch.sh"
    with open(path, "rb") as f:
        content = f.read().decode("utf-8", errors="ignore")

    # Replace the execution inside if [ -f $NEXT_PATH ]
    # Target pattern
    pattern = r'(\tif \[ -f \$NEXT_PATH \]; then\r?\n)(.*?)(\t\trm -f \$NEXT_PATH)'
    
    replacement_body = (
        r"\1"
        "\t\tCMD=`cat $NEXT_PATH`\n"
        "\t\tLAUNCH_LOG=\"$SDCARD_PATH/cannelloni_launch.log\"\n"
        "\t\techo \"=== [$(date +'%Y-%m-%d %H:%M:%S')] Launching: $CMD ===\" >> \"$LAUNCH_LOG\"\n"
        "\t\techo \"Platform: $PLATFORM, System: $SYSTEM_PATH, Cores: $CORES_PATH\" >> \"$LAUNCH_LOG\"\n"
        "\t\techo \"LD_LIBRARY_PATH: $LD_LIBRARY_PATH\" >> \"$LAUNCH_LOG\"\n"
        "\t\techo \"PATH: $PATH\" >> \"$LAUNCH_LOG\"\n"
        "\t\teval $CMD >> \"$LAUNCH_LOG\" 2>&1\n"
        "\t\tCMD_EXIT=$?\n"
        "\t\techo \"=== Command finished with exit code: $CMD_EXIT ===\" >> \"$LAUNCH_LOG\"\n"
        "\t\techo \"\" >> \"$LAUNCH_LOG\"\n"
        "\t\tsync\n"
        r"\3"
    )

    new_content = re.sub(pattern, replacement_body, content, flags=re.DOTALL)
    if new_content != content:
        # Enforce Unix LF
        new_bytes = new_content.replace("\r\n", "\n").encode("utf-8")
        with open(path, "wb") as f:
            f.write(new_bytes)
        print(f"Updated {path}")
    else:
        print(f"Could not match pattern in {path}")
