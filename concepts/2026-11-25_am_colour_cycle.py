"""2026-11-25 08:00 — color-battle (new family): "Colour Cycle"
Three neon colours bounce inside a ring (zero gravity, real elastic collisions).
  Rule: PINK beats GOLD, GOLD beats CYAN, CYAN beats PINK — when two balls touch, the winner turns the other
        into its own colour (legend at the top: three dots with arrows).
Every ball paints the floor tiles it rolls over, so the battle leaves swirling colour fronts behind it.
When a colour is wiped out, the colour it used to beat has no enemy left — and the cycle collapses: the
survivor that beats it takes over. When the last ball is converted, on the next bar the floor floods in the
winner's colour (wave from the last conversion), ring flash + shockwave + accent; tail crossfades to the opening.
Ring bounces = music (song.note); conversions = soft pop; extinction = zap.

usage: python3 concepts/2026-11-25_am_colour_cycle.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 4
CX, CY = W / 2, 960.0
R = 470.0
C = 18.0                                      # paint tile size
BR = float(os.environ.get("BR", "8"))
SPEED = float(os.environ.get("SPEED", "380"))
NPER = int(os.environ.get("NPER", "40"))
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
MUSIC_SEED = int(os.environ.get("MSEED", "2026112501"))
RECENT = [dict(genre="space", bpm=88, key="G", mode="dorian", lead="glass"),
          dict(genre="citypop", bpm=102, key="E", mode="major", lead="ep"),
          dict(genre="tropical", bpm=112, key="A", mode="major", lead="marimba"),
          dict(genre="musicbox", bpm=95, key="E", mode="harmonic_minor", lead="celesta"),
          dict(genre="cinematic", bpm=78, key="A#", mode="minor", lead="harp"),
          dict(genre="waltz", bpm=93, key="D", mode="major", lead="ep"),
          dict(genre="synthwave", bpm=104, key="G#", mode="dorian", lead="saw"),
          dict(genre="gamelan", bpm=94, key="D#", mode="major", lead="bell"),
          dict(genre="lofi", bpm=74, key="F#", mode="major", lead="kalimba"),
          dict(genre="celtic", bpm=116, key="A#", mode="mixolydian", lead="flute"),
          dict(genre="jazzhop", bpm=89, key="C", mode="major", lead="harp"),
          dict(genre="trance_lite", bpm=123, key="F", mode="minor", lead="pluck"),
          dict(genre="bossa", bpm=96, key="G#", mode="major", lead="ep"),
          dict(genre="space", bpm=76, key="B", mode="lydian", lead="bell")]
song = music.random_song(MUSIC_SEED, avoid=RECENT)

TEAM = [(1.0, 0.30, 0.62), (1.0, 0.78, 0.25), (0.25, 0.88, 1.0)]     # pink, gold, cyan
NAMES = ["pink", "gold", "cyan"]
BEATS = [1, 2, 0]                                                     # pink>gold, gold>cyan, cyan>pink
RING_COL = (0.85, 0.88, 1.0)
PAL = {"bg": ((0.02, 0.01, 0.06), (0.00, 0.00, 0.02)), "ring": RING_COL, "balls": TEAM, "accent": (1, 1, 1)}

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)

# ---------------- paint tiles ----------------
NX = int(2 * R / C) + 2
X0, Y0 = CX - NX * C / 2, CY - NX * C / 2
GXC, GYC = np.meshgrid(X0 + (np.arange(NX) + 0.5) * C, Y0 + (np.arange(NX) + 0.5) * C)
inside = np.hypot(GXC - CX, GYC - CY) < R - C * 0.7
paint = -np.ones((NX, NX), int)
paint_t = np.full((NX, NX), -99.0)
ROT0 = -math.pi / 2
ang = (np.arctan2(GYC - CY, GXC - CX) - ROT0) % (2 * math.pi)
paint[inside] = (ang[inside] // (2 * math.pi / 3)).astype(int)

# ---------------- balls: three clean wedges ----------------
P, T = [], []
for k in range(3):
    placed = 0
    tries = 0
    while placed < NPER and tries < 20000:
        tries += 1
        a = ROT0 + (k + rng.uniform(0.12, 0.88)) * 2 * math.pi / 3
        rr = math.sqrt(rng.uniform(0.04, 0.9)) * (R - BR - 4)
        q = (CX + rr * math.cos(a), CY + rr * math.sin(a))
        if all(math.hypot(q[0] - x, q[1] - y) > 2 * BR + 6 for x, y in P):
            P.append(q); T.append(k); placed += 1
P = np.array(P); T = np.array(T)
th = rng.uniform(0, 2 * math.pi, len(P))
V = np.stack([np.cos(th), np.sin(th)], 1) * SPEED
N = len(P)
conv_t = np.full(N, -9.0)
ring_cool = np.full(N, -9.0)

t = 0.0
alive_team = [True] * 3
out_t = [None] * 3
winner = None
win_t = None
payoff_pending = payoff_t = None
last_xy = (CX, CY)
events, sparks, build_keys = [], [], []
convs = 0

def counts():
    return np.array([(T == k).sum() for k in range(3)])

def progress():
    if payoff_t is not None:
        return 1.0
    c = counts()
    alive = sum(alive_team)
    lo = c[c > 0].min() if alive > 1 else 0
    k = 1 - lo / NPER
    stage = {3: 0.0, 2: 0.55, 1: 1.0}[alive]
    return float(np.clip(0.12 * min(1, t / 6) + 0.55 * max(stage, 0.8 * k) + 0.33 * min(1, t / 60), 0, 1))

def convert(i, k):
    """ball i becomes colour k."""
    global convs, last_xy
    old = int(T[i])
    T[i] = k
    conv_t[i] = t
    convs += 1
    last_xy = (float(P[i, 0]), float(P[i, 1]))
    song.sfx(t, "pop", float((P[i, 0] - CX) / R), 0.32)
    events.append((t, "conv", (i, k)))
    for _ in range(5):
        sparks.append([P[i, 0] + rng.normal(0, 7), P[i, 1] + rng.normal(0, 7), rng.uniform(6, 13), t, TEAM[k]])
    if alive_team[old] and (T == old).sum() == 0:
        alive_team[old] = False
        out_t[old] = t
        song.sfx(t + 0.03, "zap", 0.0, 0.7)
        events.append((t, "out", (old,)))

def physics_step(dt):
    global P, V, winner, win_t, payoff_pending
    P += V * dt
    # keep speed constant-ish (no friction in this world)
    sp = np.hypot(V[:, 0], V[:, 1]) + 1e-9
    V *= (1 + (SPEED / sp - 1) * 0.6 * dt)[:, None]
    # ring
    d = P - (CX, CY)
    dc = np.hypot(d[:, 0], d[:, 1]) + 1e-9
    for i in np.where(dc > R - BR)[0]:
        u = d[i] / dc[i]
        P[i] -= (dc[i] - (R - BR)) * u
        vn = V[i] @ u
        if vn > 0:
            V[i] -= 2 * vn * u
            if t - ring_cool[i] > 0.15:
                ring_cool[i] = t
                song.note(t, float(u[0]), vel=0.5 + 0.4 * min(1, vn / SPEED))
                events.append((t, "ring", (float(CX + u[0] * R), float(CY + u[1] * R), int(T[i]))))
    # collisions (elastic, equal mass) + conversions
    d = P[None, :, :] - P[:, None, :]
    dd = np.hypot(d[..., 0], d[..., 1])
    ii, jj = np.where(np.triu(dd < 2 * BR, 1))
    for i, j in zip(ii, jj):
        nrm = (P[j] - P[i]) / (dd[i, j] + 1e-9)
        over = 2 * BR - dd[i, j]
        P[i] -= nrm * over / 2; P[j] += nrm * over / 2
        rel = (V[j] - V[i]) @ nrm
        if rel < 0:
            V[i] += rel * nrm; V[j] -= rel * nrm
            if winner is None:
                if BEATS[T[i]] == T[j]:
                    convert(j, int(T[i]))
                elif BEATS[T[j]] == T[i]:
                    convert(i, int(T[j]))
    # paint
    iy = np.clip(((P[:, 1] - Y0) // C).astype(int), 0, NX - 1)
    ix = np.clip(((P[:, 0] - X0) // C).astype(int), 0, NX - 1)
    ok = inside[iy, ix]
    ch = ok & (paint[iy, ix] != T)
    paint_t[iy[ch], ix[ch]] = t
    paint[iy[ok], ix[ok]] = T[ok]
    if winner is None and sum(alive_team) == 1:
        winner = alive_team.index(True)
        win_t = t
        payoff_pending = song.next_bar(t + 0.3)
        song.sfx(t + 0.05, "chime", 0.0, 0.9)

def do_payoff():
    global payoff_t
    payoff_t = t
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 0.5)
    for _ in range(120):
        a = fx_rng.uniform(0, 2 * math.pi)
        sparks.append([CX + R * math.cos(a), CY + R * math.sin(a), fx_rng.uniform(10, 26), t, TEAM[winner]])
    events.append((t, "payoff", 0))

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SPR = neon.BallSprites(TEAM, BR, glow=2.8, glow_alpha=0.6)

def draw_tiles():
    pad = 1.6
    o = paint.copy()
    if payoff_t is not None:
        rad = (t - payoff_t) * 1500
        dd = np.hypot(GXC - last_xy[0], GYC - last_xy[1])
        o[inside & (dd < rad)] = winner
    age = t - paint_t
    for k in range(3):
        col = TEAM[k]
        for lo, hi, a in ((2.5, 1e9, 0.20), (0.8, 2.5, 0.30), (-1, 0.8, 0.45)):
            m = inside & (o == k) & (age >= lo) & (age < hi)
            ys, xs = np.where(m)
            if len(ys) == 0:
                continue
            ctx.set_source_rgba(*col, a)
            for yy, xx in zip(ys, xs):
                ctx.rectangle(X0 + xx * C + pad, Y0 + yy * C + pad, C - 2 * pad, C - 2 * pad)
            ctx.fill()
    if payoff_t is not None:
        rad = (t - payoff_t) * 1500
        dd = np.hypot(GXC - last_xy[0], GYC - last_xy[1])
        ys, xs = np.where(inside & (np.abs(dd - rad) < 80))
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_source_rgba(*neon.mix(TEAM[winner], (1, 1, 1), 0.5), 0.6)
        for yy, xx in zip(ys, xs):
            ctx.rectangle(X0 + xx * C + pad, Y0 + yy * C + pad, C - 2 * pad, C - 2 * pad)
        ctx.fill(); ctx.restore()

def arrow(x0, y0, x1, y1, col, a=1.0):
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
    sx, sy = x0 + ux * 38, y0 + uy * 38
    ex, ey = x1 - ux * 42, y1 - uy * 42
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for w_, al in ((12, 0.12), (4.5, 0.9)):
        ctx.set_source_rgba(*col, al * a); ctx.set_line_width(w_)
        ctx.move_to(sx, sy); ctx.line_to(ex, ey)
        ctx.move_to(ex - ux * 14 - uy * 9, ey - uy * 14 + ux * 9); ctx.line_to(ex, ey)
        ctx.line_to(ex - ux * 14 + uy * 9, ey - uy * 14 - ux * 9)
        ctx.stroke()
    ctx.restore()

def draw_legend(cnt):
    """three dots in a triangle, arrows from each colour to the one it beats (no text)."""
    cx, cy, rr = 540, 300, 105
    pos = [(cx + rr * math.cos(-math.pi / 2 + k * 2 * math.pi / 3), cy + 0.82 * rr * math.sin(-math.pi / 2 + k * 2 * math.pi / 3)) for k in range(3)]
    for k in range(3):
        j = BEATS[k]
        a = 1.0 if (alive_team[k] and alive_team[j]) else 0.25
        arrow(*pos[k], *pos[j], neon.mix(TEAM[k], (1, 1, 1), 0.35), a)
    for k in range(3):
        x, y = pos[k]
        grey = not alive_team[k]
        c = (0.4, 0.4, 0.48) if grey else TEAM[k]
        big = 1.0 + (0.3 if k == winner else 0.0) + (0 if grey else 0.35 * cnt[k] / (3 * NPER))
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        g = cairo.RadialGradient(x, y, 0, x, y, 56 * big)
        g.add_color_stop_rgba(0, *c, 0.12 if grey else 0.5); g.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(g); ctx.arc(x, y, 56 * big, 0, 2 * math.pi); ctx.fill(); ctx.restore()
        ctx.save(); ctx.set_source_rgba(*c, 0.35 if grey else 1.0); ctx.arc(x, y, 23 * big, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.25 if grey else 0.7); ctx.arc(x - 6, y - 6, 5 * big, 0, 2 * math.pi); ctx.fill(); ctx.restore()
    # share bar (ball counts)
    x0, x1, y, h = 160, 920, 1530, 22
    xs = x0
    for k in range(3):
        w_ = (x1 - x0) * cnt[k] / max(1, cnt.sum())
        if w_ <= 0.5:
            continue
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        g = cairo.LinearGradient(0, y - 26, 0, y + h + 26)
        g.add_color_stop_rgba(0, *TEAM[k], 0); g.add_color_stop_rgba(0.5, *TEAM[k], 0.25); g.add_color_stop_rgba(1, *TEAM[k], 0)
        ctx.set_source(g); ctx.rectangle(xs, y - 26, w_, h + 52); ctx.fill(); ctx.restore()
        ctx.set_source_rgba(*neon.mix(TEAM[k], (1, 1, 1), 0.2), 0.95); ctx.rectangle(xs + 1, y, w_ - 2, h); ctx.fill()
        xs += w_

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    cnt = counts()
    lead = int(np.argmax(cnt)) if winner is None else winner
    gcol = TEAM[lead]
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 950)
    ga = 0.04 + 0.11 * pr + 0.02 * math.sin(t * 1.9)
    if payoff_t is not None:
        ga = 0.22 * math.exp(-(t - payoff_t) * 0.9) + 0.06
    rg.add_color_stop_rgba(0, *gcol, ga); rg.add_color_stop_rgba(1, *gcol, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    duel = sum(alive_team) == 2 and winner is None
    shake = 18 * math.exp(-(t - payoff_t) * 6) if payoff_t is not None else (2.0 if duel else 0.0)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    draw_tiles()
    # ring: tinted toward the leading colour, pulsing once the cycle has collapsed to a duel
    rc = neon.mix(RING_COL, gcol, 0.2 + 0.6 * pr)
    if payoff_t is not None:
        rc = neon.mix(TEAM[winner], (1, 1, 1), 0.3 * math.exp(-(t - payoff_t) * 3))
    pulse = 1.0 + (0.35 * (0.5 + 0.5 * math.sin(t * 18)) if duel else 0.0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for w_, a_ in ((46, 0.05), (28, 0.09), (16, 0.16), (9, 0.35)):
        ctx.set_source_rgba(*rc, a_ * pulse); ctx.set_line_width(w_ * pulse)
        ctx.new_path(); ctx.arc(CX, CY, R, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
    ctx.set_source_rgba(*neon.mix(rc, (1, 1, 1), 0.6), 0.95); ctx.set_line_width(5)
    ctx.new_path(); ctx.arc(CX, CY, R, 0, 2 * math.pi); ctx.stroke()
    # flashes
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, data in events[-200:]:
        if kind == "ring" and 0 <= t - et < 0.3:
            x, y, k = data; a = 1 - (t - et) / 0.3
            ctx.set_source_rgba(*TEAM[k], 0.6 * a); ctx.set_line_width(2.5)
            ctx.new_path(); ctx.arc(x, y, 6 + 20 * (1 - a), 0, 2 * math.pi); ctx.stroke()
        elif kind == "conv" and 0 <= t - et < 0.45:
            i, k = data; a = 1 - (t - et) / 0.45
            ctx.set_source_rgba(*neon.mix(TEAM[k], (1, 1, 1), 0.4), 0.85 * a); ctx.set_line_width(3)
            ctx.new_path(); ctx.arc(P[i, 0], P[i, 1], BR + 4 + 26 * (1 - a), 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
    SPR.draw(ctx, [tuple(q) for q in P], list(T))
    # just-converted balls: white core flash
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for i in np.where(t - conv_t < 0.25)[0]:
        a = 1 - (t - conv_t[i]) / 0.25
        ctx.set_source_rgba(1, 1, 1, 0.7 * a); ctx.arc(P[i, 0], P[i, 1], BR * 0.9, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    live = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = live
    groups = {}
    for x, y, sz, st, c in live:
        al = 1 - (t - st) / 0.5
        groups.setdefault((c, round(al, 1)), []).append((x, y, sz * (0.6 + al)))
    for (c, al), q in groups.items():
        neon.sparkles(ctx, q, neon.mix(c, (1, 1, 1), 0.5), alpha=al * 0.9)
    ctx.restore()
    draw_legend(cnt)
    if counter and payoff_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(92)
        txt = f"{int(cnt.max())}"
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1690)
        ctx.text_path(txt)
        cc = neon.mix(gcol, (1, 1, 1), 0.35)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(20); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.95); ctx.fill()
        ctx.restore()
    if payoff_t is not None:
        dtp = t - payoff_t
        fa = max(0.0, 0.45 - dtp * 2.5)
        if fa > 0:
            ctx.set_source_rgba(*neon.mix(TEAM[winner], (1, 1, 1), 0.7), fa); ctx.paint()
        if dtp < 1.3:
            a = 1 - dtp / 1.3
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*TEAM[winner], 0.8 * a); ctx.set_line_width(4 + 18 * a)
            ctx.new_path(); ctx.arc(CX, CY, R + 1400 * dtp, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        end = payoff_t + TAIL
        xf = (t - (end - 1.4)) / 1.4
        if xf > 0 and first is not None:
            ctx.set_source_surface(first, 0, 0); ctx.paint_with_alpha(min(1.0, xf) ** 1.5)

ff = None
if not SIM_ONLY:
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", OUT
    ], stdin=subprocess.PIPE)

dt = 1.0 / (FPS * SUB)
frame = 0
log = []
while True:
    for _ in range(SUB):
        physics_step(dt)
        if payoff_pending is not None and payoff_t is None and t >= payoff_pending:
            do_payoff()
        t += dt
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if frame % 300 == 0:
        log.append((round(t), list(counts())))
    if PREVIEW and any(abs(t - pt) < 0.5 / FPS for pt in PREVIEW):
        draw(); surf.flush(); surf.write_to_png(f"prev_{t:05.1f}.png")
    if not SIM_ONLY:
        draw(); surf.flush()
        if first is None:
            first = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            c2 = cairo.Context(first); c2.set_source_surface(surf, 0, 0); c2.paint()
        ff.stdin.write(bytes(surf.get_data()))
    frame += 1
    if payoff_t is not None and t >= payoff_t + TAIL:
        break
    if t > 80:
        break

if ff:
    ff.stdin.close(); ff.wait()
print("seed", SEED, "log(t,counts)", log)
print("outs", [(NAMES[k], round(out_t[k], 1)) for k in range(3) if out_t[k] is not None],
      "winner", winner is not None and NAMES[winner], "win", win_t and round(win_t, 2), "payoff", payoff_t and round(payoff_t, 2),
      "duration", round(t, 2), "conversions", convs)
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
