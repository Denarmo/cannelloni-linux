import os
import io
import gzip
from PIL import Image, ImageFont, ImageDraw

LOGO_PATH = ".github/resources/logo.png"
FONT_PATH = "skeleton/SYSTEM/res/BPreplayBold-unhinted.otf"

logo = Image.open(LOGO_PATH)
bbox = logo.getbbox()
logo_cropped = logo.crop(bbox)

def make_bootlogo(w, h, logo_h=None, rotate_deg=0, mode="RGB", quantize_colors=None):
    """Generates a boot logo image centered on a black background reading 'Cannelloni' and 'forked from MinUI/Cannoli'."""
    canvas_w = w if rotate_deg in (0, 180) else h
    canvas_h = h if rotate_deg in (0, 180) else w
    
    scale = min(canvas_w / 640.0, canvas_h / 480.0)
    base_h = logo_h if logo_h is not None else int(min(canvas_w, canvas_h) * 0.32)
    lh = max(16, int(base_h * 0.75))
    lw = int(logo_cropped.width * (lh / logo_cropped.height))
    scaled = logo_cropped.resize((lw, lh), Image.Resampling.LANCZOS)
    
    title_text = "Cannelloni"
    sub_text = "forked from MinUI/Cannoli"
    
    title_size = max(8, int(28 * scale))
    sub_size = max(6, int(15 * scale))
    
    font_title = ImageFont.truetype(FONT_PATH, title_size)
    font_sub = ImageFont.truetype(FONT_PATH, sub_size)
    
    # Ensure subtitle fits within 92% of canvas width
    while sub_size > 5:
        tb = font_sub.getbbox(sub_text)
        if (tb[2] - tb[0]) <= canvas_w * 0.92:
            break
        sub_size -= 1
        font_sub = ImageFont.truetype(FONT_PATH, sub_size)
        
    while title_size > 6:
        tb = font_title.getbbox(title_text)
        if (tb[2] - tb[0]) <= canvas_w * 0.92:
            break
        title_size -= 1
        font_title = ImageFont.truetype(FONT_PATH, title_size)

    tb_t = font_title.getbbox(title_text)
    tw_t = tb_t[2] - tb_t[0]
    th_t = tb_t[3] - tb_t[1]

    tb_s = font_sub.getbbox(sub_text)
    tw_s = tb_s[2] - tb_s[0]
    th_s = tb_s[3] - tb_s[1]

    gap1 = max(2, int(10 * scale))
    gap2 = max(2, int(6 * scale))

    total_h = lh + gap1 + th_t + gap2 + th_s
    start_y = max(0, (canvas_h - total_h) // 2)

    bg = Image.new(mode, (canvas_w, canvas_h), (0, 0, 0, 255) if mode == "RGBA" else (0, 0, 0))
    lx = (canvas_w - lw) // 2
    bg.paste(scaled, (lx, start_y), scaled)

    draw = ImageDraw.Draw(bg)
    tx_t = (canvas_w - tw_t) // 2 - tb_t[0]
    ty_t = start_y + lh + gap1 - tb_t[1]
    draw.text((tx_t, ty_t), title_text, font=font_title, fill=(255, 255, 255))

    tx_s = (canvas_w - tw_s) // 2 - tb_s[0]
    ty_s = start_y + lh + gap1 + th_t + gap2 - tb_s[1]
    draw.text((tx_s, ty_s), sub_text, font=font_sub, fill=(205, 205, 205))

    if quantize_colors:
        bg = bg.quantize(colors=quantize_colors).convert("RGBA")

    if rotate_deg != 0:
        bg = bg.rotate(rotate_deg, expand=True)
    return bg

def make_action_screen(w, h, text, angle=0, mode="RGB", rotate_deg=0):
    """Generates an installation/updating screen with:
    1. Cannelloni logo at top.
    2. Message 'Installing Cannelloni' in middle.
    3. Spinning cannelloni rotated by `angle` below the message to show loading."""
    canvas_w = w if rotate_deg in (0, 180) else h
    canvas_h = h if rotate_deg in (0, 180) else w
    
    scale = min(canvas_w / 640.0, canvas_h / 480.0)
    
    # 1. Top Logo
    top_logo_h = max(24, int(105 * scale))
    top_logo_w = int(logo_cropped.width * (top_logo_h / logo_cropped.height))
    scaled_top_logo = logo_cropped.resize((top_logo_w, top_logo_h), Image.Resampling.LANCZOS)
    
    # 2. Text: "Installing Cannelloni" (or "Updating Cannelloni")
    font_size = max(10, int(26 * scale))
    font = ImageFont.truetype(FONT_PATH, font_size)
    draw_dummy = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    tb = draw_dummy.textbbox((0, 0), text, font=font)
    tw = tb[2] - tb[0]
    th = tb[3] - tb[1]
    
    # 3. Spinning Cannelloni below message
    spinner_box_size = max(20, int(84 * scale))
    spinner_w = int(spinner_box_size * 0.88)
    spinner_h = int(logo_cropped.height * (spinner_w / logo_cropped.width))
    spinner_base = logo_cropped.resize((spinner_w, spinner_h), Image.Resampling.LANCZOS)
    
    # Create square canvas for smooth centered rotation
    sq_canvas = Image.new('RGBA', (spinner_box_size, spinner_box_size), (0, 0, 0, 0))
    sq_canvas.paste(spinner_base, ((spinner_box_size - spinner_w) // 2, (spinner_box_size - spinner_h) // 2), spinner_base)
    rotated_spinner = sq_canvas.rotate(angle, resample=Image.Resampling.BICUBIC)
    
    # Vertical layout
    gap1 = max(4, int(18 * scale))
    gap2 = max(6, int(24 * scale))
    total_h = top_logo_h + gap1 + th + gap2 + spinner_box_size
    start_y = max(0, int((canvas_h - total_h) // 2))
    
    im = Image.new(mode, (canvas_w, canvas_h), (0, 0, 0, 255) if mode == "RGBA" else (0, 0, 0))
    
    # Paste top logo
    lx = (canvas_w - top_logo_w) // 2
    im.paste(scaled_top_logo, (lx, start_y), scaled_top_logo)
    
    # Draw text
    draw = ImageDraw.Draw(im)
    tx = (canvas_w - tw) // 2
    ty = start_y + top_logo_h + gap1
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255))
    
    # Paste rotated spinner below text
    sx = (canvas_w - spinner_box_size) // 2
    sy = ty + th + gap2
    im.paste(rotated_spinner, (sx, sy), rotated_spinner)
    
    if rotate_deg != 0:
        im = im.rotate(rotate_deg, expand=True)
    return im

def save_image(img, path, fmt=None, quality=90):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if fmt is None:
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.jpg', '.jpeg'):
            fmt = 'JPEG'
        elif ext == '.bmp':
            fmt = 'BMP'
        else:
            fmt = 'PNG'
    if fmt == 'JPEG':
        img.convert('RGB').save(path, format=fmt, quality=quality)
    elif fmt == 'BMP':
        img.save(path, format=fmt)
    else:
        img.save(path, format=fmt)
    print(f"Generated {path} ({img.size}, {img.mode})")

def generate_action_screen_set(w, h, text, base_path_pattern, mode="RGB", rotate_deg=0, num_frames=12):
    """Generates the static action screen (frame 0) and the full animated sequence of rotation frames."""
    angles = [int(i * (360.0 / num_frames)) for i in range(num_frames)]
    
    # Static base image (angle 0)
    base_img = make_action_screen(w, h, text, angle=0, mode=mode, rotate_deg=rotate_deg)
    save_image(base_img, base_path_pattern.replace("{frame}", "").replace("_.png", ".png").replace("_.bmp", ".bmp"))
    
    # Animated frames
    for i, ang in enumerate(angles):
        frame_img = make_action_screen(w, h, text, angle=-ang, mode=mode, rotate_deg=rotate_deg)
        frame_path = base_path_pattern.format(frame=f"{i:02d}")
        save_image(frame_img, frame_path)

def main():
    print("Generating official Cannelloni boot logos, action screens, and spinning loaders...")

    # 1. Boot logos
    save_image(make_bootlogo(640, 480, logo_h=140, rotate_deg=180), "skeleton/SYSTEM/miyoomini/dat/image1.jpg", "JPEG", quality=90)
    save_image(make_bootlogo(240, 320, logo_h=60, rotate_deg=90), "skeleton/SYSTEM/trimuismart/dat/logo.bmp", "BMP")
    save_image(make_bootlogo(100, 100, logo_h=45), "skeleton/EXTRAS/Tools/m17/Bootlogo.pak/logo.bmp", "BMP")
    save_image(make_bootlogo(480, 640, logo_h=140, rotate_deg=90, mode="RGBA", quantize_colors=64), "skeleton/EXTRAS/Tools/my282/Bootlogo.pak/bootlogo.bmp", "BMP")
    save_image(make_bootlogo(640, 480, logo_h=140), "skeleton/EXTRAS/Tools/my355/Bootlogo.pak/payload/logo.bmp", "BMP")
    save_image(make_bootlogo(128, 128, logo_h=60), "skeleton/EXTRAS/Tools/tg5040/Bootlogo.pak/bootlogo.bmp", "BMP")
    save_image(make_bootlogo(216, 237, logo_h=90), "skeleton/EXTRAS/Tools/tg5040/Bootlogo.pak/brick/bootlogo.bmp", "BMP")
    save_image(make_bootlogo(120, 120, logo_h=55), "skeleton/EXTRAS/Tools/zero28/Bootlogo.pak/bootlogo.bmp", "BMP")
    save_image(make_bootlogo(640, 480, logo_h=140), "workspace/rg35xx/boot/boot_logo.png", "PNG")
    save_image(make_bootlogo(640, 480, logo_h=140), "workspace/rg35xxplus/boot/bootlogo.bmp", "BMP")
    save_image(make_bootlogo(480, 640, logo_h=140, rotate_deg=90), "workspace/rg35xxplus/boot/bootlogo-r.bmp", "BMP")
    save_image(make_bootlogo(720, 720, logo_h=160), "workspace/rg35xxplus/boot/bootlogo-s.bmp", "BMP")
    save_image(make_bootlogo(720, 480, logo_h=140), "workspace/rg35xxplus/boot/bootlogo-w.bmp", "BMP")

    # 2. Action screens (Installing and Updating) with spinning Cannelloni loader
    # 640x480 standard
    for plat in ["miyoomini", "my282", "my355", "zero28", "tg5040"]:
        generate_action_screen_set(640, 480, "Installing Cannelloni", f"workspace/{plat}/install/installing_{{frame}}.png")
        generate_action_screen_set(640, 480, "Updating Cannelloni", f"workspace/{plat}/install/updating_{{frame}}.png")

    # RG35XX & RG35XX+
    ins_640 = make_action_screen(640, 480, "Installing Cannelloni", angle=0)
    upd_640 = make_action_screen(640, 480, "Updating Cannelloni", angle=0)
    save_image(ins_640, "workspace/rg35xx/boot/installing.bmp", "BMP")
    save_image(upd_640, "workspace/rg35xx/boot/updating.bmp", "BMP")
    save_image(ins_640, "workspace/rg35xxplus/boot/installing.bmp", "BMP")
    save_image(upd_640, "workspace/rg35xxplus/boot/updating.bmp", "BMP")

    # 960x720 Brick
    generate_action_screen_set(960, 720, "Installing Cannelloni", "workspace/tg5040/install/brick/installing_{frame}.png")
    generate_action_screen_set(960, 720, "Updating Cannelloni", "workspace/tg5040/install/brick/updating_{frame}.png")

    # 320x240 TrimUI Smart & GKD Pixel
    generate_action_screen_set(320, 240, "Installing Cannelloni", "workspace/trimuismart/install/installing_{frame}.png")
    generate_action_screen_set(320, 240, "Updating Cannelloni", "workspace/trimuismart/install/updating_{frame}.png")
    ins_320 = make_action_screen(320, 240, "Installing Cannelloni", angle=0)
    upd_320 = make_action_screen(320, 240, "Updating Cannelloni", angle=0)
    save_image(ins_320, "workspace/gkdpixel/boot/installing.bmp", "BMP")
    save_image(upd_320, "workspace/gkdpixel/boot/updating.bmp", "BMP")

    # 480x272 M17
    ins_480_272 = make_action_screen(480, 272, "Installing Cannelloni", angle=0)
    upd_480_272 = make_action_screen(480, 272, "Updating Cannelloni", angle=0)
    save_image(ins_480_272, "workspace/m17/boot/installing.bmp", "BMP")
    save_image(upd_480_272, "workspace/m17/boot/updating.bmp", "BMP")

    # 480x640 MagicMini & RG35XX Plus Rotated
    ins_480_640 = make_action_screen(480, 640, "Installing Cannelloni", angle=0)
    upd_480_640 = make_action_screen(480, 640, "Updating Cannelloni", angle=0)
    save_image(ins_480_640, "workspace/magicmini/install/installing.bmp", "BMP")
    save_image(upd_480_640, "workspace/magicmini/install/updating.bmp", "BMP")
    save_image(ins_480_640, "workspace/rg35xxplus/boot/installing-r.bmp", "BMP")
    save_image(upd_480_640, "workspace/rg35xxplus/boot/updating-r.bmp", "BMP")

    # 720x720 Square
    ins_720 = make_action_screen(720, 720, "Installing Cannelloni", angle=0)
    upd_720 = make_action_screen(720, 720, "Updating Cannelloni", angle=0)
    save_image(ins_720, "workspace/rg35xxplus/boot/installing-s.bmp", "BMP")
    save_image(upd_720, "workspace/rg35xxplus/boot/updating-s.bmp", "BMP")

    # 720x480 Wide
    ins_720_480 = make_action_screen(720, 480, "Installing Cannelloni", angle=0)
    upd_720_480 = make_action_screen(720, 480, "Updating Cannelloni", angle=0)
    save_image(ins_720_480, "workspace/rg35xxplus/boot/installing-w.bmp", "BMP")
    save_image(upd_720_480, "workspace/rg35xxplus/boot/updating-w.bmp", "BMP")

    # Tool and Setting resource images
    save_image(upd_640, "skeleton/EXTRAS/Settings/rgb30/Wi-Fi.pak/res/update.png", "PNG")
    save_image(upd_640, "skeleton/EXTRAS/Tools/my282/Bootlogo.pak/res/updating.png", "PNG")
    save_image(make_action_screen(640, 480, "Rebooting...", angle=0), "skeleton/EXTRAS/Tools/my355/Bootlogo.pak/res/reboot.png", "PNG")
    save_image(make_action_screen(640, 480, "Replacing Boot Logo...", angle=0), "skeleton/EXTRAS/Tools/my355/Bootlogo.pak/res/replace-logo.png", "PNG")
    save_image(make_action_screen(640, 480, "Rebooting...", angle=0), "workspace/my355/init/res/reboot.png", "PNG")

    print("All assets generated successfully!")

if __name__ == "__main__":
    main()
