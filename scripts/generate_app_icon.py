"""Generate a high-resolution, multi-layer Windows .ico and .png brand icon.

Creates assets/icons/cortex.ico and assets/icons/cortex.png with multi-size layers:
256x256, 128x128, 64x64, 48x48, 32x32, 16x16.
"""
import os
import math
from PIL import Image, ImageDraw, ImageFilter

def create_cortex_icon(size: int = 256) -> Image.Image:
    """Render a premium cybernetic shield emblem for Cortex Workstation."""
    scale = size / 256.0
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Center & coordinates
    cx, cy = size / 2, size / 2

    # Shield points relative to 256x256
    raw_shield = [
        (128, 20),   # Top center peak
        (216, 44),   # Top right corner
        (210, 150),  # Mid right
        (128, 236),  # Bottom tip
        (46, 150),   # Mid left
        (40, 44),    # Top left corner
    ]
    shield_pts = [(p[0] * scale, p[1] * scale) for p in raw_shield]

    # 1. Outer ambient glow (blurred cyan layer)
    glow_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    glow_draw.polygon(shield_pts, fill=(0, 210, 255, 60))
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=8 * scale))
    img.alpha_composite(glow_img)

    # 2. Shield Dark Carbon Background
    # Draw dark metallic base
    draw.polygon(shield_pts, fill=(13, 19, 33, 245))

    # Inner shield (inset by ~8px at 256x256)
    inset = 10 * scale
    raw_inner = [
        (128, 20 + inset * 1.2),
        (216 - inset, 44 + inset * 0.8),
        (210 - inset * 0.9, 150 - inset * 0.5),
        (128, 236 - inset * 1.4),
        (46 + inset * 0.9, 150 - inset * 0.5),
        (40 + inset, 44 + inset * 0.8),
    ]
    inner_pts = [(p[0] * scale, p[1] * scale) for p in raw_inner]
    draw.polygon(inner_pts, fill=(18, 26, 46, 255))

    # 3. Outer Shield Border (Vibrant Cyan Gradient Simulation)
    border_w = max(2, int(6 * scale))
    draw.line(shield_pts + [shield_pts[0]], fill=(0, 210, 255, 255), width=border_w, joint="curve")

    # 4. Neural Cortex Network / Circuits in the center
    # Central Core Node
    core_r = 18 * scale
    draw.ellipse([cx - core_r, cy - core_r + 4 * scale, cx + core_r, cy + core_r + 4 * scale],
                 fill=(0, 210, 255, 230), outline=(255, 255, 255, 255), width=max(1, int(2 * scale)))

    # Satellite Nodes & Circuit Traces
    satellites = [
        (cx, cy - 54 * scale),              # Top
        (cx + 46 * scale, cy - 24 * scale), # Top Right
        (cx + 40 * scale, cy + 38 * scale), # Bottom Right
        (cx, cy + 62 * scale),              # Bottom
        (cx - 40 * scale, cy + 38 * scale), # Bottom Left
        (cx - 46 * scale, cy - 24 * scale), # Top Left
    ]

    line_w = max(1, int(3 * scale))
    node_r = 8 * scale

    for sx, sy in satellites:
        # Trace line from center to satellite
        draw.line([(cx, cy + 4 * scale), (sx, sy)], fill=(56, 189, 248, 200), width=line_w)
        # Node circle
        draw.ellipse([sx - node_r, sy - node_r, sx + node_r, sy + node_r],
                     fill=(14, 165, 233, 255), outline=(255, 255, 255, 220), width=max(1, int(1.5 * scale)))

    # Connect outer satellites in a hexagonal circuit ring
    for i in range(len(satellites)):
        p1 = satellites[i]
        p2 = satellites[(i + 1) % len(satellites)]
        draw.line([p1, p2], fill=(0, 210, 255, 120), width=max(1, int(2 * scale)))

    # 5. Core bright specular center
    spec_r = 7 * scale
    draw.ellipse([cx - spec_r, cy - spec_r + 4 * scale, cx + spec_r, cy + spec_r + 4 * scale],
                 fill=(255, 255, 255, 255))

    return img

def main():
    os.makedirs("assets/icons", exist_ok=True)
    sizes = [256, 128, 64, 48, 32, 16]
    images = [create_cortex_icon(s) for s in sizes]

    # Save 256x256 PNG
    png_path = "assets/icons/cortex.png"
    images[0].save(png_path, format="PNG")
    print(f"[✓] Saved PNG: {png_path}")

    # Save Multi-Layer Windows .ICO
    ico_path = "assets/icons/cortex.ico"
    images[0].save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"[✓] Saved Multi-Resolution ICO: {ico_path} with sizes {sizes}")

if __name__ == "__main__":
    main()
