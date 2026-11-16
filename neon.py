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
