"""Shared neon rendering helpers for physics-shorts (pycairo).

Usage:
    import neon
    pal = neon.PALETTES["synthwave"]
    sprites = neon.BallSprites(pal["balls"], radius=14)
    neon.background(ctx, W, H, pal)              # or neon.fade(ctx, W, H, pal, 0.35) for light trails
    neon.ring(ctx, cx, cy, R, pal["ring"], t, heat=0.0)
    sprites.draw(ctx, positions, color_indices)  # glow (additive) + glossy cores
"""
import math
import cairo

PALETTES = {
    # bg_top, bg_bottom, ring, balls (list), accent
    "synthwave": {"bg": ((0.03, 0.01, 0.10), (0.01, 0.00, 0.04)), "ring": (1.0, 0.25, 0.85),
                  "balls": [(1.0, 0.25, 0.85), (0.20, 0.90, 1.0), (0.60, 0.35, 1.0), (1.0, 0.55, 0.20)],
                  "accent": (1.0, 0.85, 0.30)},
    "aurora": {"bg": ((0.00, 0.04, 0.08), (0.00, 0.01, 0.03)), "ring": (0.30, 1.0, 0.75),
               "balls": [(0.30, 1.0, 0.75), (0.25, 0.70, 1.0), (0.65, 0.45, 1.0), (0.85, 1.0, 0.45)],
               "accent": (0.85, 1.0, 0.90)},
    "sunset": {"bg": ((0.08, 0.02, 0.08), (0.02, 0.01, 0.03)), "ring": (1.0, 0.50, 0.25),
               "balls": [(1.0, 0.35, 0.35), (1.0, 0.60, 0.20), (1.0, 0.85, 0.35), (1.0, 0.40, 0.70)],
               "accent": (1.0, 0.90, 0.60)},
    "ocean": {"bg": ((0.00, 0.03, 0.10), (0.00, 0.01, 0.04)), "ring": (0.25, 0.75, 1.0),
              "balls": [(0.20, 0.60, 1.0), (0.20, 0.95, 1.0), (0.45, 1.0, 0.85), (0.70, 0.55, 1.0)],
              "accent": (0.80, 0.95, 1.0)},
    "spectrum": {"bg": ((0.02, 0.02, 0.06), (0.00, 0.00, 0.02)), "ring": (0.95, 0.95, 1.0),
                 "balls": [(1.0, 0.25, 0.30), (1.0, 0.60, 0.15), (1.0, 0.95, 0.25), (0.30, 1.0, 0.45),
                           (0.20, 0.85, 1.0), (0.35, 0.45, 1.0), (0.80, 0.35, 1.0)],
                 "accent": (1.0, 1.0, 1.0)},
    "mono-ice": {"bg": ((0.01, 0.02, 0.05), (0.00, 0.00, 0.02)), "ring": (0.75, 0.90, 1.0),
                 "balls": [(0.75, 0.90, 1.0), (0.55, 0.80, 1.0), (0.95, 0.98, 1.0)],
                 "accent": (1.0, 0.75, 0.30)},
}


def hsv(h, s=0.85, v=1.0):
    i = int(h * 6) % 6; f = h * 6 - int(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    return [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i]


def mix(a, b, k):
    return tuple(a[i] * (1 - k) + b[i] * k for i in range(3))


def background(ctx, W, H, pal, vignette=True):
    top, bot = pal["bg"]
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *top); g.add_color_stop_rgb(1, *bot)
    ctx.set_source(g); ctx.paint()
    if vignette:
        v = cairo.RadialGradient(W / 2, H / 2, min(W, H) * 0.3, W / 2, H / 2, max(W, H) * 0.75)
        v.add_color_stop_rgba(0, 0, 0, 0, 0); v.add_color_stop_rgba(1, 0, 0, 0, 0.55)
        ctx.set_source(v); ctx.paint()


def fade(ctx, W, H, pal, alpha):
    """Paint the background at partial opacity instead of clearing -> light trails."""
    top, bot = pal["bg"]
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgba(0, *top, alpha); g.add_color_stop_rgba(1, *bot, alpha)
    ctx.set_source(g); ctx.paint()


def ring(ctx, cx, cy, R, rgb, t=0.0, heat=0.0, width=5.0):
    """Neon tube ring. heat 0..1 shifts to red and pulses (tension before a burst)."""
    col = mix(rgb, (1.0, 0.18, 0.22), heat)
    pulse = 1.0 + heat * 0.6 * (0.5 + 0.5 * math.sin(t * 26))
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_ADD)
    for w, a in [(46, 0.05), (28, 0.09), (16, 0.16), (9, 0.35)]:
        ctx.set_source_rgba(*col, a * pulse); ctx.set_line_width(w * pulse)
        ctx.arc(cx, cy, R, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
    ctx.set_source_rgba(*mix(col, (1, 1, 1), 0.65), 0.95); ctx.set_line_width(width)
    ctx.arc(cx, cy, R, 0, 2 * math.pi); ctx.stroke()


def polygon_ring(ctx, pts, rgb, heat=0.0, t=0.0, width=5.0):
    col = mix(rgb, (1.0, 0.18, 0.22), heat)
    pulse = 1.0 + heat * 0.6 * (0.5 + 0.5 * math.sin(t * 26))
    def path():
        ctx.move_to(*pts[0])
        for p in pts[1:]: ctx.line_to(*p)
        ctx.close_path()
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for w, a in [(46, 0.05), (28, 0.09), (16, 0.16), (9, 0.35)]:
        ctx.set_source_rgba(*col, a * pulse); ctx.set_line_width(w * pulse); path(); ctx.stroke()
    ctx.restore()
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_source_rgba(*mix(col, (1, 1, 1), 0.65), 0.95); ctx.set_line_width(width); path(); ctx.stroke()


class BallSprites:
    """Pre-rendered glow + glossy core per colour, so thousands of balls stay fast."""

    def __init__(self, colors, radius, glow=3.2, glow_alpha=0.55):
        self.r = radius
        self.colors = colors
        self.glow, self.core = [], []
        for c in colors:
            self.glow.append(self._glow_sprite(c, radius, glow, glow_alpha))
            self.core.append(self._core_sprite(c, radius))

    @staticmethod
    def _glow_sprite(c, r, k, a):
        G = int(r * k)
        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2 * G, 2 * G)
        x = cairo.Context(s)
        g = cairo.RadialGradient(G, G, r * 0.4, G, G, G)
        g.add_color_stop_rgba(0, *c, a); g.add_color_stop_rgba(0.35, *c, a * 0.35); g.add_color_stop_rgba(1, *c, 0)
        x.set_source(g); x.paint()
        return s, G

    @staticmethod
    def _core_sprite(c, r):
        P = int(r + 3)
        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2 * P, 2 * P)
        x = cairo.Context(s)
        g = cairo.RadialGradient(P - r * 0.35, P - r * 0.40, r * 0.05, P, P, r)
        g.add_color_stop_rgb(0, *mix(c, (1, 1, 1), 0.85))
        g.add_color_stop_rgb(0.45, *mix(c, (1, 1, 1), 0.25))
        g.add_color_stop_rgb(1, *mix(c, (0, 0, 0), 0.35))
        x.set_source(g); x.arc(P, P, r, 0, 2 * math.pi); x.fill()
        x.set_source_rgba(*mix(c, (1, 1, 1), 0.7), 0.9); x.set_line_width(max(1.0, r * 0.10))
        x.arc(P, P, r - r * 0.05, 0, 2 * math.pi); x.stroke()
        x.set_source_rgba(1, 1, 1, 0.75)
        x.save(); x.translate(P - r * 0.38, P - r * 0.42); x.rotate(-0.5); x.scale(r * 0.30, r * 0.18)
        x.arc(0, 0, 1, 0, 2 * math.pi); x.restore(); x.fill()
        return s, P

    def draw(self, ctx, positions, color_idx, scale=1.0, glow=True):
        if glow:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            for (x, y), ci in zip(positions, color_idx):
                s, G = self.glow[ci % len(self.glow)]
                ctx.set_source_surface(s, x - G, y - G); ctx.paint()
            ctx.restore()
        for (x, y), ci in zip(positions, color_idx):
            s, P = self.core[ci % len(self.core)]
            ctx.set_source_surface(s, x - P, y - P); ctx.paint()


def sparkles(ctx, pts, rgb, alpha=0.8):
    """Tiny 4-point neon sparks (bursts, hits)."""
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for x, y, r in pts:
        ctx.set_source_rgba(*rgb, alpha)
        ctx.move_to(x, y - r); ctx.line_to(x + r * 0.2, y - r * 0.2); ctx.line_to(x + r, y)
        ctx.line_to(x + r * 0.2, y + r * 0.2); ctx.line_to(x, y + r); ctx.line_to(x - r * 0.2, y + r * 0.2)
        ctx.line_to(x - r, y); ctx.line_to(x - r * 0.2, y - r * 0.2); ctx.close_path(); ctx.fill()
    ctx.restore()


# ---------------------------------------------------------------------------
# Seasonal skins: drop-in replacement for the glossy core (physics stays a circle).
#   SkinSprites(colors, radius, skin="pumpkin").draw(ctx, positions, color_idx, angles=None)
# Skins: orb, pumpkin, snowflake, ornament, heart, clover, egg, lantern, blossom, star,
#        firework, leaf, beachball, moon, earth
# ---------------------------------------------------------------------------
SKINS = ["orb", "pumpkin", "snowflake", "ornament", "heart", "clover", "egg", "lantern",
         "blossom", "star", "firework", "leaf", "beachball", "moon", "earth"]


def _heart_path(x, s):
    x.move_to(0, 0.35 * s)
    x.curve_to(-1.1 * s, -0.35 * s, -0.45 * s, -1.05 * s, 0, -0.45 * s)
    x.curve_to(0.45 * s, -1.05 * s, 1.1 * s, -0.35 * s, 0, 0.35 * s)
    x.close_path()


def _draw_skin(x, skin, c, r):
    W2 = (1, 1, 1)
    if skin == "orb":
        g = cairo.RadialGradient(-r * 0.35, -r * 0.4, r * 0.05, 0, 0, r)
        g.add_color_stop_rgb(0, *mix(c, W2, 0.85)); g.add_color_stop_rgb(0.45, *mix(c, W2, 0.25))
        g.add_color_stop_rgb(1, *mix(c, (0, 0, 0), 0.35))
        x.set_source(g); x.arc(0, 0, r, 0, 2 * math.pi); x.fill()
        x.set_source_rgba(*mix(c, W2, 0.7), 0.9); x.set_line_width(max(1, r * 0.1)); x.arc(0, 0, r * 0.95, 0, 2 * math.pi); x.stroke()
        x.save(); x.translate(-r * 0.38, -r * 0.42); x.rotate(-0.5); x.scale(r * 0.3, r * 0.18)
        x.set_source_rgba(1, 1, 1, 0.75); x.arc(0, 0, 1, 0, 2 * math.pi); x.restore(); x.fill()
    elif skin == "pumpkin":
        org = (1.0, 0.50, 0.08)
        for k, dx in enumerate((-0.45, 0.45, -0.2, 0.2, 0.0)):
            x.save(); x.translate(dx * r, r * 0.05); x.scale(0.55 if k < 4 else 0.6, 0.9)
            g = cairo.RadialGradient(-r * 0.3, -r * 0.35, r * 0.1, 0, 0, r)
            g.add_color_stop_rgb(0, *mix(org, W2, 0.35)); g.add_color_stop_rgb(1, *mix(org, (0, 0, 0), 0.3))
            x.set_source(g); x.arc(0, 0, r, 0, 2 * math.pi); x.fill(); x.restore()
        x.set_source_rgb(0.25, 0.45, 0.12); x.rectangle(-r * 0.09, -r * 1.05, r * 0.18, r * 0.32); x.fill()
        glow = (1.0, 0.95, 0.45)
        x.set_source_rgb(*glow)
        for sx in (-1, 1):
            x.move_to(sx * r * 0.42, -r * 0.05); x.line_to(sx * r * 0.18, -r * 0.05); x.line_to(sx * r * 0.30, -r * 0.32); x.close_path(); x.fill()
        x.move_to(-r * 0.5, r * 0.22); x.line_to(-r * 0.3, r * 0.42); x.line_to(-r * 0.12, r * 0.28); x.line_to(0, r * 0.45)
        x.line_to(r * 0.12, r * 0.28); x.line_to(r * 0.3, r * 0.42); x.line_to(r * 0.5, r * 0.22); x.line_to(0, r * 0.32); x.close_path(); x.fill()
    elif skin == "snowflake":
        col = mix(c, W2, 0.6)
        x.set_line_cap(cairo.LINE_CAP_ROUND)
        for k in range(6):
            x.save(); x.rotate(k * math.pi / 3)
            x.set_source_rgb(*col); x.set_line_width(max(1.5, r * 0.14))
            x.move_to(0, 0); x.line_to(0, -r); x.stroke()
            x.set_line_width(max(1.2, r * 0.10))
            for f in (0.45, 0.72):
                x.move_to(0, -r * f); x.line_to(-r * 0.22, -r * (f + 0.18)); x.move_to(0, -r * f); x.line_to(r * 0.22, -r * (f + 0.18)); x.stroke()
            x.restore()
        x.set_source_rgb(1, 1, 1); x.arc(0, 0, r * 0.14, 0, 2 * math.pi); x.fill()
    elif skin == "ornament":
        _draw_skin(x, "orb", c, r * 0.92)
        x.set_source_rgba(*mix(c, W2, 0.6), 0.9); x.set_line_width(max(1, r * 0.12))
        x.move_to(-r * 0.85, r * 0.1); x.curve_to(-r * 0.3, r * 0.35, r * 0.3, r * 0.35, r * 0.85, r * 0.1); x.stroke()
        x.set_source_rgb(0.95, 0.80, 0.35); x.rectangle(-r * 0.22, -r * 1.12, r * 0.44, r * 0.26); x.fill()
        x.set_line_width(max(1, r * 0.08)); x.arc(0, -r * 1.2, r * 0.12, 0, 2 * math.pi); x.stroke()
    elif skin == "heart":
        g = cairo.RadialGradient(-r * 0.3, -r * 0.5, r * 0.05, 0, -r * 0.1, r * 1.1)
        g.add_color_stop_rgb(0, *mix(c, W2, 0.8)); g.add_color_stop_rgb(0.5, *c); g.add_color_stop_rgb(1, *mix(c, (0, 0, 0), 0.35))
        x.save(); x.translate(0, r * 0.25); _heart_path(x, r * 1.15); x.set_source(g); x.fill_preserve()
        x.set_source_rgba(*mix(c, W2, 0.7), 0.9); x.set_line_width(max(1, r * 0.08)); x.stroke(); x.restore()
    elif skin == "clover":
        col = (0.25, 0.85, 0.40)
        for k in range(3):
            x.save(); x.rotate(k * 2 * math.pi / 3); x.translate(0, -r * 0.45)
            _heart_path(x, r * 0.55)
            g = cairo.RadialGradient(0, -r * 0.2, r * 0.05, 0, 0, r * 0.6)
            g.add_color_stop_rgb(0, *mix(col, W2, 0.5)); g.add_color_stop_rgb(1, *mix(col, (0, 0, 0), 0.3))
            x.set_source(g); x.fill(); x.restore()
        x.set_source_rgb(0.2, 0.6, 0.25); x.set_line_width(max(1, r * 0.12)); x.move_to(0, 0); x.curve_to(r * 0.1, r * 0.5, r * 0.3, r * 0.8, r * 0.35, r * 1.0); x.stroke()
    elif skin == "egg":
        x.save(); x.scale(0.82, 1.0)
        g = cairo.RadialGradient(-r * 0.3, -r * 0.4, r * 0.05, 0, 0, r * 1.05)
        g.add_color_stop_rgb(0, *mix(c, W2, 0.85)); g.add_color_stop_rgb(1, *mix(c, W2, 0.1))
        x.set_source(g); x.arc(0, 0, r, 0, 2 * math.pi); x.fill(); x.restore()
        x.set_source_rgba(*mix(c, (0, 0, 0), 0.25), 0.8); x.set_line_width(max(1, r * 0.12))
        x.move_to(-r * 0.75, -r * 0.1)
        for k in range(6): x.line_to(-r * 0.75 + (k + 0.5) * r * 0.25, -r * (0.25 if k % 2 == 0 else -0.05))
        x.stroke()
        x.set_source_rgba(1, 1, 1, 0.7)
        for dx in (-0.35, 0.0, 0.35): x.arc(dx * r, r * 0.4, r * 0.09, 0, 2 * math.pi); x.fill()
    elif skin == "lantern":
        red = (0.95, 0.15, 0.15)
        x.save(); x.scale(1.0, 0.85)
        g = cairo.RadialGradient(0, 0, r * 0.1, 0, 0, r)
        g.add_color_stop_rgb(0, 1.0, 0.75, 0.35); g.add_color_stop_rgb(0.6, *red); g.add_color_stop_rgb(1, *mix(red, (0, 0, 0), 0.35))
        x.set_source(g); x.arc(0, 0, r, 0, 2 * math.pi); x.fill(); x.restore()
        x.set_source_rgba(0.6, 0.05, 0.05, 0.6); x.set_line_width(max(1, r * 0.06))
        for dx in (-0.5, 0, 0.5):
            x.save(); x.scale(1.0, 0.85); x.move_to(dx * r, -r * 0.95); x.curve_to(dx * r * 1.6, -r * 0.3, dx * r * 1.6, r * 0.3, dx * r, r * 0.95); x.restore(); x.stroke()
        x.set_source_rgb(0.98, 0.78, 0.25)
        x.rectangle(-r * 0.45, -r * 0.98, r * 0.9, r * 0.18); x.fill(); x.rectangle(-r * 0.45, r * 0.8, r * 0.9, r * 0.18); x.fill()
        x.set_line_width(max(1, r * 0.08)); x.move_to(0, r * 0.98); x.line_to(0, r * 1.3); x.stroke()
    elif skin == "blossom":
        pink = mix(c, (1.0, 0.75, 0.85), 0.6)
        for k in range(5):
            x.save(); x.rotate(k * 2 * math.pi / 5); x.translate(0, -r * 0.5); x.scale(0.55, 0.62)
            g = cairo.RadialGradient(0, r * 0.4, r * 0.1, 0, 0, r)
            g.add_color_stop_rgb(0, 1, 0.95, 0.97); g.add_color_stop_rgb(1, *pink)
            x.set_source(g); x.arc(0, 0, r, 0, 2 * math.pi); x.fill(); x.restore()
        x.set_source_rgb(1.0, 0.85, 0.35); x.arc(0, 0, r * 0.2, 0, 2 * math.pi); x.fill()
    elif skin == "star":
        x.new_path()
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5; rr = r * (1.05 if k % 2 == 0 else 0.45)
            (x.move_to if k == 0 else x.line_to)(rr * math.cos(a), rr * math.sin(a))
        x.close_path()
        g = cairo.RadialGradient(-r * 0.2, -r * 0.3, r * 0.05, 0, 0, r)
        g.add_color_stop_rgb(0, *mix(c, W2, 0.85)); g.add_color_stop_rgb(1, *c)
        x.set_source(g); x.fill()
    elif skin == "firework":
        x.set_line_cap(cairo.LINE_CAP_ROUND)
        for k in range(12):
            a = k * math.pi / 6
            x.set_source_rgba(*mix(c, W2, 0.4), 0.95); x.set_line_width(max(1, r * 0.1))
            x.move_to(r * 0.25 * math.cos(a), r * 0.25 * math.sin(a)); x.line_to(r * math.cos(a), r * math.sin(a)); x.stroke()
            x.set_source_rgb(1, 1, 1); x.arc(r * math.cos(a), r * math.sin(a), r * 0.08, 0, 2 * math.pi); x.fill()
        x.arc(0, 0, r * 0.18, 0, 2 * math.pi); x.fill()
    elif skin == "leaf":
        col = mix(c, (0.95, 0.45, 0.10), 0.5)
        x.save(); x.rotate(0.6)
        x.move_to(0, -r); x.curve_to(r * 0.9, -r * 0.4, r * 0.7, r * 0.6, 0, r); x.curve_to(-r * 0.7, r * 0.6, -r * 0.9, -r * 0.4, 0, -r); x.close_path()
        g = cairo.LinearGradient(0, -r, 0, r); g.add_color_stop_rgb(0, *mix(col, (1, 0.9, 0.3), 0.4)); g.add_color_stop_rgb(1, *mix(col, (0.5, 0.1, 0.05), 0.4))
        x.set_source(g); x.fill()
        x.set_source_rgba(0.4, 0.15, 0.05, 0.8); x.set_line_width(max(1, r * 0.07)); x.move_to(0, -r * 0.9); x.line_to(0, r * 1.15); x.stroke(); x.restore()
    elif skin == "beachball":
        cols = [(1, 0.25, 0.3), (1, 1, 1), (0.2, 0.6, 1), (1, 1, 1), (1, 0.85, 0.2), (1, 1, 1)]
        for k, cc in enumerate(cols):
            x.move_to(0, 0); x.arc(0, 0, r, k * math.pi / 3, (k + 1) * math.pi / 3); x.close_path(); x.set_source_rgb(*cc); x.fill()
        g = cairo.RadialGradient(-r * 0.35, -r * 0.4, r * 0.05, 0, 0, r)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.55); g.add_color_stop_rgba(0.5, 1, 1, 1, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.35)
        x.set_source(g); x.arc(0, 0, r, 0, 2 * math.pi); x.fill()
    elif skin == "moon":
        g = cairo.RadialGradient(-r * 0.3, -r * 0.35, r * 0.05, 0, 0, r)
        g.add_color_stop_rgb(0, 1, 0.99, 0.94); g.add_color_stop_rgb(1, 0.72, 0.69, 0.60)
        x.set_source(g); x.arc(0, 0, r, 0, 2 * math.pi); x.fill()
        x.set_source_rgba(0.55, 0.52, 0.45, 0.45)
        for dx, dy, rr in ((-0.3, -0.2, 0.22), (0.3, 0.1, 0.28), (-0.1, 0.45, 0.16), (0.35, -0.45, 0.12)):
            x.arc(dx * r, dy * r, rr * r, 0, 2 * math.pi); x.fill()
    elif skin == "earth":
        g = cairo.RadialGradient(-r * 0.3, -r * 0.35, r * 0.05, 0, 0, r)
        g.add_color_stop_rgb(0, 0.45, 0.75, 1); g.add_color_stop_rgb(1, 0.05, 0.25, 0.6)
        x.set_source(g); x.arc(0, 0, r, 0, 2 * math.pi); x.fill()
        x.set_source_rgb(0.25, 0.75, 0.35)
        for dx, dy, rx, ry in ((-0.35, -0.25, 0.35, 0.25), (0.3, 0.2, 0.3, 0.35), (-0.1, 0.55, 0.2, 0.12)):
            x.save(); x.translate(dx * r, dy * r); x.scale(rx * r, ry * r); x.arc(0, 0, 1, 0, 2 * math.pi); x.restore(); x.fill()
    else:
        raise ValueError(skin)


class SkinSprites(BallSprites):
    """Same API as BallSprites but with a themed shape for the core."""

    def __init__(self, colors, radius, skin="orb", glow=3.2, glow_alpha=0.5):
        self.skin = skin
        super().__init__(colors, radius, glow, glow_alpha)

    def _core_sprite(self, c, r):
        P = int(r * 1.5 + 4)
        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2 * P, 2 * P)
        x = cairo.Context(s); x.translate(P, P)
        _draw_skin(x, self.skin, c, r)
        return s, P
