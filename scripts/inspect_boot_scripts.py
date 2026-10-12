import glob

for p in sorted(glob.glob('workspace/*/install/boot.sh') + glob.glob('workspace/*/boot/boot.sh')):
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    print(f"=== {p} ===")
    for i, line in enumerate(lines):
        if any(k in line for k in ['UPDATE', 'unzip', 'rm -f', 'device_select', 'LAUNCH_PATH']):
            print(f"  {i+1}: {line.strip()}")
