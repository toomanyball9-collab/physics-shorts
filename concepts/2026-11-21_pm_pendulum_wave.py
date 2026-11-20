"""2026-11-21 18:00 — pendulum-wave (new family): "Pendulum Wave"
16 neon pendulum balls seen from above, one per lane, swinging between two glowing walls (every wall hit
rings a note). Each ball is on a slightly shorter string than the one above, so it makes exactly ONE more
swing per minute: 24, 25, 26 … 39 round trips in 61.3 s. They start in a perfect line, drift into waves,
snakes, two / three / four interleaved groups and chaos — and because the periods are exact, all 16 come
back into one straight line and hit the wall together on the final bar (payoff). Short tail that crossfades
to the opening line for a clean loop.

Exact motion (no integration drift): harmonic swing x = A0 sin(theta), truncated and reflected by the walls
at |x| = AW (AW/A0 = 0.8). Round trip of ball n = GAMMA / (K + n). Top ball's round trip = exactly 1 bar.

usage: python3 concepts/2026-11-21_pm_pendulum_wave.py [--audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
AUDIO_ONLY = "--audio" in sys.argv
OUT = "out_noaudio.mp4"
MUSIC_SEED = 20261121 * 10 + 500 + 13
song = music.Song.from_genre("gamelan", seed=MUSIC_SEED)
N, K = 16, 24
BARS = 24
GAMMA = BARS * song.chord_len           # realignment time = exactly 24 bars
TAIL = 2.6
DUR = GAMMA + TAIL
CX = W / 2
AW = 405.0                              # wall half-distance (ball centre at contact)
A0 = AW / 0.8                           # virtual amplitude
TH_W = math.asin(0.8)
BR = 21.0
Y0, Y1 = 360.0, 1560.0
LANES = [Y0 + (Y1 - Y0) * n / (N - 1) for n in range(N)]
TAU = [GAMMA / (2 * (K + n)) for n in range(N)]   # wall-to-wall time
WALL_X = (CX - AW - BR, CX + AW + BR)
PAL = {"bg": ((0.03, 0.01, 0.07), (0.00, 0.00, 0.025)), "ring": (0.92, 0.90, 1.0), "accent": (1.0, 0.97, 0.9)}
COLS = [neon.hsv(0.0 + 0.80 * n / (N - 1), 0.72, 1.0) for n in range(N)]
fx_rng = np.random.default_rng(7)

def pos_x(n, t):
    T2 = 2 * TAU[n]
    ph = (t % T2) / T2
    if ph < 0.5:
        th = TH_W - 2 * TH_W * (ph / 0.5)
    else:
        th = -TH_W + 2 * TH_W * ((ph - 0.5) / 0.5)
    return CX + A0 * math.sin(th)

def coherence(t):
    z = sum(complex(math.cos(2 * math.pi * t / (2 * TAU[n])), math.sin(2 * math.pi * t / (2 * TAU[n]))) for n in range(N))
    return abs(z) / N

# ---------------- hits (exact) -> music ----------------
hits = []                               # (t, n, side)  side +1 right, -1 left
for n in range(N):
    m = 0
    while m * TAU[n] <= DUR + 1e-9:
        hits.append((m * TAU[n], n, 1 if m % 2 == 0 else -1))
        m += 1
hits.sort()
ht = np.array([h[0] for h in hits])
for (t, n, side) in hits:
    if t > DUR - 0.2:
        continue
    cl = int(np.sum(np.abs(ht - t) < 0.035))
    vel = 0.55 + 0.45 * min(1.0, (cl - 1) / 6)
    song.note(max(0.0, t - 1e-6), 0.75 * side, vel)
song.accent(GAMMA - 1e-6)
song.sfx(GAMMA, "chime", 0.6, 0.9)

def build(t):
    if t >= GAMMA:
        return 1.0
    x = t / GAMMA
    return min(1.0, 0.12 + 0.88 * x ** 1.25)

if AUDIO_ONLY:
    song.render("audio.wav", DUR, build=build)
    print("music", song.recipe_str(), "gamma", round(GAMMA, 3), "dur", round(DUR, 3))
    sys.exit()

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
sprites = neon.SkinSprites(COLS, int(BR), skin="orb")
trail = [[] for _ in range(N)]
first = None

def wall(x, glow_amt, t):
    y0, y1 = LANES[0] - 120, LANES[-1] + 120
    col = neon.mix(PAL["ring"], (1.0, 0.92, 0.75), 0.25 * glow_amt)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for w, a in [(46, 0.04), (28, 0.08), (16, 0.14), (9, 0.30)]:
        ctx.set_source_rgba(*col, a * (1 + 0.8 * glow_amt)); ctx.set_line_width(w)
        ctx.move_to(x, y0); ctx.line_to(x, y1); ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(*neon.mix(col, (1, 1, 1), 0.65), 0.95); ctx.set_line_width(5)
    ctx.move_to(x, y0); ctx.line_to(x, y1); ctx.stroke(); ctx.restore()

def catmull(pts, steps=8):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(steps):
            u = s / steps
            u2, u3 = u * u, u * u * u
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * u + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * u2
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * u3) for k in range(2)))
    out.append(pts[-1])
    return out

ff = subprocess.Popen([
    "ffmpeg", "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", OUT
], stdin=subprocess.PIPE)

nframes = int(round(DUR * FPS))
hi = 0
recent = []                              # (t, n, side) for glows
for f in range(nframes):
    t = f / FPS
    while hi < len(hits) and hits[hi][0] <= t + 1e-9:
        recent.append(hits[hi]); hi += 1
    recent = [h for h in recent if t - h[0] < 0.6]
    coh = coherence(t)
    b = build(t)
    pay = t - GAMMA                       # >0 after payoff
    neon.background(ctx, W, H, PAL)
    # breathing glow: grows with the build and with how aligned the line is
    ga = 0.03 + 0.07 * b + 0.10 * coh ** 6 + 0.02 * math.sin(t * 1.7)
    if pay >= 0:
        ga += 0.25 * math.exp(-pay * 2.0)
    rg = cairo.RadialGradient(CX, (Y0 + Y1) / 2, 0, CX, (Y0 + Y1) / 2, 1000)
    gc = neon.mix(COLS[int(t * 0.6) % N], PAL["accent"], 0.6)
    rg.add_color_stop_rgba(0, *gc, ga); rg.add_color_stop_rgba(1, *gc, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    if pay >= 0:
        s_ = 16 * math.exp(-pay * 7)
        ctx.translate(fx_rng.uniform(-s_, s_), fx_rng.uniform(-s_, s_))
    # lane guides
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for n in range(N):
        ctx.set_source_rgba(*COLS[n], 0.07); ctx.set_line_width(2)
        ctx.move_to(WALL_X[0], LANES[n]); ctx.line_to(WALL_X[1], LANES[n]); ctx.stroke()
    ctx.restore()
    # walls (glow with recent hits on that side)
    for si, x in ((-1, WALL_X[0]), (1, WALL_X[1])):
        g = sum(max(0, 1 - (t - h[0]) / 0.4) for h in recent if h[2] == si) / 5.0
        if pay >= 0 and si == 1:
            g += 2.0 * math.exp(-pay * 2.5)
        wall(x, min(2.5, g), t)
    # hit glows on the walls (coloured by the ball)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for (ht0, n, side) in recent:
        age = t - ht0
        if age > 0.45:
            continue
        a = 1 - age / 0.45
        x = WALL_X[1] if side > 0 else WALL_X[0]
        y = LANES[n]
        rad = 40 + 50 * (1 - a)
        gr = cairo.RadialGradient(x, y, 0, x, y, rad)
        gr.add_color_stop_rgba(0, *neon.mix(COLS[n], (1, 1, 1), 0.4), 0.85 * a); gr.add_color_stop_rgba(1, *COLS[n], 0)
        ctx.set_source(gr); ctx.arc(x, y, rad, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(*COLS[n], 0.9 * a); ctx.set_line_width(5)
        ctx.move_to(x, y - 34 * a - 8); ctx.line_to(x, y + 34 * a + 8); ctx.stroke()
    ctx.restore()
    xs = [pos_x(n, t) for n in range(N)]
    pts = [(xs[n], LANES[n]) for n in range(N)]
    # the wave line through all balls
    curve = catmull(pts, 10)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    seg = len(curve) - 1
    for i in range(seg):
        c = COLS[min(N - 1, int(i / seg * N))]
        for w, a in [(12, 0.06), (3, 0.30 + 0.35 * coh ** 4)]:
            ctx.set_source_rgba(*c, a); ctx.set_line_width(w)
            ctx.move_to(*curve[i]); ctx.line_to(*curve[i + 1]); ctx.stroke()
    ctx.restore()
    # short trails
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    for n in range(N):
        trail[n].append(xs[n]); trail[n] = trail[n][-14:]
        tr = trail[n]
        for i in range(1, len(tr)):
            a = i / len(tr)
            ctx.set_source_rgba(*COLS[n], 0.20 * a * a); ctx.set_line_width(BR * 0.9 * a)
            ctx.move_to(tr[i - 1], LANES[n]); ctx.line_to(tr[i], LANES[n]); ctx.stroke()
    ctx.restore()
    sprites.draw(ctx, pts, list(range(N)))
    # payoff: shockwave sweeping from the right wall + sparkles along it
    if 0 <= pay < 1.3:
        a = 1 - pay / 1.3
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        x = WALL_X[1] - 1400 * pay
        ctx.set_source_rgba(*PAL["accent"], 0.55 * a); ctx.set_line_width(4 + 18 * a)
        ctx.move_to(x, LANES[0] - 140); ctx.line_to(x, LANES[-1] + 140); ctx.stroke()
        ctx.restore()
        sp = [(WALL_X[1] + fx_rng.normal(0, 30) + 260 * pay * fx_rng.random(), LANES[n] + fx_rng.normal(0, 26),
               fx_rng.uniform(8, 22) * a) for n in range(N) for _ in range(3)]
        neon.sparkles(ctx, sp, (1, 1, 1), alpha=0.9 * a)
    ctx.restore()
    if 0 <= pay < 0.14:
        ctx.set_source_rgba(1, 1, 1, 0.28 * (1 - pay / 0.14)); ctx.paint()
    # loop: crossfade to the opening line
    xf = (t - (DUR - 1.2)) / 1.2
    if xf > 0 and first is not None:
        ctx.set_source_surface(first, 0, 0); ctx.paint_with_alpha(min(1.0, xf) ** 1.5)
    surf.flush()
    if first is None:
        first = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        c2 = cairo.Context(first); c2.set_source_surface(surf, 0, 0); c2.paint()
    ff.stdin.write(bytes(surf.get_data()))

ff.stdin.close(); ff.wait()
song.render("audio.wav", DUR, build=build)
print("music", song.recipe_str(), "gamma", round(GAMMA, 3), "dur", round(DUR, 3), "hits", len(hits))
