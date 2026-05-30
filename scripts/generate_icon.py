"""Generate ClearSameFile app icon (pure Python, no Pillow/PySide6 needed).

Produces resources/app.ico with a clean professional design:
blue rounded-rect background, two overlapping document silhouettes,
and a magnifying glass overlay — all rendered via raw pixel math."""
import struct
import os
import math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "resources")
OUT_PATH = os.path.join(OUT_DIR, "app.ico")


# ── colour helpers ──────────────────────────────────────────────
def lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(lerp(c1[i], c2[i], t) for i in range(4))


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ── pixel-pushing ───────────────────────────────────────────────
def set_pixel(pixels: bytearray, x: int, y: int, w: int, h: int, color: tuple):
    """Set pixel (x,y) to RGBA color, blending with background."""
    if x < 0 or x >= w or y < 0 or y >= h:
        return
    i = (y * w + x) * 4
    # Existing BGRA
    b = pixels[i]
    g = pixels[i + 1]
    r = pixels[i + 2]
    a = pixels[i + 3]
    # Source is RGBA
    sr, sg, sb, sa = color
    sa_norm = sa / 255.0
    da_norm = a / 255.0
    out_a = sa_norm + da_norm * (1 - sa_norm)
    if out_a == 0:
        return
    out_r = (sr * sa_norm + r * da_norm * (1 - sa_norm)) / out_a
    out_g = (sg * sa_norm + g * da_norm * (1 - sa_norm)) / out_a
    out_b = (sb * sa_norm + b * da_norm * (1 - sa_norm)) / out_a
    pixels[i] = round(out_b)       # B
    pixels[i + 1] = round(out_g)   # G
    pixels[i + 2] = round(out_r)   # R
    pixels[i + 3] = round(out_a * 255)


def fill_rect(pixels: bytearray, x: int, y: int, rw: int, rh: int,
              w: int, h: int, color: tuple):
    x0 = max(x, 0)
    y0 = max(y, 0)
    x1 = min(x + rw, w)
    y1 = min(y + rh, h)
    for py in range(y0, y1):
        for px in range(x0, x1):
            set_pixel(pixels, px, py, w, h, color)


def fill_rounded_rect(pixels: bytearray, x: int, y: int, rw: int, rh: int,
                      radius: int, w: int, h: int, color: tuple):
    """Fill a rounded rectangle using anti-aliased corners."""
    def inside(cx: float, cy: float, rx: float, ry: float) -> float:
        """Signed distance from corner arc center for anti-aliasing."""
        return math.sqrt(cx * cx + cy * cy) - rx

    for py in range(y, y + rh):
        for px in range(x, x + rw):
            # Determine which corner region
            if px < x + radius and py < y + radius:
                # top-left
                d = inside(px - (x + radius) + 0.5, py - (y + radius) + 0.5, radius, radius)
            elif px >= x + rw - radius and py < y + radius:
                # top-right
                d = inside(px - (x + rw - radius) + 0.5, py - (y + radius) + 0.5, radius, radius)
            elif px < x + radius and py >= y + rh - radius:
                # bottom-left
                d = inside(px - (x + radius) + 0.5, py - (y + rh - radius) + 0.5, radius, radius)
            elif px >= x + rw - radius and py >= y + rh - radius:
                # bottom-right
                d = inside(px - (x + rw - radius) + 0.5, py - (y + rh - radius) + 0.5, radius, radius)
            else:
                d = -1  # inside body

            if d < -0.5:
                set_pixel(pixels, px, py, w, h, color)
            elif d < 0.5:
                # Anti-alias edge
                alpha = clamp((0.5 - d), 0, 1)
                blended = list(color)
                blended[3] = round(color[3] * alpha)
                set_pixel(pixels, px, py, w, h, tuple(blended))


def draw_line(pixels: bytearray, x0: int, y0: int, x1: int, y1: int,
              w: int, h: int, color: tuple, thickness: int = 1):
    """Bresenham line with square thickness."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        for ty in range(-thickness // 2, (thickness + 1) // 2):
            for tx in range(-thickness // 2, (thickness + 1) // 2):
                set_pixel(pixels, x0 + tx, y0 + ty, w, h, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def fill_circle(pixels: bytearray, cx: int, cy: int, r: int,
                w: int, h: int, color: tuple):
    """Filled circle (uses distance for AA)."""
    y0 = max(cy - r - 1, 0)
    y1 = min(cy + r + 1, h)
    x0 = max(cx - r - 1, 0)
    x1 = min(cx + r + 1, w)
    for py in range(y0, y1):
        for px in range(x0, x1):
            d = math.sqrt((px - cx + 0.5) ** 2 + (py - cy + 0.5) ** 2) - r
            if d < -0.5:
                set_pixel(pixels, px, py, w, h, color)
            elif d < 0.5:
                alpha = clamp((0.5 - d), 0, 1)
                blended = list(color)
                blended[3] = round(color[3] * alpha)
                set_pixel(pixels, px, py, w, h, tuple(blended))


def draw_circle_outline(pixels: bytearray, cx: int, cy: int, r: int,
                        w: int, h: int, color: tuple, thickness: int = 2):
    """Anti-aliased circle outline."""
    y0 = max(cy - r - thickness, 0)
    y1 = min(cy + r + thickness, h)
    x0 = max(cx - r - thickness, 0)
    x1 = min(cx + r + thickness, w)
    for py in range(y0, y1):
        for px in range(x0, x1):
            dist = math.sqrt((px - cx + 0.5) ** 2 + (py - cy + 0.5) ** 2)
            if abs(dist - r) <= thickness / 2:
                d = abs(dist - r) - thickness / 2 + 0.5
                if d < 0:
                    set_pixel(pixels, px, py, w, h, color)
                elif d < 1:
                    alpha = clamp(1 - d, 0, 1)
                    blended = list(color)
                    blended[3] = round(color[3] * alpha)
                    set_pixel(pixels, px, py, w, h, tuple(blended))


# ── icon design ─────────────────────────────────────────────────
def create_icon_pixels(size: int) -> bytes:
    w = h = size
    pixels = bytearray(w * h * 4)  # pre-filled with 0 = fully transparent

    M = size / 256.0  # scale multiplier
    def s(v: float) -> int:
        return round(v * M)

    # Colours
    BLUE_A = (0, 130, 220, 255)   # lighter blue
    BLUE_B = (0, 80, 170, 255)    # darker blue
    FILE_BG = (225, 235, 248, 255)  # light blue-gray
    FILE_WHITE = (255, 255, 255, 255)
    LINE_COLOR = (185, 200, 220, 255)
    GLASS_WHITE = (255, 255, 255, 230)
    GLASS_SHD = (255, 255, 255, 70)

    # ── 1. Background rounded rect (vertical gradient) ──
    margin = s(12)
    rr_x = margin
    rr_y = margin
    rr_w = size - 2 * margin
    rr_h = size - 2 * margin
    radius = s(40)

    # Fill background with gradient and rounded corners
    for py in range(rr_y, rr_y + rr_h):
        t = (py - rr_y) / rr_h  # 0→1 top→bottom
        bg_col = lerp_color(BLUE_A, BLUE_B, t)
        for px in range(rr_x, rr_x + rr_w):
            # Check corner distance
            in_corner = False
            d = 999
            if px < rr_x + radius and py < rr_y + radius:
                d = math.sqrt((px - (rr_x + radius)) ** 2 + (py - (rr_y + radius)) ** 2) - radius
                in_corner = True
            elif px >= rr_x + rr_w - radius and py < rr_y + radius:
                d = math.sqrt((px - (rr_x + rr_w - radius)) ** 2 + (py - (rr_y + radius)) ** 2) - radius
                in_corner = True
            elif px < rr_x + radius and py >= rr_y + rr_h - radius:
                d = math.sqrt((px - (rr_x + radius)) ** 2 + (py - (rr_y + rr_h - radius)) ** 2) - radius
                in_corner = True
            elif px >= rr_x + rr_w - radius and py >= rr_y + rr_h - radius:
                d = math.sqrt((px - (rr_x + rr_w - radius)) ** 2 + (py - (rr_y + rr_h - radius)) ** 2) - radius
                in_corner = True

            if not in_corner:
                # Full body
                set_pixel(pixels, px, py, w, h, bg_col)
            elif d < -0.5:
                set_pixel(pixels, px, py, w, h, bg_col)
            elif d < 0.5:
                alpha = clamp((0.5 - d), 0, 1)
                blended = list(bg_col)
                blended[3] = round(bg_col[3] * alpha)
                set_pixel(pixels, px, py, w, h, tuple(blended))

    # ── 2. Document silhouettes ──
    doc_w = s(90)
    doc_h = s(122)
    corner = s(8)

    # Document 1 (back, offset)
    d1x = s(70)
    d1y = s(66)
    fill_rounded_rect(pixels, d1x, d1y, doc_w, doc_h, corner, w, h, FILE_BG)

    # Document 2 (front)
    d2x = s(104)
    d2y = s(92)
    fill_rounded_rect(pixels, d2x, d2y, doc_w, doc_h, corner, w, h, FILE_WHITE)

    # Text lines on both documents
    line_thick = max(s(1), 1)
    for fx, fy in [(d1x, d1y), (d2x, d2y)]:
        for i in range(4):
            ly = fy + s(38) + i * s(18)
            lx0 = fx + s(16)
            lx1 = fx + doc_w - s(16)
            draw_line(pixels, lx0, ly, lx1, ly, w, h, LINE_COLOR, line_thick)

    # ── 3. Magnifying glass ──
    gcx = s(180)
    gcy = s(120)
    gr = s(50)

    # Glass circle (outline + fill)
    draw_circle_outline(pixels, gcx, gcy, gr, w, h, GLASS_WHITE, max(s(4), 2))

    # Inner fill
    fill_circle(pixels, gcx, gcy, gr - max(s(4), 2), w, h, (255, 255, 255, 160))

    # Glass highlight
    hl_r = s(16)
    fill_circle(pixels, gcx - s(10), gcy - s(10), hl_r, w, h, GLASS_SHD)

    # Handle
    hx0 = gcx + round(gr * 0.65)
    hy0 = gcy + round(gr * 0.65)
    hx1 = gcx + round(gr * 1.5)
    hy1 = gcy + round(gr * 1.5)
    draw_line(pixels, hx0, hy0, hx1, hy1, w, h, GLASS_WHITE, max(s(6), 2))

    return bytes(pixels)


# ── ICO container format ───────────────────────────────────────
def create_ico(size: int) -> bytes:
    pixels = create_icon_pixels(size)

    # BITMAPINFOHEADER (40 bytes) — for ICO, height is double
    bih = struct.pack(
        '<IiiHHIIiiII',
        40,              # biSize
        size,            # biWidth
        size * 2,        # biHeight (doubled — XOR + AND mask convention)
        1,               # biPlanes
        32,              # biBitCount (BGRA)
        0,               # biCompression (BI_RGB)
        size * size * 4, # biSizeImage
        0, 0, 0, 0,
    )

    # ICO header: reserved(2) + type(2) + count(2)
    header = struct.pack('<HHH', 0, 1, 1)

    # Directory entry
    w_ico = 0 if size >= 256 else size
    h_ico = 0 if size >= 256 else size
    data_offset = 6 + 16  # header + 1 directory entry
    dir_entry = struct.pack(
        '<BBBBHHII',
        w_ico, h_ico,   # width, height (0 = 256)
        0, 0,           # palette colors, reserved
        1,              # color planes
        32,             # bits per pixel
        40 + size * size * 4,  # image data size (bih + pixels)
        data_offset,    # offset in file
    )

    return header + dir_entry + bih + pixels


# ── main ────────────────────────────────────────────────────────
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Rendering icon 256×256 …")
    ico_data = create_ico(256)
    with open(OUT_PATH, 'wb') as f:
        f.write(ico_data)
    print(f"Icon saved: {OUT_PATH}  ({len(ico_data)} bytes)")


if __name__ == '__main__':
    main()
