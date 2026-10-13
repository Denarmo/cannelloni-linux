import os
import math
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "skeleton/SYSTEM/res/BPreplayBold-unhinted.otf"

def draw_lightning_bolt(draw, cx, cy, size, fill_color):
    """Draws a stylized lightning bolt centered at (cx, cy)."""
    s = size / 40.0
    pts = [
        (cx - 3 * s, cy - 20 * s),
        (cx + 8 * s, cy - 20 * s),
        (cx - 2 * s, cy - 2 * s),
        (cx + 10 * s, cy - 2 * s),
        (cx - 10 * s, cy + 20 * s),
        (cx - 3 * s, cy + 3 * s),
        (cx - 9 * s, cy + 3 * s),
    ]
    draw.polygon(pts, fill=fill_color)

def generate_charging_frame(w, h, fill_pct, is_pulse=False):
    """Generates a 640x480 charging frame with a cannelloni battery filling up."""
    im = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(im)

    # Fonts
    font_title = ImageFont.truetype(FONT_PATH, 28)
    font_status = ImageFont.truetype(FONT_PATH, 18)

    cx = w // 2
    battery_w = 120
    battery_h = 200
    top_y = 145

    # 1. Title at top: "Cannelloni"
    title_text = "Cannelloni"
    tb_t = font_title.getbbox(title_text)
    tw_t = tb_t[2] - tb_t[0]
    draw.text((cx - tw_t // 2, 75), title_text, font=font_title, fill=(255, 255, 255))

    # 2. Battery Positive Terminal (top cap)
    cap_w = 40
    cap_h = 10
    cap_x0 = cx - cap_w // 2
    cap_y0 = top_y - cap_h
    cap_x1 = cx + cap_w // 2
    cap_y1 = top_y
    draw.rounded_rectangle([cap_x0, cap_y0, cap_x1, cap_y1], radius=4, fill=(227, 163, 13))

    # 3. Outer Cannelloni Tube (battery body)
    body_x0 = cx - battery_w // 2
    body_y0 = top_y
    body_x1 = cx + battery_w // 2
    body_y1 = top_y + battery_h
    border_radius = 16
    border_width = 6

    # Draw outer border
    draw.rounded_rectangle([body_x0, body_y0, body_x1, body_y1], radius=border_radius, outline=(227, 163, 13), width=border_width)

    # Inner cavity dimensions
    pad = border_width + 4
    cav_x0 = body_x0 + pad
    cav_y0 = body_y0 + pad
    cav_x1 = body_x1 - pad
    cav_y1 = body_y1 - pad
    cav_w = cav_x1 - cav_x0
    cav_h = cav_y1 - cav_y0

    # Draw subtle background pasta ridges inside empty portion of tube
    ridge_color = (25, 22, 10)
    for ry in range(cav_y0 + 8, cav_y1 - 4, 16):
        draw.line([(cav_x0 + 4, ry), (cav_x1 - 4, ry)], fill=ridge_color, width=2)

    # 4. Golden Ricotta Filling (liquid filling rising from bottom)
    if fill_pct > 0.02:
        fill_h = max(8, int(cav_h * fill_pct))
        fill_y0 = cav_y1 - fill_h
        fill_y1 = cav_y1

        # Draw filled rect with rounded bottom
        draw.rounded_rectangle([cav_x0, fill_y0, cav_x1, fill_y1], radius=8, fill=(241, 196, 15))

        # Add subtle warm gradient / cheese highlights
        highlight_y = fill_y0 + 2
        if highlight_y < cav_y1:
            draw.line([(cav_x0 + 4, fill_y0 + 2), (cav_x1 - 4, fill_y0 + 2)], fill=(255, 245, 180), width=3)

        # Subtle cheese texture bubbles / ridges in the filling
        fill_ridge_color = (220, 160, 10)
        for ry in range(fill_y0 + 12, fill_y1 - 6, 16):
            draw.line([(cav_x0 + 6, ry), (cav_x1 - 6, ry)], fill=fill_ridge_color, width=2)

    # 5. Centered Lightning Bolt
    bolt_cy = (cav_y0 + cav_y1) // 2
    bolt_fill = (255, 255, 255) if fill_pct < 0.6 else (40, 30, 10)
    draw_lightning_bolt(draw, cx, bolt_cy, size=36, fill_color=bolt_fill)

    # 6. Status text at bottom: "Charging" and percentage
    pct_text = f"Charging ({int(fill_pct * 100)}%)"
    tb_s = font_status.getbbox(pct_text)
    tw_s = tb_s[2] - tb_s[0]
    draw.text((cx - tw_s // 2, body_y1 + 25), pct_text, font=font_status, fill=(200, 200, 200))

    return im

def main():
    print("Generating official Cannelloni charging assets and animation frames...")
    
    # 6 progressive filling frames (15%, 32%, 50%, 68%, 85%, 100%)
    fill_levels = [0.15, 0.32, 0.50, 0.68, 0.85, 1.00]
    
    # Static fallback charging image (showing ~70% charged state)
    static_img = generate_charging_frame(640, 480, 0.70)
    static_path = "skeleton/SYSTEM/res/charging-640-480.png"
    static_img.save(static_path, "PNG")
    print(f"Saved static charging screen: {static_path}")
    
    # Also save to RG35XX ramdisk
    rg35xx_path = "workspace/rg35xx/ramdisk/charging.png"
    os.makedirs(os.path.dirname(rg35xx_path), exist_ok=True)
    static_img.save(rg35xx_path, "PNG")
    print(f"Saved RG35XX charging screen: {rg35xx_path}")

    # Generate animation frames: charging_00.png .. charging_05.png
    for i, pct in enumerate(fill_levels):
        frame_img = generate_charging_frame(640, 480, pct)
        frame_path = f"skeleton/SYSTEM/res/charging_{i:02d}.png"
        frame_img.save(frame_path, "PNG")
        print(f"Saved frame {i}: {frame_path} ({int(pct*100)}%)")

if __name__ == "__main__":
    main()
