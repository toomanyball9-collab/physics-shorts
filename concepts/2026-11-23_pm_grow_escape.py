"""2026-11-23 18:00 — escape (variation): "Grow Escape"
Ring Escape's structure with a new visible rule: EVERY WALL HIT MAKES A BALL BIGGER (its colour warms as
it grows). 12 rotating neon rings, each gap slowly opening — but a ball only gets
through if it still FITS the gap; too-big balls bounce off the gap's edges. Getting out shatters the ring
and the escaping ball splits into 3 smaller balls (area conserved, colour cools again). Camera zooms out.
The last ring is sealed: the balls keep growing with every wall hit until they pack it completely; the ring
heats red and shakes from the pressure and bursts outward on a bar line. Tail crossfades to the opening.

usage: python3 concepts/2026-11-23_pm_grow_escape.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 4
CX, CY = W / 2, 930
BR = 11.0
N_GAP = 12
R0, R_FINAL = 78.0, 455.0
RADII = [R0 + (R_FINAL - R0) * k / N_GAP for k in range(N_GAP + 1)]
SCREEN_SPEED = 520.0
PAYOFF_TARGET = 61.0
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 16
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
# size ladder colours: mint -> cyan -> blue -> violet -> pink -> gold (warmer = bigger)
COLS = [(0.35, 1.0, 0.75), (0.20, 0.85, 1.0), (0.30, 0.50, 1.0), (0.62, 0.38, 1.0), (1.0, 0.35, 0.72),
        (1.0, 0.70, 0.30)]
RING_A, RING_B = (0.25, 0.95, 0.90), (0.75, 0.40, 1.0)
PAL = {"bg": ((0.01, 0.03, 0.08), (0.00, 0.00, 0.03)), "ring": (0.80, 0.85, 1.0), "balls": COLS,
       "accent": (1.0, 0.95, 0.85)}
NC = len(COLS)
MUSIC_SEED = 2026112355   # random_song(seed, avoid=last 11 recipes incl. 08:00 jazzhop) -> space / bell
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
          dict(genre="jazzhop", bpm=89, key="C", mode="major", lead="harp")]
SKIN = "orb"
GROW = float(os.environ.get("GROW", "0.0045"))    # every wall hit: radius + GROW * ring radius (same on-screen step)
FILL_END = float(os.environ.get("FILL_END", "0.72"))
GK = float(os.environ.get("GK", "0.6"))
NSPLIT = int(os.environ.get("NSPLIT", "2"))

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)
song = music.random_song(MUSIC_SEED, avoid=RECENT)
GAP_MAX = math.radians(64)

def zoom_for(r):
    return (150 + 0.67 * r) / r

TARGET = [5.0 - 2.2 * k / (N_GAP - 1) for k in range(N_GAP)]
T_K = [x / 0.886 for x in TARGET]
GAP_RATE = []
for k in range(N_GAP):
    n_k = 1 + (NSPLIT - 1) * k
    h_k = GK * SCREEN_SPEED / (1.3 * (150 + 0.67 * RADII[k]))
    GAP_RATE.append(4 * math.pi / (n_k * h_k * T_K[k] ** 2))
OMEGA = [(0.45 + 0.4 * rng.random()) * (1 if k % 2 == 0 else -1) for k in range(N_GAP + 1)]
ROT0 = [rng.uniform(0, 2 * math.pi) for _ in range(N_GAP + 1)]

def ring_color(k):
    return neon.mix(RING_A, RING_B, k / N_GAP)

# ---------------- state ----------------
a0 = rng.uniform(0, 2 * math.pi)
z = zoom_for(R0)
spd = SCREEN_SPEED / z
p = np.array([[CX + 8.0, CY - 4.0]])
v = np.array([[math.cos(a0) * spd, math.sin(a0) * spd]])
r = np.array([BR])
pulse = np.array([-9.0])          # time of last growth (for the white pulse)
cool = np.array([-9.0])
passing = np.array([False])       # inside the gap right now (keeps going even if the ring turns)
cur = 0
ring_t0 = 0.0
alive = [True] * (N_GAP + 1)
frags, sparks = [], []
hit_flash = 0.0
edge_flash = 0.0
heat = 0.0
fill = 0.0
final_t0 = None
burst_pending = None
burst_t = None
events = []
build_keys = []
n_bounce = n_block = 0
t = 0.0

def rot(k, tt):
    return ROT0[k] + OMEGA[k] * tt

def gap_now(k, tt):
    if k >= N_GAP:
        return 0.0
    age = tt - ring_t0
    g0 = 2 * math.asin(min(0.99, BR / RADII[k])) * 0.9
    return min(GAP_MAX, g0 + GAP_RATE[k] * min(age, 3.0 * T_K[k]))

def col_of(rad_world):
    x = math.log(max(1.0, rad_world / BR)) / math.log(7.5) * (NC - 1)
    return int(np.clip(round(x), 0, NC - 1))

def progress():
    if burst_t is not None:
        return 1.0
    if cur < N_GAP:
        return 0.82 * (cur + min(1.0, (t - ring_t0) / T_K[cur]) * 0.5) / N_GAP
    return 0.82 + 0.18 * heat

def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi

def grow(i, k):
    global n_bounce
    if t - cool[i] < 0.06:
        return
    cool[i] = t
    if k == N_GAP and fill >= FILL_END:
        return
    if k < N_GAP and np.sum(r ** 2) / RADII[k] ** 2 > 0.5:
        return
    r[i] = r[i] + GROW * RADII[k]
    pulse[i] = t

def split(i):
    """escaping ball splits into NSPLIT (area conserved)"""
    global p, v, r, pulse, cool, passing
    ns = NSPLIT
    rn = r[i] / math.sqrt(ns)
    dx, dy = p[i][0] - CX, p[i][1] - CY
    dl = math.hypot(dx, dy) + 1e-6
    ux, uy = dx / dl, dy / dl
    tx, ty = -uy, ux
    ps, vs = [], []
    base = math.atan2(v[i][1], v[i][0])
    sp = math.hypot(*v[i])
    offs = [-1, 1] if ns == 2 else [-1, 0, 1]
    for off in offs:
        ps.append([p[i][0] + tx * off * 1.05 * rn * (2 if ns == 3 else 1) - ux * 2,
                   p[i][1] + ty * off * 1.05 * rn * (2 if ns == 3 else 1) - uy * 2])
        a = base + off * rng.uniform(0.5, 1.0)
        vs.append([math.cos(a) * sp, math.sin(a) * sp])
    keep = np.ones(len(p), bool); keep[i] = False
    p = np.vstack([p[keep], ps]); v = np.vstack([v[keep], vs])
    r = np.concatenate([r[keep], [rn] * ns])
    pulse = np.concatenate([pulse[keep], [t] * ns]); cool = np.concatenate([cool[keep], [t] * ns])
    passing = np.zeros(len(p), bool)

def shatter(k, tt, pan):
    alive[k] = False
    R = RADII[k]; g = gap_now(k, tt); rr = rot(k, tt)
    N = 10 + k
    span_total = 2 * math.pi - g
    for m in range(N):
        span = span_total / N
        ac = rr + g / 2 + span * (m + 0.5)
        sp = rng.uniform(160, 420) * (1 + k * 0.05)
        frags.append([CX + R * math.cos(ac), CY + R * math.sin(ac), math.cos(ac) * sp, math.sin(ac) * sp,
                      ac, span * 0.86, R, 0.0, rng.uniform(-3, 3), ring_color(k), tt])
    song.sfx(tt, "shatter", pan, 0.6)
    song.sfx(tt + 0.02, "chime", pan, 0.8)
    events.append((tt, "break", k))

def do_burst():
    global burst_t, v
    burst_t = t
    R = RADII[N_GAP]
    d = p - (CX, CY)
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    radial = d / dist[:, None]
    v = v * 0.2 + radial * rng.uniform(380, 900, len(p))[:, None]
    N = 30
    for m in range(N):
        ac = rot(N_GAP, t) + 2 * math.pi * (m + 0.5) / N
        sp = rng.uniform(650, 1250)
        frags.append([CX + R * math.cos(ac), CY + R * math.sin(ac), math.cos(ac) * sp, math.sin(ac) * sp,
                      ac, 2 * math.pi / N * 0.85, R, 0.0, rng.uniform(-5, 5), neon.mix(PAL["ring"], (1, .2, .2), 0.7), t])
    for _ in range(80):
        a = rng.uniform(0, 2 * math.pi)
        sparks.append([CX + R * math.cos(a), CY + R * math.sin(a), rng.uniform(10, 26), t, COLS[int(rng.integers(NC))]])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    alive[N_GAP] = False
    events.append((t, "burst", N_GAP))

def physics_step(dt):
    global p, v, cur, ring_t0, hit_flash, edge_flash, heat, fill, final_t0, burst_pending, n_bounce, n_block
    p += v * dt
    if burst_t is not None:
        return
    n = len(p)
    k = cur
    m = r ** 2
    if n > 1:
        for it in range(3 if k == N_GAP else 1):
            d = p[None, :, :] - p[:, None, :]
            dd = np.hypot(d[..., 0], d[..., 1])
            rr_ = r[None, :] + r[:, None]
            ii, jj = np.where(np.triu(dd < rr_, 1))
            for i, j in zip(ii, jj):
                dist = dd[i, j]
                if dist < 1e-3:
                    a_ = rng.uniform(0, 2 * math.pi); nrm = np.array([math.cos(a_), math.sin(a_)]); dist = 1e-3
                else:
                    nrm = (p[j] - p[i]) / dist
                over = min(rr_[i, j] - dist, 6.0)
                wi = m[j] / (m[i] + m[j])
                p[i] -= nrm * over * wi; p[j] += nrm * over * (1 - wi)
                if it == 0:
                    rel = np.dot(v[j] - v[i], nrm)
                    if rel < 0:
                        imp = 2 * rel / (1 / m[i] + 1 / m[j])
                        v[i] += nrm * imp / m[i]; v[j] -= nrm * imp / m[j]
                        song.sfx(t, "tick", float((p[i][0] - CX) / 500), 0.18)
    R = RADII[k]
    rr = rot(k, t)
    g = gap_now(k, t)
    d = p - (CX, CY)
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-9
    escaped = None
    passing[dist + r < R - 0.5] = False
    for i in np.where(dist + r > R)[0]:
        bh = math.asin(min(0.999, r[i] / R))
        rel = wrap(math.atan2(d[i, 1], d[i, 0]) - rr)
        fits = k < N_GAP and bh * 0.92 < g / 2
        in_gap = passing[i] or (fits and abs(rel) + bh * 0.92 < g / 2)
        if in_gap:
            passing[i] = True
            if dist[i] > R + r[i] * 0.3 and escaped is None:
                escaped = i
            continue
        if dist[i] > R + r[i] * 0.5:
            continue
        u = d[i] / dist[i]
        p[i] -= u * (dist[i] + r[i] - R)
        vn = np.dot(v[i], u)
        if vn > 0:
            v[i] -= 2 * vn * u
            jit = rng.uniform(-0.12, 0.12)
            c, s_ = math.cos(jit), math.sin(jit)
            v[i] = [v[i][0] * c - v[i][1] * s_, v[i][0] * s_ + v[i][1] * c]
            pan = float(d[i, 0] / R)
            song.note(t, pan)
            n_bounce += 1
            hx, hy = p[i] + u * r[i]
            near_gap = k < N_GAP and abs(rel) < g / 2 + bh
            if near_gap:                    # too big for the gap: bounced off its edge
                n_block += 1
                edge_flash = 1.0
                sparks.extend([[hx, hy, rng.uniform(8, 16), t, COLS[col_of(r[i])]] for _ in range(3)])
            else:
                hit_flash = 1.0
                sparks.append([hx, hy, rng.uniform(6, 12), t, COLS[col_of(r[i])]])
            grow(i, k)
    if escaped is not None:
        pan = float(d[escaped, 0] / R)
        shatter(k, t, pan)
        sparks.extend([[p[escaped][0], p[escaped][1], rng.uniform(10, 22), t, COLS[col_of(r[escaped])]] for _ in range(8)])
        song.sfx(t + 0.05, "pop", pan, 0.8)
        split(escaped)
        cur += 1
        ring_t0 = t
        if cur == N_GAP:
            final_t0 = t
            events.append((t, "final", cur))
            print("fill at final", round(float(np.sum(r ** 2) / RADII[N_GAP] ** 2), 3), "maxr", round(float(r.max()), 1))
    if cur == N_GAP:
        fill = float(np.sum(r ** 2) / RADII[N_GAP] ** 2)
        heat = float(np.clip((fill - 0.40) / (FILL_END - 0.40), 0, 1))
        if fill >= FILL_END and burst_pending is None:
            burst_pending = song.next_bar(t)
            events.append((t, "full", cur))
    target = SCREEN_SPEED / z
    sp = np.hypot(v[:, 0], v[:, 1]) + 1e-6
    v *= (target / sp)[:, None]

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
sprite_cache = {}

def sprites_for(rpx):
    q = max(4, int(round(rpx / 2.0) * 2))
    if q not in sprite_cache:
        sprite_cache[q] = neon.SkinSprites(COLS, q, skin=SKIN, glow=2.6 if q > 40 else 3.2)
    return sprite_cache[q]

def S(x, y):
    return CX + (x - CX) * z, CY + (y - CY) * z

def arc_tube(R, a0, a1, rgb, alpha=1.0, heat_=0.0, width=5.0, glow=1.0):
    c = neon.mix(rgb, (1.0, 0.18, 0.22), heat_)
    pl = 1.0 + heat_ * 0.6 * (0.5 + 0.5 * math.sin(t * 26))
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for w, a in [(46, 0.05), (28, 0.09), (16, 0.16), (9, 0.35)]:
        ctx.set_source_rgba(*c, a * pl * alpha * glow); ctx.set_line_width(w * pl)
        ctx.new_path(); ctx.arc(CX, CY, R, a0, a1); ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.65), 0.95 * alpha); ctx.set_line_width(width)
    ctx.new_path(); ctx.arc(CX, CY, R, a0, a1); ctx.stroke(); ctx.restore()

def gap_caps(R, rr, g, c, alpha, flash):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for a in (rr - g / 2, rr + g / 2):
        ex, ey = CX + R * math.cos(a), CY + R * math.sin(a)
        rad = 22 + 16 * flash
        gr = cairo.RadialGradient(ex, ey, 0, ex, ey, rad)
        gr.add_color_stop_rgba(0, *neon.mix(c, (1, 1, 1), 0.6), (0.8 + 0.2 * flash) * alpha)
        gr.add_color_stop_rgba(0.45, *c, 0.4 * alpha); gr.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(gr); ctx.arc(ex, ey, rad, 0, 2 * math.pi); ctx.fill()
    ctx.restore()

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gcol = neon.mix(ring_color(min(cur, N_GAP)), (1.0, 0.3, 0.35), heat * 0.8)
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 900)
    ga = 0.04 + 0.14 * pr + 0.03 * math.sin(t * 2.0)
    if burst_t is not None:
        ga *= math.exp(-(t - burst_t) * 1.5)
    rg.add_color_stop_rgba(0, *gcol, ga); rg.add_color_stop_rgba(1, *gcol, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    shake = 0.0
    if burst_t is None and heat > 0.45:
        shake = 9 * ((heat - 0.45) / 0.55) ** 2
    if burst_t is not None:
        shake = 28 * math.exp(-(t - burst_t) * 6)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    for k in range(N_GAP, -1, -1):
        if not alive[k]:
            continue
        R = RADII[k] * z
        if R > 1400:
            continue
        rr = rot(k, t)
        is_cur = k == cur
        alpha = 1.0 if is_cur else max(0.25, 0.75 - 0.08 * (k - cur))
        glow = 1.0 + (0.6 * hit_flash if is_cur else 0.0)
        if k == N_GAP:
            arc_tube(R, 0, 2 * math.pi, PAL["ring"], alpha, heat if is_cur else 0.0, 6.0, glow)
        else:
            g = gap_now(k, t) if is_cur else 2 * math.asin(BR / RADII[k]) * 1.4
            arc_tube(R, rr + g / 2, rr + 2 * math.pi - g / 2, ring_color(k), alpha, 0.0, 5.0, glow)
            if is_cur:
                gap_caps(R, rr, g, ring_color(k), alpha, edge_flash)
    # fragments
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for fx, fy, _vx, _vy, ac, span, R_, frot, _vr, fc, ft0 in frags:
        age = t - ft0
        fa = max(0.0, 1 - age / 2.2)
        if fa <= 0:
            continue
        sx, sy = S(fx, fy)
        ctx.save(); ctx.translate(sx, sy); ctx.rotate(frot)
        for w_, a_ in [(16, 0.16), (6, 0.9)]:
            ctx.set_source_rgba(*fc, a_ * fa); ctx.set_line_width(w_)
            ctx.new_path(); ctx.arc(-R_ * z * math.cos(ac), -R_ * z * math.sin(ac), R_ * z, ac - span / 2, ac + span / 2); ctx.stroke()
        ctx.restore()
    ctx.restore()
    # shockwaves
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, k in events:
        if kind not in ("break", "burst"):
            continue
        age = t - et
        dur = 0.7 if kind == "break" else 1.2
        if 0 <= age < dur:
            a = (1 - age / dur) * (0.5 if kind == "break" else 0.8)
            c = ring_color(k) if kind == "break" else PAL["accent"]
            ctx.set_source_rgba(*c, a); ctx.set_line_width(3 + 16 * a)
            ctx.new_path(); ctx.arc(CX, CY, RADII[k] * z + (500 if kind == "break" else 2200) * age, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
    # balls, grouped by on-screen size
    groups = {}
    for (x, y), rad, f in zip(p, r, pulse):
        sx, sy = S(x, y)
        rp = rad * z
        if -rp * 3 < sx < W + rp * 3 and -rp * 3 < sy < H + rp * 3:
            groups.setdefault(max(4, int(round(rp / 2.0) * 2)), []).append(((sx, sy), col_of(rad), f, rp))
    for q in sorted(groups):
        items = groups[q]
        spr = sprites_for(q)
        spr.draw(ctx, [it[0] for it in items], [it[1] for it in items])
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for q, items in groups.items():
        for (x, y), c, f, rp in items:
            age = t - f
            if 0 <= age < 0.22:
                a = 1 - age / 0.22
                ctx.set_source_rgba(*neon.mix(COLS[c], (1, 1, 1), 0.55), 0.55 * a); ctx.set_line_width(2.5)
                ctx.new_path(); ctx.arc(x, y, rp * (1.0 + 0.5 * (1 - a)) + 2, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
    live = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = live
    by_col = {}
    for x, y, sz, st, c in live:
        a = 1 - (t - st) / 0.5
        sx, sy = S(x, y)
        by_col.setdefault((c, round(a, 1)), []).append((sx, sy, sz * (0.6 + a)))
    for (c, a), pts_ in by_col.items():
        neon.sparkles(ctx, pts_, neon.mix(c, (1, 1, 1), 0.4), alpha=a * 0.9)
    ctx.restore()
    if counter and burst_t is None:
        left = sum(alive)
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(120)
        txt = str(left)
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1690)
        ctx.text_path(txt)
        cc = neon.mix(ring_color(min(cur, N_GAP)), (1, 1, 1), 0.45)
        cc = neon.mix(cc, (1, .3, .3), heat)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(22); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.95); ctx.fill()
        ctx.restore()
    if burst_t is not None:
        fa = max(0.0, 0.5 - (t - burst_t) * 2.5)
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
maxr_log = []
while True:
    for _ in range(SUB):
        physics_step(dt)
        if burst_pending is not None and burst_t is None and t >= burst_pending:
            do_burst()
        for f in frags:
            f[0] += f[2] * dt; f[1] += f[3] * dt; f[7] += f[8] * dt
        t += dt
    zt = zoom_for(RADII[min(cur, N_GAP)])
    if burst_t is not None:
        zt = zoom_for(R_FINAL) * 0.92
    z += (zt - z) * 0.035
    hit_flash *= 0.82
    edge_flash *= 0.85
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if frame % 300 == 0:
        maxr_log.append((round(t), cur, len(p), round(float(r.max()), 1), round(fill, 2)))
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
brk = [round(e[0], 1) for e in events if e[1] == "break"]
print("seed", SEED, "breaks", brk)
print("intervals", [round(b - a, 1) for a, b in zip([0] + brk, brk)])
print("final_t0", final_t0 and round(final_t0, 1), "burst", burst_t and round(burst_t, 2), "duration", round(t, 2),
      "balls", len(p), "bounces", n_bounce, "blocked", n_block, "fill", round(fill, 2))
print("log", maxr_log)
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
