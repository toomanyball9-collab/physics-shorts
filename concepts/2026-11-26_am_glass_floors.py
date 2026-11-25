"""2026-11-26 08:00 — chain-reaction (new family): "Glass Floors"
A tall neon column with a stack of glass floors. A dropper at the top drops a ball on the beat
(1 -> 2 -> 4 -> 8 per beat, switching on bar lines; colour changes every 4 bars so the piles show layers).
Every glass floor has a visible strength (thicker glass = holds more). The pile on a floor makes it glow,
heat red, sag and shake; when the weight is more than it can hold, it shatters on the beat and the whole
pile crashes down onto the next floor (the camera follows). The thin floor can't take the crash and breaks
straight away (chain reaction). The bottom basin fills until it is completely packed, heats red, and on the
bar it gives way under the weight: everything falls out of the bottom. Tail crossfades to the opening.
Sound: floor/wall bounces = music (song.note); floor breaking = shatter; heavy pile landing = thump.

usage: python3 concepts/2026-11-26_am_glass_floors.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 6
ITERS = int(os.environ.get('ITERS', '8'))
CL, CR = 200.0, 880.0
CXC = (CL + CR) / 2
BR = 13.0
G = 1500.0
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
DEBUG = "DEBUG" in os.environ
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
MUSIC_SEED = int(os.environ.get("MSEED", "2026112611"))
RECENT = [dict(genre="celtic", bpm=116, key="A#", mode="mixolydian", lead="flute"),
          dict(genre="jazzhop", bpm=89, key="C", mode="major", lead="harp"),
          dict(genre="trance_lite", bpm=123, key="F", mode="minor", lead="pluck"),
          dict(genre="bossa", bpm=96, key="G#", mode="major", lead="ep"),
          dict(genre="space", bpm=76, key="B", mode="lydian", lead="bell"),
          dict(genre="desert", bpm=104, key="F#", mode="phrygian_dominant", lead="flute"),
          dict(genre="chiptune", bpm=124, key="F#", mode="mixolydian", lead="square")]
song = music.random_song(MUSIC_SEED, avoid=RECENT)
BEAT = song.beat
BAR = song.chord_len

# ---- floors (world y of the top surface centre line), strength = balls it can hold, thickness shows it
DROP_Y = 215.0
F0 = 1240.0
GAP = 560.0
CAPS = [int(x) for x in os.environ.get("CAPS", "8,30,60,10,115,180").split(",")]
THICK = [9, 13, 18, 4, 24, 30]
NGLASS = len(CAPS)
FLOOR_Y = [F0 + k * GAP for k in range(NGLASS)]
BASIN_GAP = float(os.environ.get("BGAP", "380"))
BASIN_Y = FLOOR_Y[-1] + BASIN_GAP
BASIN_T = 34
TIERS = [float(x) for x in os.environ.get("TIERS", "8,20,34").split(",")]   # seconds where 1->2->4->8 (snapped to bars)
TIER_BARS = [math.ceil(x / BAR) for x in TIERS]

PAL_COLS = [(0.35, 1.0, 0.80), (0.30, 0.78, 1.0), (0.55, 0.55, 1.0), (0.85, 0.50, 1.0), (1.0, 0.55, 0.80)]
GLASS = (0.80, 0.93, 1.0)
PAL = {"bg": ((0.01, 0.03, 0.07), (0.00, 0.01, 0.03)), "ring": GLASS, "balls": PAL_COLS, "accent": (1, 1, 1)}

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 777)
wall_rng = np.random.default_rng(SEED + 31)

p = np.zeros((0, 2)); v = np.zeros((0, 2)); col = np.zeros(0, int)
note_cool = np.zeros(0)
intact = [True] * NGLASS
broken_t = [None] * NGLASS
break_pending = [None] * NGLASS
heat = [0.0] * (NGLASS + 1)
load_now = [0] * (NGLASS + 1)
basin_full_t = None
basin_pending = None
payoff_t = None
t = 0.0
cam = 0.0
shards, sparks, events, build_keys = [], [], [], []
next_drop = 0.0
drop_k = 0
max_load = 0
thump_cool = -9.0


def per_beat(tt):
    b = int(tt / BAR)
    n = 1
    for tb in TIER_BARS:
        if b >= tb:
            n *= 2
    return n


def nozzle_x(tt):
    return CXC + 255 * math.sin(2 * math.pi * tt / (8 * BEAT) + 0.6)


def cur_col(tt):
    return int(tt / (4 * BAR)) % len(PAL_COLS)


def active():
    for k in range(NGLASS):
        if intact[k]:
            return k
    return NGLASS          # basin


def floor_y(k):
    return BASIN_Y if k == NGLASS else FLOOR_Y[k]


def floor_th(k):
    return BASIN_T if k == NGLASS else THICK[k]


def sag(k):
    return 16.0 * max(0.0, (heat[k] - 0.55) / 0.45) ** 1.5


def surface(k, x):
    u = (x - CXC) / ((CR - CL) / 2)
    return floor_y(k) - floor_th(k) / 2 + sag(k) * (1 - u * u)


def progress():
    if payoff_t is not None:
        return 1.0
    k = active()
    base = k / (NGLASS + 1)
    return float(np.clip(0.1 + 0.75 * (base + heat[k] / (NGLASS + 1)) + 0.15 * min(1, t / 60), 0, 1))


def release():
    global p, v, col, note_cool, next_drop, drop_k
    while t >= next_drop and payoff_t is None and basin_full_t is None:
        x = nozzle_x(next_drop) + rng.uniform(-3, 3)
        p = np.vstack([p, [x, DROP_Y + 10]])
        v = np.vstack([v, [rng.uniform(-30, 30), 120.0]])
        col = np.append(col, cur_col(next_drop))
        note_cool = np.append(note_cool, -9.0)
        drop_k += 1
        next_drop += BEAT / per_beat(next_drop + 1e-6)


def shatter_floor(k):
    """break floor k into glowing glass shards."""
    y = floor_y(k)
    th = floor_th(k)
    n = 16 if k < NGLASS else 22
    xs = np.linspace(CL, CR, n + 1)
    c = neon.mix(GLASS, (1.0, 0.2, 0.25), heat[k])
    for a, b in zip(xs[:-1], xs[1:]):
        L = b - a
        xm = (a + b) / 2
        u = (xm - CXC) / ((CR - CL) / 2)
        shards.append(dict(x=xm, y=y + sag(k) * (1 - u * u), vx=fx_rng.uniform(-160, 160) + u * 120,
                           vy=fx_rng.uniform(-260, 40), a=0.0, va=fx_rng.uniform(-7, 7), L=L * 0.9, th=th, c=c, t0=t))
    for _ in range(60):
        sparks.append([fx_rng.uniform(CL, CR), y + fx_rng.normal(0, 10), fx_rng.uniform(8, 20), t, c])
    song.sfx(t, "shatter", 0.0, 0.85 if k < NGLASS else 1.0)
    events.append((t, "break", k))


def physics_step(dt):
    """position-based dynamics: predict, project contacts a few times, derive velocity -> stable deep piles."""
    global p, v, col, note_cool, basin_full_t, basin_pending, thump_cool, max_load
    n = len(p)
    if n:
        v[:, 1] += G * dt
        v -= v * 0.12 * dt
        sp = np.hypot(v[:, 0], v[:, 1])
        fast = sp > 1250
        if fast.any():
            v[fast] *= (1250 / sp[fast])[:, None]
        pp = p.copy()
        p += v * dt
        k = active()
        y0 = floor_y(k)
        th = floor_th(k)
        # impacts (velocity before projection) -> notes / thump
        lo = np.where((p[:, 0] < CL + BR) & (v[:, 0] < -260))[0]
        hi = np.where((p[:, 0] > CR - BR) & (v[:, 0] > 260))[0]
        for idx, s in ((lo, 1), (hi, -1)):
            for ii in idx:
                if t - note_cool[ii] > 0.3:
                    note_cool[ii] = t
                    song.note(t, -0.8 * s, vel=min(1.0, 0.35 + abs(v[ii, 0]) / 1500))
        near = np.where((p[:, 1] > y0 - th / 2 - BR - 30) & (p[:, 1] < y0 + th / 2 + 20))[0]
        sy = np.array([surface(k, x) for x in p[near, 0]]) if len(near) else np.zeros(0)
        hit = near[(p[near, 1] > sy - BR) & (v[near, 1] > 0)] if len(near) else near
        landing = float(v[hit, 1].sum()) if len(hit) else 0.0
        for ii in hit:
            if v[ii, 1] > 300 and t - note_cool[ii] > 0.3:
                note_cool[ii] = t
                song.note(t, float((p[ii, 0] - CXC) / 400), vel=min(1.0, 0.35 + v[ii, 1] / 1800))
        if landing > 9000 and t - thump_cool > 0.25:
            thump_cool = t
            song.sfx(t, "thump", 0.0, min(1.0, landing / 30000))
            events.append((t, "thump", k))
        WJ = wall_rng.uniform(0.0, 2.5, n)        # walls are not perfectly smooth: no impossible vertical columns
        if payoff_t is not None:
            near = near[:0]; hit = hit[:0]
        pairs = cKDTree(p).query_pairs(2 * BR + 1.0, output_type="ndarray") if n > 1 else np.zeros((0, 2), int)
        i, j = (pairs[:, 0], pairs[:, 1]) if len(pairs) else (None, None)
        for it in range(ITERS):
            if i is not None:
                d = p[j] - p[i]
                dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
                over = 2 * BR - dist
                m = over > 0
                if m.any():
                    corr = (d[m] / dist[m, None]) * (over[m] * 0.5)[:, None]
                    np.add.at(p, i[m], -corr); np.add.at(p, j[m], corr)
            wl = p[:, 0] < CL + BR; wr = p[:, 0] > CR - BR
            if wl.any():
                p[wl, 0] = CL + BR + WJ[wl]
            if wr.any():
                p[wr, 0] = CR - BR - WJ[wr]
            if len(near):
                sy = np.array([surface(k, x) for x in p[near, 0]])
                below = p[near, 1] > sy - BR
                if below.any():
                    p[near[below], 1] = sy[below] - BR
        nv = (p - pp) / dt
        if i is not None:                       # resting contacts lose a little energy (no boiling deep piles)
            cnt = np.bincount(np.concatenate([i, j]), minlength=n)
            calm = cnt >= 3
            nv[calm] *= 1 - 6 * dt
        # floor contact: a little friction, tiny bounce for fast drops
        if len(hit):
            nv[hit, 0] *= 0.9
            nv[hit, 1] = np.minimum(nv[hit, 1], -0.18 * v[hit, 1])
        sp = np.hypot(nv[:, 0], nv[:, 1])
        fast = sp > 1400
        if fast.any():
            nv[fast] *= (1400 / sp[fast])[:, None]
        v = nv
        # load on the active floor = balls in its chamber
        top = y0 - (GAP if k < NGLASS else BASIN_GAP)
        inch = (p[:, 1] > top) & (p[:, 1] < y0)
        load = int(inch.sum())
        load_now[k] = load
        touching = len(near) > 0
        if k < NGLASS:
            heat[k] = min(1.0, load / CAPS[k])
            if load >= CAPS[k] and touching and break_pending[k] is None:
                break_pending[k] = math.ceil(t / BEAT - 1e-9) * BEAT
        else:
            # basin is completely packed when the settled pile reaches the stubs of the last glass floor
            sl = inch & (np.hypot(v[:, 0], v[:, 1]) < 70)
            ys = np.sort(p[sl, 1])
            topy = ys[min(7, len(ys) - 1)] if len(ys) >= 30 else y0
            fill = (y0 - topy) / BASIN_GAP
            if DEBUG and int(t*360) % 360 == 0:
                spd = np.hypot(v[inch, 0], v[inch, 1])
                print(f"t={t:.1f} load={load} fill={fill:.2f} settled={int(sl.sum())} medspd={np.median(spd) if len(spd) else 0:.0f} p90={np.percentile(spd,90) if len(spd) else 0:.0f}")
            heat[k] = max(heat[k], float(np.clip((fill - 0.3) / 0.6, 0, 1)))
            max_load = max(max_load, load)
            if fill >= 0.93 and basin_full_t is None:
                basin_full_t = t
                basin_pending = song.next_bar(t + 0.05)
                song.sfx(t, "chime", 0.0, 0.6)
        # remove balls far below (after the payoff)
        keep = p[:, 1] < cam + H + 400
        if not keep.all():
            p, v, col, note_cool = p[keep], v[keep], col[keep], note_cool[keep]
    # shards
    for s in shards:
        s["vy"] += G * 0.8 * dt
        s["x"] += s["vx"] * dt; s["y"] += s["vy"] * dt; s["a"] += s["va"] * dt


def do_breaks():
    global payoff_t
    for k in range(NGLASS):
        if intact[k] and break_pending[k] is not None and t >= break_pending[k]:
            intact[k] = False
            broken_t[k] = t
            shatter_floor(k)
    if basin_pending is not None and payoff_t is None and t >= basin_pending:
        payoff_t = t
        song.accent(t)
        shatter_floor(NGLASS)


# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SPR = neon.BallSprites(PAL_COLS, BR, glow=2.6, glow_alpha=0.5)


def glass_path(k, ox):
    th = floor_th(k)
    n = 24
    xs = np.linspace(CL, CR, n)
    top = [(x + ox, surface(k, x) - cam) for x in xs]
    bot = [(x + ox, surface(k, x) + th - cam) for x in xs[::-1]]
    return top, bot


def draw_floor(k, ox):
    hk = heat[k]
    c = neon.mix(GLASS, (1.0, 0.2, 0.25), max(0.0, (hk - 0.35) / 0.65))
    pulse = 1.0 + (0.5 * (0.5 + 0.5 * math.sin(t * 24)) * max(0, hk - 0.75) / 0.25 if hk > 0.75 else 0)
    th = floor_th(k)
    top, bot = glass_path(k, ox)
    mid = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(top, bot[::-1])]
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for w_, a_ in ((th + 40, 0.05), (th + 22, 0.09), (th + 10, 0.16)):
        ctx.set_source_rgba(*c, a_ * pulse * (1.4 + 0.6 * hk)); ctx.set_line_width(w_)
        ctx.move_to(*mid[0])
        for q in mid[1:]: ctx.line_to(*q)
        ctx.stroke()
    ctx.restore()
    # translucent glass body + bright edges
    ctx.move_to(*top[0])
    for q in top[1:] + bot: ctx.line_to(*q)
    ctx.close_path()
    ctx.set_source_rgba(*c, 0.30 + 0.25 * hk); ctx.fill()
    ctx.set_line_width(2.5); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.65), 0.95)
    ctx.move_to(*top[0])
    for q in top[1:]: ctx.line_to(*q)
    ctx.stroke()
    ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.3), 0.6)
    ctx.move_to(*bot[0])
    for q in bot[1:]: ctx.line_to(*q)
    ctx.stroke()
    # glass glints
    ctx.set_source_rgba(1, 1, 1, 0.35)
    for gx in (0.18, 0.47, 0.79):
        x = CL + gx * (CR - CL)
        y = surface(k, x) - cam + th * 0.35
        ctx.move_to(x - 22 + ox, y); ctx.line_to(x + 8 + ox, y); ctx.set_line_width(max(1.5, th * 0.18)); ctx.stroke()


def draw_walls(ox):
    ytop = max(60.0, cam - 50) - cam
    ybot = min(BASIN_Y + BASIN_T / 2 + 6, cam + H + 50) - cam
    if ybot <= ytop:
        return
    k = active()
    c = neon.mix(GLASS, PAL_COLS[cur_col(t)], 0.35)
    for x in (CL - 7 + ox, CR + 7 + ox):
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for w_, a_ in ((40, 0.04), (24, 0.08), (13, 0.15), (7, 0.32)):
            ctx.set_source_rgba(*c, a_); ctx.set_line_width(w_)
            ctx.move_to(x, ytop); ctx.line_to(x, ybot); ctx.stroke()
        ctx.restore()
        ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.6), 0.95); ctx.set_line_width(4.5)
        ctx.move_to(x, ytop); ctx.line_to(x, ybot); ctx.stroke()
    # stubs of broken floors
    for kk in range(NGLASS):
        if not intact[kk]:
            y = FLOOR_Y[kk] - cam
            if -40 < y < H + 40:
                ctx.set_source_rgba(*neon.mix(GLASS, (1, 1, 1), 0.3), 0.7); ctx.set_line_width(THICK[kk])
                ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                for x0, x1 in ((CL - 4, CL + 14), (CR - 14, CR + 4)):
                    ctx.move_to(x0 + ox, y); ctx.line_to(x1 + ox, y); ctx.stroke()


def draw_dropper(ox):
    y = DROP_Y - cam
    if y < -80:
        return
    x = nozzle_x(t) + ox
    c = PAL_COLS[cur_col(t)]
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.RadialGradient(x, y, 0, x, y, 80)
    g.add_color_stop_rgba(0, *c, 0.35); g.add_color_stop_rgba(1, *c, 0)
    ctx.set_source(g); ctx.arc(x, y, 80, 0, 2 * math.pi); ctx.fill(); ctx.restore()
    ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.5), 0.95); ctx.set_line_width(5); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.move_to(x - 34, y - 30); ctx.line_to(x - 12, y); ctx.line_to(x + 12, y); ctx.line_to(x + 34, y - 30); ctx.stroke()
    # rail
    ctx.set_source_rgba(*c, 0.25); ctx.set_line_width(2)
    ctx.move_to(CXC - 290 + ox, y - 30); ctx.line_to(CXC + 290 + ox, y - 30); ctx.stroke()


def draw(counter=False):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    k = active()
    hk = heat[min(k, NGLASS)]
    gc = neon.mix(PAL_COLS[cur_col(t)], (1.0, 0.3, 0.3), max(0, hk - 0.6) / 0.4 * 0.6)
    rg = cairo.RadialGradient(W / 2, H * 0.55, 0, W / 2, H * 0.55, 1100)
    ga = 0.04 + 0.10 * pr
    if payoff_t is not None:
        ga = 0.06 + 0.2 * math.exp(-(t - payoff_t) * 1.2)
    rg.add_color_stop_rgba(0, *gc, ga); rg.add_color_stop_rgba(1, *gc, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()
    shake = 0.0
    if hk > 0.8 and payoff_t is None:
        shake = 3.5 * (hk - 0.8) / 0.2
    for kk in range(NGLASS):
        if broken_t[kk] is not None and t - broken_t[kk] < 0.4:
            shake = max(shake, 10 * (1 - (t - broken_t[kk]) / 0.4))
    if payoff_t is not None:
        shake = max(shake, 16 * math.exp(-(t - payoff_t) * 5))
    ox = fx_rng.uniform(-shake, shake) if shake > 0 else 0.0
    oy = fx_rng.uniform(-shake, shake) if shake > 0 else 0.0
    ctx.save(); ctx.translate(0, oy)
    draw_walls(ox)
    draw_dropper(ox)
    for kk in range(NGLASS):
        if intact[kk]:
            y = FLOOR_Y[kk] - cam
            if -60 < y < H + 60:
                draw_floor(kk, ox)
    if payoff_t is None and -60 < BASIN_Y - cam < H + 60:
        draw_floor(NGLASS, ox)
    # balls
    vis = (p[:, 1] > cam - 40) & (p[:, 1] < cam + H + 40)
    pts = [(x + ox, y - cam) for x, y in p[vis]]
    SPR.draw(ctx, pts, list(col[vis]))
    # shards
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    live = []
    for s in shards:
        age = t - s["t0"]
        if age > 2.5 or s["y"] - cam > H + 100:
            continue
        live.append(s)
        a = max(0.0, 1 - age / 2.5)
        x, y = s["x"] + ox, s["y"] - cam
        dx, dy = math.cos(s["a"]) * s["L"] / 2, math.sin(s["a"]) * s["L"] / 2
        for w_, al in ((s["th"] + 16, 0.12), (s["th"] + 4, 0.35), (max(2.0, s["th"] * 0.5), 0.9)):
            ctx.set_source_rgba(*neon.mix(s["c"], (1, 1, 1), 0.3 if al > 0.5 else 0), al * a); ctx.set_line_width(w_)
            ctx.move_to(x - dx, y - dy); ctx.line_to(x + dx, y + dy); ctx.stroke()
    shards[:] = live
    ctx.restore()
    lv = [s for s in sparks if t - s[3] < 0.6]
    sparks[:] = lv
    for x, y, sz, st, c in lv:
        al = 1 - (t - st) / 0.6
        neon.sparkles(ctx, [(x + ox, y - cam - 60 * (t - st), sz * (0.5 + al))], neon.mix(c, (1, 1, 1), 0.5), alpha=al * 0.9)
    ctx.restore()
    if counter and payoff_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(84)
        txt = f"{drop_k}"
        xb, yb, tw, th_, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1800)
        ctx.text_path(txt)
        cc = neon.mix(PAL_COLS[cur_col(t)], (1, 1, 1), 0.4)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(18); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.92); ctx.fill()
        ctx.restore()
    if payoff_t is not None:
        dtp = t - payoff_t
        fa = max(0.0, 0.5 - dtp * 2.8)
        if fa > 0:
            ctx.set_source_rgba(1, 1, 1, fa); ctx.paint()
        if dtp < 1.2:
            a = 1 - dtp / 1.2
            yb_ = BASIN_Y - cam
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*GLASS, 0.7 * a); ctx.set_line_width(4 + 16 * a)
            ctx.new_path(); ctx.arc(W / 2, yb_, 60 + 1300 * dtp, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
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
        release()
        physics_step(dt)
        do_breaks()
        t += dt
    # camera follows the loaded floor
    k = active()
    target = max(0.0, floor_y(k) - 1240)
    if payoff_t is not None:
        target = max(0.0, BASIN_Y - 1240)
    cam += (target - cam) * min(1.0, 2.2 / FPS)
    if frame % 15 == 0:
        build_keys.append((t, progress()))
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
print("seed", SEED, "breaks", [b and round(b, 1) for b in broken_t], "basin full", basin_full_t and round(basin_full_t, 1),
      "payoff", payoff_t and round(payoff_t, 2), "duration", round(t, 2), "drops", drop_k, "basin load", max_load)
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
