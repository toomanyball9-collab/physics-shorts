"""2026-11-23 08:00 — plinko (new family): "Bell Curve"
A neon Galton board. A dropper at the top releases a ball on the beat (1 per beat, then 2, then 4 as the
song builds — every release is visible). Each ball tumbles through 14 rows of glowing pegs (every peg hit
plays the next note) and lands in one of 32 narrow tubes, stacking up. The dropper changes colour every
4 bars, so the stacks grow in colour layers. A faint dashed curve shows the bell curve the beads should
build. When the tallest stack reaches the top of its tube the floor has to carry every bead: it heats red,
sags and shakes, then gives way on the next bar line and everything falls out of the bottom.
Tail crossfades back to the opening frame.

usage: python3 concepts/2026-11-23_am_bell_curve.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 6
CX = W / 2
G = 1500.0
DRAG = G / 760.0                  # terminal speed ~760 px/s
BR = 12.5
PEG_R = 5.0
NBIN = int(os.environ.get("NBIN", "17"))
DROP_Y = 232.0
PEG_Y0 = float(os.environ.get("PEG_Y0", "350"))
DY = float(os.environ.get("DY", "46"))
DX = float(os.environ.get("DX", "54"))
ROWS = int(os.environ.get("ROWS", "14"))
BIN_TOP = PEG_Y0 + (ROWS - 1) * DY + float(os.environ.get("BIN_GAP", "52"))
FLOOR = float(os.environ.get("FLOOR", "1735"))
PITCH = DX                       # tubes sit exactly under the gaps of the last peg row
L_WALL, R_WALL = CX - PITCH * NBIN / 2, CX + PITCH * NBIN / 2
CAP = int((FLOOR - BIN_TOP) / (2 * BR))   # beads per sub-column (2 side by side per tube)
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
MUSIC_SEED = 2026112308   # random_song(seed, avoid=last 10 recipes) -> jazzhop / harp (checked vs rules)
RECENT = [dict(genre="space", bpm=88, key="G", mode="dorian", lead="glass"),
          dict(genre="citypop", bpm=102, key="E", mode="major", lead="ep"),
          dict(genre="tropical", bpm=112, key="A", mode="major", lead="marimba"),
          dict(genre="musicbox", bpm=95, key="E", mode="harmonic_minor", lead="celesta"),
          dict(genre="cinematic", bpm=78, key="A#", mode="minor", lead="harp"),
          dict(genre="waltz", bpm=93, key="D", mode="major", lead="ep"),
          dict(genre="synthwave", bpm=104, key="G#", mode="dorian", lead="saw"),
          dict(genre="gamelan", bpm=94, key="D#", mode="major", lead="bell"),
          dict(genre="lofi", bpm=74, key="F#", mode="major", lead="kalimba"),
          dict(genre="celtic", bpm=116, key="A#", mode="mixolydian", lead="flute")]
song = music.random_song(MUSIC_SEED, avoid=RECENT)
BAR = song.chord_len
BEAT = song.beat
# release rate per beat, switching on bar lines
R2 = int(os.environ.get("R2", "3")); R3 = int(os.environ.get("R3", "5")); R4 = int(os.environ.get("R4", "10"))
def rate_at(tt):
    b = int(tt / BAR + 1e-9)
    return 1 if b < R2 else 2 if b < R3 else 4 if b < R4 else int(os.environ.get("RL", "8"))
COL_BARS = 4
# colour strata: deep blue -> cyan -> mint -> gold -> coral -> magenta -> violet
COLS = [(0.30, 0.45, 1.0), (0.20, 0.85, 1.0), (0.30, 1.0, 0.70), (1.0, 0.85, 0.30), (1.0, 0.50, 0.40),
        (1.0, 0.35, 0.75), (0.70, 0.45, 1.0)]
PAL = {"bg": ((0.02, 0.02, 0.08), (0.00, 0.00, 0.03)), "ring": (0.70, 0.80, 1.0), "balls": COLS,
       "accent": (1.0, 0.95, 0.85)}
FRAME_COL = (0.62, 0.72, 1.0)
CURVE_MU = float(os.environ.get("MU", "-0.02"))      # fitted from a --sim run (in bins, relative to centre)
CURVE_SIG = float(os.environ.get("SIG", "3.20"))

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)

# pegs
PEGS = []
for i in range(ROWS):
    y = PEG_Y0 + i * DY
    off = 0.0 if i % 2 == 0 else DX / 2
    k0 = -int((CX - L_WALL) / DX) - 1
    for k in range(k0, -k0 + 1):
        x = CX + k * DX + off
        if L_WALL + 16 < x < R_WALL - 16:
            PEGS.append((x, y))
PEGS = np.array(PEGS)
peg_flash = np.zeros(len(PEGS)); peg_fcol = np.zeros(len(PEGS), int)
DIV_X = np.array([L_WALL + k * PITCH for k in range(NBIN + 1)])

# ---------------- state ----------------
# movers (in flight)
p = np.zeros((0, 2)); v = np.zeros((0, 2)); col = np.zeros(0, int); colm = np.zeros(0, int) - 1
# landed beads
landed = []                     # (x, y, colour, bin)
height = np.zeros((NBIN, 2), int)
t = 0.0
next_drop = 0.15
drop_k = 0
n_drop = 0
full_t = None
burst_pending = None
burst_t = None
heat = 0.0
events = []
sparks = []
frags = []
fall = None                      # after the burst: arrays of falling beads
build_keys = []
drop_flash = 0.0
peg_cool = {}

def sub_x(b, sub):
    return L_WALL + (b + 0.5) * PITCH + (sub - 0.5) * (2 * BR + 0.8)

def cur_col(tt):
    return int(tt / (BAR * COL_BARS)) % len(COLS)

def progress():
    if burst_t is not None:
        return 1.0
    return float(min(1.0, height.max() / CAP))

def release():
    global p, v, col, colm, n_drop, drop_flash
    x = CX + rng.uniform(-1.5, 1.5)
    p = np.vstack([p, [[x, DROP_Y]]]); v = np.vstack([v, [[rng.uniform(-12, 12), 60.0]]])
    col = np.append(col, cur_col(t)); colm = np.append(colm, -1)
    n_drop += 1
    drop_flash = 1.0
    song.sfx(t, "tick", 0.0, 0.10)

def physics_step(dt):
    global p, v, col, colm, heat, full_t, burst_pending
    n = len(p)
    if n == 0:
        return
    v[:, 1] += G * dt
    v -= v * DRAG * dt
    p += v * dt
    inbin = colm >= 0
    # ball-ball (movers only, outside the tubes)
    fr = np.where(~inbin)[0]
    if len(fr) > 1:
        q = p[fr]
        d = q[None, :, :] - q[:, None, :]
        dd = np.hypot(d[..., 0], d[..., 1])
        ii, jj = np.where(np.triu(dd < 2 * BR, 1))
        for a, b in zip(ii, jj):
            i, j = fr[a], fr[b]
            dist = dd[a, b] + 1e-6
            nrm = (p[j] - p[i]) / dist
            over = 2 * BR - dist
            p[i] -= nrm * over / 2; p[j] += nrm * over / 2
            rel = np.dot(v[j] - v[i], nrm)
            if rel < 0:
                imp = 0.85 * rel * nrm
                v[i] += imp; v[j] -= imp
    # pegs
    if len(fr):
        q = p[fr]
        d = q[:, None, :] - PEGS[None, :, :]
        dd = np.hypot(d[..., 0], d[..., 1])
        ai, pk = np.where(dd < BR + PEG_R)
        for a, k in zip(ai, pk):
            i = fr[a]
            dist = dd[a, k] + 1e-6
            nrm = (p[i] - PEGS[k]) / dist
            p[i] = PEGS[k] + nrm * (BR + PEG_R)
            vn = np.dot(v[i], nrm)
            if vn < 0:
                vt = v[i] - vn * nrm
                v[i] = vt * 0.92 - 0.42 * vn * nrm
                # tiny deterministic-per-seed nudge so dead-centre hits don't balance on top of a peg
                v[i][0] += rng.uniform(-14, 14)
                if -vn > 90:
                    key = (i, k)
                    if t - peg_cool.get(k, -9) > 0.05:
                        song.note(t, float((PEGS[k][0] - CX) / 480), vel=min(1.0, 0.45 + -vn / 900))
                    peg_cool[k] = t
                    peg_flash[k] = 1.0; peg_fcol[k] = col[i]
    # side walls
    lo = p[:, 0] < L_WALL + BR; hi = p[:, 0] > R_WALL - BR
    p[lo, 0] = L_WALL + BR; v[lo, 0] = np.abs(v[lo, 0]) * 0.5
    p[hi, 0] = R_WALL - BR; v[hi, 0] = -np.abs(v[hi, 0]) * 0.5
    # divider tops (round caps) for balls still above the tubes
    for i in fr:
        if p[i, 1] > BIN_TOP - BR - 2 and p[i, 1] < BIN_TOP + BR:
            k = int(round((p[i, 0] - L_WALL) / PITCH))
            if 0 <= k <= NBIN:
                cx_, cy_ = DIV_X[k], BIN_TOP
                dx_, dy_ = p[i, 0] - cx_, p[i, 1] - cy_
                dist = math.hypot(dx_, dy_)
                if dist < BR + 2.0 and dy_ < 0:
                    nrm = np.array([dx_, dy_]) / (dist + 1e-6)
                    p[i] = np.array([cx_, cy_]) + nrm * (BR + 2.0)
                    vn = np.dot(v[i], nrm)
                    if vn < 0:
                        v[i] = (v[i] - vn * nrm) * 0.9 - 0.3 * vn * nrm
                        if abs(dx_) < 1.0:
                            v[i][0] += rng.choice([-30.0, 30.0])
    # entering a tube -> lock to its column and fall straight down onto the stack
    for i in fr:
        if p[i, 1] >= BIN_TOP + 1:
            b = int(np.clip((p[i, 0] - L_WALL) // PITCH, 0, NBIN - 1))
            sub = 0 if p[i, 0] < L_WALL + (b + 0.5) * PITCH else 1
            colm[i] = b * 2 + sub
    inbin = colm >= 0
    landed_now = []
    for i in np.where(inbin)[0]:
        b, sub = divmod(int(colm[i]), 2)
        if height[b, 1 - sub] < height[b, sub]:      # beads settle into the lower side
            sub = 1 - sub; colm[i] = b * 2 + sub
        xc = sub_x(b, sub)
        p[i, 0] += (xc - p[i, 0]) * min(1.0, 14 * dt)
        v[i, 0] *= 0.8
        y_stop = FLOOR - BR - 2 * BR * height[b, sub]
        if p[i, 1] >= y_stop:
            landed_now.append(i)
    if landed_now:
        for i in sorted(landed_now, key=lambda i: -p[i, 1]):
            b, sub = divmod(int(colm[i]), 2)
            y_stop = FLOOR - BR - 2 * BR * height[b, sub]
            xc = sub_x(b, sub)
            landed.append((xc, y_stop, int(col[i]), int(b)))
            height[b, sub] += 1
            sp = float(v[i, 1])
            song.sfx(t, "tick", float((xc - CX) / 480), min(0.35, 0.12 + sp / 3000))
            events.append((t, "land", (xc, y_stop, int(col[i]))))
            if height[b, sub] >= CAP and full_t is None:
                full_t = t
                burst_pending = song.next_bar(t + 0.05)
                events.append((t, "full", b))
                song.sfx(t, "chime", float((xc - CX) / 480), 0.7)
        keep = np.ones(len(p), bool); keep[landed_now] = False
        p, v, col, colm = p[keep], v[keep], col[keep], colm[keep]
    # don't let two beads in the same tube overlap while falling
    inbin = np.where(colm >= 0)[0]
    if len(inbin) > 1:
        order = sorted(inbin, key=lambda i: (colm[i], -p[i, 1]))
        for a, b in zip(order, order[1:]):
            if colm[a] == colm[b] and p[b, 1] > p[a, 1] - 2 * BR:
                p[b, 1] = p[a, 1] - 2 * BR
                v[b, 1] = min(v[b, 1], v[a, 1])
    n_l = len(landed)
    heat = float(np.clip((height.max() / CAP - 0.62) / 0.38, 0, 1)) if full_t is None else 1.0

def do_burst():
    global burst_t, fall
    burst_t = t
    xs = np.array([b[0] for b in landed] + list(p[:, 0]))
    ys = np.array([b[1] for b in landed] + list(p[:, 1]))
    cs = np.array([b[2] for b in landed] + list(col), int)
    # weight breaks the floor: the sag is deepest in the middle, beads start falling with a little spread
    vx = (xs - CX) * 0.15 + fx_rng.normal(0, 25, len(xs))
    vy = 60 + 120 * np.exp(-((xs - CX) / 300) ** 2) + fx_rng.uniform(0, 40, len(xs))
    fall = [np.stack([xs, ys], 1), np.stack([vx, vy], 1), cs]
    nseg = 12
    for m in range(nseg):
        x0 = L_WALL + (R_WALL - L_WALL) * m / nseg
        x1 = L_WALL + (R_WALL - L_WALL) * (m + 1) / nseg
        xm = (x0 + x1) / 2
        frags.append([xm, FLOOR, (xm - CX) * 0.5 + fx_rng.normal(0, 40), 100 + fx_rng.uniform(0, 160),
                      0.0, fx_rng.uniform(-3, 3), (x1 - x0) * 0.92, "floor"])
    for k, x in enumerate(DIV_X):
        frags.append([x, (BIN_TOP + FLOOR) / 2, fx_rng.normal(0, 50), fx_rng.uniform(0, 80), 0.0,
                      fx_rng.uniform(-1.2, 1.2), FLOOR - BIN_TOP, "div"])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    song.sfx(t + 0.03, "thump", 0.0, 1.0)
    for _ in range(60):
        x = fx_rng.uniform(L_WALL, R_WALL)
        sparks.append([x, FLOOR + fx_rng.uniform(-10, 10), fx_rng.uniform(10, 24), t, COLS[int(fx_rng.integers(len(COLS)))]])
    events.append((t, "burst", 0))

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
spr = neon.SkinSprites(COLS, BR, skin="orb")
# landed beads are cached on layers (glow added, cores over) — they never move until the floor breaks
glow_layer = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
core_layer = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
gctx = cairo.Context(glow_layer); cctx = cairo.Context(core_layer)
gctx.set_operator(cairo.OPERATOR_ADD)
n_cached = 0

def curve_y(x):
    """dashed target curve: Gaussian fitted to this seed's final pile, peak = top of the tubes"""
    u = (x - CX) / PITCH - CURVE_MU
    return FLOOR - (FLOOR - BIN_TOP) * math.exp(-0.5 * (u / CURVE_SIG) ** 2)

def tube(x0, y0, x1, y1, rgb, alpha=1.0, width=3.0, glowk=1.0):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for w, a in [(26, 0.05), (14, 0.10), (7, 0.25)]:
        ctx.set_source_rgba(*rgb, a * alpha * glowk); ctx.set_line_width(w * width / 4)
        ctx.move_to(x0, y0); ctx.line_to(x1, y1); ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(*neon.mix(rgb, (1, 1, 1), 0.6), 0.9 * alpha); ctx.set_line_width(width)
    ctx.move_to(x0, y0); ctx.line_to(x1, y1); ctx.stroke(); ctx.restore()

def draw_pegs():
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    base = (0.62, 0.72, 1.0)
    for k, (x, y) in enumerate(PEGS):
        f = peg_flash[k]
        c = neon.mix(base, COLS[peg_fcol[k]], min(1.0, f * 1.5))
        rr = 13 + 10 * f
        g = cairo.RadialGradient(x, y, 0, x, y, rr)
        g.add_color_stop_rgba(0, *c, 0.35 + 0.5 * f); g.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(g); ctx.arc(x, y, rr, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    ctx.save()
    for k, (x, y) in enumerate(PEGS):
        f = peg_flash[k]
        ctx.set_source_rgba(*neon.mix(base, (1, 1, 1), 0.6 + 0.4 * f), 0.95)
        ctx.arc(x, y, PEG_R * (1 + 0.25 * f), 0, 2 * math.pi); ctx.fill()
    ctx.restore()

def draw_dropper():
    c = COLS[cur_col(t)]
    if full_t is not None:
        c = neon.mix(c, (0.5, 0.5, 0.6), 0.6)
    k = drop_flash
    pts = [(CX - 70, DROP_Y - 70), (CX - 22, DROP_Y - 18), (CX - 22, DROP_Y - 4)]
    pts2 = [(CX + 70, DROP_Y - 70), (CX + 22, DROP_Y - 18), (CX + 22, DROP_Y - 4)]
    for pp in (pts, pts2):
        for a, b in zip(pp, pp[1:]):
            tube(a[0], a[1], b[0], b[1], c, 1.0, 3.5, 1.0 + 1.2 * k)
    g = cairo.RadialGradient(CX, DROP_Y - 30, 0, CX, DROP_Y - 30, 70)
    g.add_color_stop_rgba(0, *c, 0.25 + 0.35 * k); g.add_color_stop_rgba(1, *c, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(g); ctx.arc(CX, DROP_Y - 30, 70, 0, 2 * math.pi); ctx.fill(); ctx.restore()

def draw(counter=True):
    global first, n_cached
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gc = neon.mix(COLS[cur_col(t)], (1.0, 0.3, 0.3), heat * 0.7)
    rg = cairo.RadialGradient(CX, FLOOR - 300, 0, CX, FLOOR - 300, 1000)
    ga = 0.03 + 0.12 * pr + 0.02 * math.sin(t * 2.0)
    if burst_t is not None:
        ga *= math.exp(-(t - burst_t) * 1.5)
    rg.add_color_stop_rgba(0, *gc, ga); rg.add_color_stop_rgba(1, *gc, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()
    shake = 0.0
    if burst_t is None and heat > 0.4:
        shake = 7 * ((heat - 0.4) / 0.6) ** 2
    if burst_t is not None:
        shake = 22 * math.exp(-(t - burst_t) * 6)
    ctx.save()
    sx = sy = 0.0
    if shake > 0:
        sx, sy = fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake)
        ctx.translate(sx, sy)
    draw_pegs()
    draw_dropper()
    # side walls of the board
    tube(L_WALL - 6, PEG_Y0 - 120, L_WALL - 6, FLOOR, FRAME_COL, 0.55, 3.0)
    tube(R_WALL + 6, PEG_Y0 - 120, R_WALL + 6, FLOOR, FRAME_COL, 0.55, 3.0)
    sag = 0.0
    if burst_t is None:
        sag = 10 * heat
        # tube dividers
        for x in DIV_X:
            tube(x, BIN_TOP, x, FLOOR + sag * math.exp(-((x - CX) / 300) ** 2), FRAME_COL, 0.45, 2.0, 0.8)
        # floor (sags under the weight, heats red)
        fc = neon.mix(FRAME_COL, (1.0, 0.18, 0.22), heat)
        pulse = 1.0 + heat * 0.6 * (0.5 + 0.5 * math.sin(t * 24))
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for w, a in [(46, 0.05), (28, 0.09), (16, 0.16), (9, 0.35)]:
            ctx.set_source_rgba(*fc, a * pulse); ctx.set_line_width(w * pulse)
            ctx.move_to(L_WALL - 6, FLOOR + BR * 0.2)
            for xx in np.linspace(L_WALL, R_WALL, 24):
                ctx.line_to(xx, FLOOR + 3 + sag * math.exp(-((xx - CX) / 300) ** 2))
            ctx.line_to(R_WALL + 6, FLOOR + 3); ctx.stroke()
        ctx.restore()
        ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgba(*neon.mix(fc, (1, 1, 1), 0.65), 0.95); ctx.set_line_width(5)
        ctx.move_to(L_WALL - 6, FLOOR + 3)
        for xx in np.linspace(L_WALL, R_WALL, 24):
            ctx.line_to(xx, FLOOR + 3 + sag * math.exp(-((xx - CX) / 300) ** 2))
        ctx.line_to(R_WALL + 6, FLOOR + 3); ctx.stroke(); ctx.restore()
        # target curve (dashed)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_dash([10, 12], -t * 15)
        cc = neon.mix(PAL["accent"], gc, 0.3)
        xs = np.linspace(L_WALL + 4, R_WALL - 4, 120)
        for w, a in [(10, 0.07), (3, 0.40)]:
            ctx.set_source_rgba(*cc, a * (0.7 + 0.3 * math.sin(t * 3))); ctx.set_line_width(w)
            ctx.move_to(xs[0], curve_y(xs[0]))
            for xx in xs[1:]:
                ctx.line_to(xx, curve_y(xx))
            ctx.stroke()
        ctx.set_dash([]); ctx.restore()
        # landed beads (cached)
        while n_cached < len(landed):
            x, y, c, b = landed[n_cached]
            s, Gs = spr.glow[c]
            gctx.set_source_surface(s, x - Gs, y - Gs); gctx.paint()
            s2, P = spr.core[c]
            cctx.set_source_surface(s2, x - P, y - P); cctx.paint()
            n_cached += 1
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source_surface(glow_layer, 0, 0); ctx.paint(); ctx.restore()
        ctx.set_source_surface(core_layer, 0, 0); ctx.paint()
        # landing pulse
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        for et, kind, data in events[-80:]:
            if kind == "land" and 0 <= t - et < 0.25:
                a = 1 - (t - et) / 0.25
                x, y, c = data
                ctx.set_source_rgba(*neon.mix(COLS[c], (1, 1, 1), 0.5), 0.6 * a); ctx.set_line_width(2.5)
                ctx.new_path(); ctx.arc(x, y, BR * (1 + 0.8 * (1 - a)), 0, 2 * math.pi); ctx.stroke()
        ctx.restore()
        # movers
        if len(p):
            spr.draw(ctx, [tuple(q) for q in p], list(col))
    else:
        age = t - burst_t
        # fragments of the floor and the tube walls falling
        for f in frags:
            x, y, _vx, _vy, rot, _vr, ln, kind = f
            a = max(0.0, 1 - age / 2.6)
            if a <= 0:
                continue
            c = neon.mix(FRAME_COL, (1.0, 0.25, 0.25), 0.7 if kind == "floor" else 0.3)
            ctx.save(); ctx.translate(x, y); ctx.rotate(rot)
            if kind == "floor":
                ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                for w, aa in [(18, 0.15), (7, 0.9)]:
                    ctx.set_source_rgba(*c, aa * a); ctx.set_line_width(w)
                    ctx.move_to(-ln / 2, 0); ctx.line_to(ln / 2, 0); ctx.stroke()
                ctx.restore()
            else:
                ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
                ctx.set_source_rgba(*c, 0.5 * a); ctx.set_line_width(2.0)
                ctx.move_to(0, -ln / 2); ctx.line_to(0, ln / 2); ctx.stroke(); ctx.restore()
            ctx.restore()
        if fall is not None:
            pts = [(x, y) for x, y in fall[0] if -40 < y < H + 40]
            cs = [c for (x, y), c in zip(fall[0], fall[2]) if -40 < y < H + 40]
            spr.draw(ctx, pts, cs)
        # horizontal shock line along the broken floor
        if age < 0.9:
            a = 1 - age / 0.9
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*PAL["accent"], 0.7 * a); ctx.set_line_width(4 + 18 * a)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(L_WALL, FLOOR + 600 * age); ctx.line_to(R_WALL, FLOOR + 600 * age); ctx.stroke()
            ctx.restore()
    # sparks
    live = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = live
    by = {}
    for x, y, sz, st, c in live:
        a = 1 - (t - st) / 0.5
        by.setdefault((c, round(a, 1)), []).append((x, y, sz * (0.6 + a)))
    for (c, a), pts_ in by.items():
        neon.sparkles(ctx, pts_, neon.mix(c, (1, 1, 1), 0.4), alpha=a * 0.9)
    ctx.restore()
    if counter and burst_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(96)
        txt = str(len(landed))
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1860)
        ctx.text_path(txt)
        cc = neon.mix(neon.mix(COLS[cur_col(t)], (1, 1, 1), 0.45), (1, .3, .3), heat)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(20); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.95); ctx.fill()
        ctx.restore()
    if burst_t is not None:
        fa = max(0.0, 0.45 - (t - burst_t) * 2.5)
        if fa > 0:
            ctx.set_source_rgba(1, 1, 1, fa); ctx.paint()
        end = burst_t + TAIL
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
while True:
    for _ in range(SUB):
        if full_t is None and t >= next_drop:
            release()
            drop_k += 1
            step = BEAT / rate_at(t)
            next_drop = (math.floor(t / step + 1e-6) + 1) * step
        physics_step(dt)
        if burst_pending is not None and burst_t is None and t >= burst_pending:
            do_burst()
        if fall is not None:
            fall[1][:, 1] += G * 1.1 * dt
            fall[0] += fall[1] * dt
        for f in frags:
            f[3] += G * dt
            f[0] += f[2] * dt; f[1] += f[3] * dt; f[4] += f[5] * dt
        t += dt
    peg_flash *= 0.86
    drop_flash *= 0.8
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if not SIM_ONLY:
        draw(); surf.flush()
        if first is None:
            first = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            c2 = cairo.Context(first); c2.set_source_surface(surf, 0, 0); c2.paint()
        ff.stdin.write(bytes(surf.get_data()))
    frame += 1
    if burst_t is not None and t >= burst_t + TAIL:
        break
    if t > 80:
        break

if ff:
    ff.stdin.close(); ff.wait()
hist = height.sum(1).astype(float)
xs = np.arange(NBIN) - (NBIN - 1) / 2
mu = float(np.sum(hist * xs) / max(1, hist.sum()))
sig = float(math.sqrt(np.sum(hist * (xs - mu) ** 2) / max(1, hist.sum())))
print("seed", SEED, "bins", NBIN, "cap", CAP, "BIN_TOP", BIN_TOP, "full", full_t and round(full_t, 2),
      "burst", burst_t and round(burst_t, 2), "duration", round(t, 2), "landed", len(landed), "dropped", n_drop)
print("hist", [int(x) for x in height.sum(1)])
print(f"fit MU={mu:.2f} SIG={sig:.2f}  peak-gauss-height={hist.sum() / (sig * math.sqrt(2 * math.pi)):.1f}")
print("music", song.recipe_str(), "bar", round(BAR, 3))

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
