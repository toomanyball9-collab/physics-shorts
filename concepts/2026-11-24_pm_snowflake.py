"""2026-11-24 18:00 — crystal-growth (new family): "Snowflake"
A tiny ice seed floats in the middle of a neon ring (zero gravity).
  Rule 1: six vents in the ring release a drifting ball on the beat (1 per beat, then 2, then 4 as the song builds).
  Rule 2: a ball that touches the crystal FREEZES onto it — and the crystal copies it six ways (with mirror
          images, like a real snowflake), so every freeze grows all six arms at once.
Balls drift with a little jitter (like flakes in air), so the arms branch into a dendritic snowflake; colour
shows when each part froze. The closer a tip gets to the ring the colder (whiter) that part of the ring glows.
When an arm touches the ring the frost spreads around it, and like ice in a rock crack it splits the ring on the
bar: the ring shatters outward, the free balls fly out, the finished snowflake flashes. Tail crossfades to start.

usage: python3 concepts/2026-11-24_pm_snowflake.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 4
CX, CY = W / 2, 900.0
R = 455.0                         # ring radius
BR = float(os.environ.get("BR", "7.0"))   # ball radius (free and frozen)
SPEED = float(os.environ.get("SPEED", "430"))
JIT = float(os.environ.get("JIT", "2.2"))    # angular jitter rad/sqrt(s)
SYM_MIRROR = os.environ.get("MIRROR", "1") == "1"
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
# random_song(2026112405, avoid=last 12 recipes) -> space 76 B lydian bell (checked vs rules and vs the 08:00 bossa)
MUSIC_SEED = 2026112405
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
          dict(genre="trance_lite", bpm=123, key="F", mode="minor", lead="pluck")]
song = music.random_song(MUSIC_SEED, avoid=RECENT)
BAR = song.chord_len
T2 = float(os.environ.get("T2", "22")); T3 = float(os.environ.get("T3", "44")); T4 = float(os.environ.get("T4", "99"))
RATE0 = float(os.environ.get("RATE0", "0.5"))
TEXP = float(os.environ.get("TEXP", "58"))   # expected contact time (colour bands only)

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)

ICE = [(0.40, 0.42, 1.0), (0.30, 0.62, 1.0), (0.22, 0.85, 1.0), (0.35, 1.0, 0.92),
       (0.65, 1.0, 0.88), (0.85, 0.82, 1.0), (1.0, 0.72, 0.95)]
FREE_COL = (0.82, 0.93, 1.0)
RING_COL = (0.55, 0.45, 1.0)
FROST = (0.92, 0.98, 1.0)
PAL = {"bg": ((0.01, 0.015, 0.07), (0.00, 0.00, 0.02)), "ring": RING_COL, "balls": ICE, "accent": (1, 1, 1)}
VENTS = [math.pi / 6 + k * math.pi / 3 - math.pi / 2 for k in range(6)]   # between the six arms

# ---------------- state ----------------
fp = np.zeros((0, 2)); fv = np.zeros((0, 2))          # free balls
fborn = np.zeros(0)
cp = []          # frozen particles (x, y)
ccol = []        # colour band
cpar = []        # parent index (bond)
ct = []          # freeze time
t = 0.0
next_drop = 0.0
vent_i = 0
launches = 0
freezes = 0
contact_t = None
burst_pending = burst_t = None
reach = 0.0
frags, sparks, events, build_keys = [], [], [], []
hit_cool = {}
GC = 2 * BR                       # grid cell
NG = int(2 * R / GC) + 4
grid = -np.ones((NG, NG, 4), int)

def gcell(x, y):
    return int((x - CX + R) / GC) + 2, int((y - CY + R) / GC) + 2

def add_frozen(x, y, parent, band):
    i = len(cp)
    gx, gy = gcell(x, y)
    slot = np.where(grid[gx, gy] < 0)[0]
    if len(slot) == 0:
        return -1
    grid[gx, gy, slot[0]] = i
    cp.append((x, y)); cpar.append(parent); ccol.append(band); ct.append(t)
    return i

def near_frozen(x, y, rad):
    gx, gy = gcell(x, y)
    best, bi = 1e9, -1
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for j in grid[gx + dx, gy + dy]:
                if j >= 0:
                    d = math.hypot(cp[j][0] - x, cp[j][1] - y)
                    if d < best: best, bi = d, j
    return best, bi

def band_now():
    return int(np.clip(t / TEXP * len(ICE), 0, len(ICE) - 1))

def sym_copies(x, y):
    dx, dy = x - CX, y - CY
    r0, a0 = math.hypot(dx, dy), math.atan2(dy, dx) + math.pi / 2     # angle from 'up'
    out = []
    for k in range(6):
        for m in ((1, -1) if SYM_MIRROR else (1,)):
            a = m * a0 + k * math.pi / 3 - math.pi / 2
            out.append((CX + r0 * math.cos(a), CY + r0 * math.sin(a)))
    return out

def freeze(i, j):
    """free ball i touched frozen particle j: freeze it in contact, plus its symmetric copies."""
    global freezes, reach, contact_t
    x, y = fp[i]
    jx, jy = cp[j]
    d = math.hypot(x - jx, y - jy) + 1e-9
    x, y = jx + (x - jx) / d * 2 * BR, jy + (y - jy) / d * 2 * BR
    b = band_now()
    pan = float((x - CX) / R)
    made = []
    for k, (qx, qy) in enumerate(sym_copies(x, y)):
        rq = math.hypot(qx - CX, qy - CY)
        if rq > R - BR:              # touching the ring: sit exactly against it
            qx, qy = CX + (qx - CX) * (R - BR) / rq, CY + (qy - CY) * (R - BR) / rq
        dd, pj = near_frozen(qx, qy, BR)
        if dd < 1.55 * BR:
            continue
        idx = add_frozen(qx, qy, pj, b)
        if idx >= 0:
            made.append(idx)
    freezes += 1
    song.sfx(t, "tick", pan, 0.30)
    if freezes % 6 == 0:
        song.sfx(t + 0.01, "chime", pan, 0.18)
    for idx in made:
        qx, qy = cp[idx]
        rr = math.hypot(qx - CX, qy - CY) + BR
        reach = max(reach, rr)
        if rr >= R - 6.0 and contact_t is None:
            contact_t = t
            events.append((t, "contact", (math.atan2(qy - CY, qx - CX),)))
        for _ in range(2):
            sparks.append([qx, qy, rng.uniform(5, 11), t, ICE[b]])
    events.append((t, "freeze", (made,)))

def drops_per_beat(tt):
    return RATE0 if tt < T2 else (2 * RATE0 if tt < T3 else (4 * RATE0 if tt < T4 else 8 * RATE0))

def progress():
    if burst_t is not None:
        return 1.0
    return float(np.clip(0.2 * min(1, t / 12) + 0.8 * ((reach - 3 * BR) / (R - 3 * BR)) ** 1.3, 0, 1))

def launch():
    global fp, fv, fborn, vent_i, launches
    a = VENTS[vent_i % 6]; vent_i += 1
    x, y = CX + (R - BR - 1) * math.cos(a), CY + (R - BR - 1) * math.sin(a)
    th = a + math.pi + rng.uniform(-0.5, 0.5)
    fp = np.vstack([fp, [x, y]]); fv = np.vstack([fv, [SPEED * math.cos(th), SPEED * math.sin(th)]])
    fborn = np.concatenate([fborn, [t + 1e-4 * launches]])
    launches += 1
    song.sfx(t, "whoosh", float(math.cos(a)), 0.18)
    events.append((t, "launch", (a,)))

def remove_free(idx):
    global fp, fv, fborn
    keep = np.ones(len(fp), bool); keep[list(idx)] = False
    fp, fv, fborn = fp[keep], fv[keep], fborn[keep]

def do_burst():
    global burst_t, fv
    burst_t = t
    nseg = 40
    for j in range(nseg):
        a0, a1 = 2 * math.pi * j / nseg, 2 * math.pi * (j + 1) / nseg
        am = (a0 + a1) / 2
        sp = rng.uniform(260, 620)
        frags.append([CX + R * math.cos(am), CY + R * math.sin(am), sp * math.cos(am), sp * math.sin(am),
                      am, (a1 - a0) / 2, rng.uniform(-2.5, 2.5), 0.0])
    if len(fp):
        d = fp - (CX, CY); n = np.hypot(d[:, 0], d[:, 1])[:, None] + 1e-6
        fv = d / n * rng.uniform(500, 900, (len(fp), 1))
    for k in range(90):
        a = rng.uniform(0, 2 * math.pi)
        sparks.append([CX + R * math.cos(a), CY + R * math.sin(a), rng.uniform(10, 26), t, (1, 1, 1)])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    events.append((t, "burst", 0))

def physics_step(dt):
    global fp, fv
    n = len(fp)
    if n == 0:
        return
    if burst_t is not None:
        fp += fv * dt
        return
    # drifting flakes: constant speed, small random turning
    th = np.arctan2(fv[:, 1], fv[:, 0]) + rng.normal(0, JIT * math.sqrt(dt), n)
    sp = np.hypot(fv[:, 0], fv[:, 1])
    sp += (SPEED - sp) * 0.8 * dt
    fv = np.stack([np.cos(th), np.sin(th)], 1) * sp[:, None]
    fp += fv * dt
    # free-free collisions (elastic, equal mass)
    if n > 1:
        d = fp[None, :, :] - fp[:, None, :]
        dd = np.hypot(d[..., 0], d[..., 1])
        ii, jj = np.where(np.triu(dd < 2 * BR, 1))
        for i, j in zip(ii, jj):
            nrm = (fp[j] - fp[i]) / (dd[i, j] + 1e-9)
            over = 2 * BR - dd[i, j]
            fp[i] -= nrm * over / 2; fp[j] += nrm * over / 2
            rel = (fv[j] - fv[i]) @ nrm
            if rel < 0:
                fv[i] += rel * nrm; fv[j] -= rel * nrm
    # ring
    d = fp - (CX, CY)
    dc = np.hypot(d[:, 0], d[:, 1]) + 1e-9
    for i in np.where(dc > R - BR)[0]:
        u = d[i] / dc[i]
        fp[i] -= (dc[i] - (R - BR)) * u
        vn = fv[i] @ u
        if vn > 0:
            fv[i] -= 2 * vn * u
            key = int(fborn[i] * 1e4)
            if t - hit_cool.get(key, -9) > 0.15:
                hit_cool[key] = t
                song.note(t, float(u[0]), vel=0.6 + 0.4 * min(1, vn / SPEED))
                events.append((t, "hit", (float(CX + u[0] * R), float(CY + u[1] * R))))
    # freezing (vectorised neighbour lookup on the grid)
    gx = ((fp[:, 0] - CX + R) / GC).astype(int) + 2
    gy = ((fp[:, 1] - CY + R) / GC).astype(int) + 2
    gx = np.clip(gx, 1, NG - 2); gy = np.clip(gy, 1, NG - 2)
    cand = np.concatenate([grid[gx + ox, gy + oy] for ox in (-1, 0, 1) for oy in (-1, 0, 1)], axis=1)
    if len(cp) == 0:
        return
    cpa = np.array(cp)
    valid = cand >= 0
    cx_ = np.where(valid, cpa[np.maximum(cand, 0), 0], 1e9)
    cy_ = np.where(valid, cpa[np.maximum(cand, 0), 1], 1e9)
    dist = np.hypot(cx_ - fp[:, 0:1], cy_ - fp[:, 1:2])
    hit = np.min(dist, 1) < 2 * BR
    if np.any(hit):
        gone = []
        for i in np.where(hit)[0]:
            j = int(cand[i, np.argmin(dist[i])])
            freeze(i, j)
            gone.append(i)
        remove_free(gone)

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
FREE_SPR = neon.BallSprites([FREE_COL], BR, glow=3.4, glow_alpha=0.55)
ICE_SPR = neon.BallSprites(ICE, BR, glow=2.2, glow_alpha=0.22)
NSEG = 180

def ring_frost():
    """per-segment coldness: 1 where a crystal tip is close to the ring."""
    cold = np.zeros(NSEG)
    if not cp:
        return cold
    cpa = np.array(cp)
    d = cpa - (CX, CY)
    rr = np.hypot(d[:, 0], d[:, 1]) + BR
    near = rr > R - 150
    if np.any(near):
        ang = np.arctan2(d[near, 1], d[near, 0])
        k = (1 - (R - rr[near]) / 150) ** 2
        seg = np.linspace(-math.pi, math.pi, NSEG, endpoint=False) + math.pi / NSEG
        da = np.abs((seg[:, None] - ang[None, :] + math.pi) % (2 * math.pi) - math.pi)
        cold = np.max(k[None, :] * np.exp(-(da / 0.10) ** 2), axis=1)
    if contact_t is not None:
        # frost spreads around the ring from the contact points until the bar
        span = burst_pending - contact_t if burst_pending else 1.0
        f = min(1.0, (t - contact_t) / max(0.3, span))
        seg = np.linspace(-math.pi, math.pi, NSEG, endpoint=False) + math.pi / NSEG
        for et, kind, *info in events:
            if kind == "contact":
                a = info[0][0]
                for kk in range(6):
                    ak = a + kk * math.pi / 3
                    da = np.abs((seg - ak + math.pi) % (2 * math.pi) - math.pi)
                    cold = np.maximum(cold, np.clip(1.3 - da / (math.pi / 6 * f + 1e-3), 0, 1))
                break
    return np.clip(cold, 0, 1)

def draw_ring(cold, shake_heat):
    seg = np.linspace(-math.pi, math.pi, NSEG + 1)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    pulse = 1 + 0.35 * shake_heat * math.sin(t * 22)
    for w_, a_ in ((46, 0.05), (26, 0.10), (14, 0.18), (8, 0.35)):
        ctx.set_line_width(w_ * (1 + 0.25 * shake_heat))
        for k in range(NSEG):
            c = neon.mix(RING_COL, FROST, cold[k])
            ctx.set_source_rgba(*c, min(1.0, a_ * pulse * (1 + 0.8 * cold[k])))
            ctx.new_path(); ctx.arc(CX, CY, R, seg[k], seg[k + 1] + 0.004); ctx.stroke()
    ctx.restore()
    ctx.set_line_width(5)
    for k in range(NSEG):
        c = neon.mix(neon.mix(RING_COL, (1, 1, 1), 0.6), (1, 1, 1), cold[k])
        ctx.set_source_rgba(*c, 0.95)
        ctx.new_path(); ctx.arc(CX, CY, R, seg[k], seg[k + 1] + 0.004); ctx.stroke()

def draw_crystal(alpha=1.0):
    if not cp:
        return
    cpa = np.array(cp)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    bonds = {}
    for i, pj in enumerate(cpar):
        if pj >= 0:
            bonds.setdefault(ccol[i], []).append((cp[pj], cp[i]))
    for b, segs in bonds.items():
        for w_, a_ in ((9, 0.10), (3.5, 0.55)):
            ctx.set_source_rgba(*neon.mix(ICE[b], (1, 1, 1), 0.3), a_ * alpha); ctx.set_line_width(w_)
            for (x0, y0), (x1, y1) in segs:
                ctx.move_to(x0, y0); ctx.line_to(x1, y1)
            ctx.stroke()
    ctx.restore()
    # recent freezes flash
    ICE_SPR.draw(ctx, [tuple(q) for q in cpa], ccol, glow=True)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, *info in events[-60:]:
        if kind == "freeze" and 0 <= t - et < 0.35:
            age = (t - et) / 0.35
            for idx in info[0][0]:
                x, y = cp[idx]
                ctx.set_source_rgba(1, 1, 1, 0.6 * (1 - age)); ctx.set_line_width(2)
                ctx.new_path(); ctx.arc(x, y, BR + 14 * age, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    cold = ring_frost()
    shake_heat = float(np.clip((pr - 0.8) / 0.2, 0, 1)) if burst_t is None else 0.0
    if contact_t is not None and burst_t is None:
        shake_heat = 1.0
    gcol = neon.mix(ICE[band_now()], (1, 1, 1), 0.3)
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 900)
    ga = 0.05 + 0.13 * pr + 0.03 * math.sin(t * 1.7)
    if burst_t is not None:
        ga *= math.exp(-(t - burst_t) * 1.2)
    rg.add_color_stop_rgba(0, *gcol, ga); rg.add_color_stop_rgba(1, *gcol, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    shake = 6 * shake_heat ** 2 if burst_t is None else 24 * math.exp(-(t - burst_t) * 6)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    if burst_t is None:
        draw_ring(cold, shake_heat)
        # vents
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        for a in VENTS:
            last = max([e[0] for e in events[-80:] if e[1] == "launch" and abs(e[2][0] - a) < 1e-6] or [-9])
            pulse = max(0.0, 1 - (t - last) / 0.3)
            x, y = CX + R * math.cos(a), CY + R * math.sin(a)
            gr = cairo.RadialGradient(x, y, 0, x, y, 40)
            gr.add_color_stop_rgba(0, *FREE_COL, 0.35 + 0.6 * pulse); gr.add_color_stop_rgba(1, *FREE_COL, 0)
            ctx.set_source(gr); ctx.arc(x, y, 40, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        for a in VENTS:
            x, y = CX + R * math.cos(a), CY + R * math.sin(a)
            ctx.set_source_rgba(1, 1, 1, 0.95); ctx.arc(x, y, 6, 0, 2 * math.pi); ctx.fill()
    else:
        dt_b = t - burst_t
        sa = max(0.0, 0.7 - dt_b * 1.2)
        if sa > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(1, 1, 1, sa); ctx.set_line_width(22 * sa + 2)
            ctx.arc(CX, CY, R + 1500 * dt_b, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        fa = max(0.0, 1 - dt_b / 2.4)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for fx, fy, _vx, _vy, am, half, _vr, frot in frags:
            ctx.save(); ctx.translate(fx, fy); ctx.rotate(frot)
            for w_, a_ in ((20, 0.15), (7, 0.9)):
                ctx.set_source_rgba(*neon.mix(FROST, RING_COL, 0.25), a_ * fa); ctx.set_line_width(w_)
                ctx.new_path(); ctx.arc(-R * math.cos(am), -R * math.sin(am), R, am - half * 0.85, am + half * 0.85); ctx.stroke()
            ctx.restore()
        ctx.restore()
    # wall hit flashes
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, *info in events[-200:]:
        if kind == "hit" and 0 <= t - et < 0.3:
            x, y = info[0]; age = (t - et) / 0.3
            ctx.set_source_rgba(*FREE_COL, 0.5 * (1 - age)); ctx.set_line_width(2.5)
            ctx.new_path(); ctx.arc(x, y, 6 + 18 * age, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
    if burst_t is not None:
        ctx.save(); ctx.translate(CX, CY); ctx.rotate(0.05 * (t - burst_t)); ctx.translate(-CX, -CY)
        draw_crystal()
        ctx.restore()
    else:
        draw_crystal()
    if len(fp):
        FREE_SPR.draw(ctx, [tuple(q) for q in fp], [0] * len(fp))
    live = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = live
    groups = {}
    for x, y, sz, st, c in live:
        al = 1 - (t - st) / 0.5
        groups.setdefault((c, round(al, 1)), []).append((x, y, sz * (0.6 + al)))
    for (c, al), q in groups.items():
        neon.sparkles(ctx, q, neon.mix(c, (1, 1, 1), 0.5), alpha=al * 0.9)
    ctx.restore()
    if counter and burst_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(96)
        txt = f"{len(cp):,}"
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1640)
        ctx.text_path(txt)
        cc = neon.mix(gcol, (1, 1, 1), 0.4)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(22); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.95); ctx.fill()
        ctx.restore()
    if burst_t is not None:
        fa = max(0.0, 0.55 - (t - burst_t) * 2.5)
        if fa > 0:
            ctx.set_source_rgba(1, 1, 1, fa); ctx.paint()
        end = burst_t + TAIL
        xf = (t - (end - 1.4)) / 1.4
        if xf > 0 and first is not None:
            ctx.set_source_surface(first, 0, 0); ctx.paint_with_alpha(min(1.0, xf) ** 1.5)

def beat_gap():
    return song.beat / drops_per_beat(t)

ff = None
if not SIM_ONLY:
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", OUT
    ], stdin=subprocess.PIPE)

# opening: a tiny hexagonal ice seed, and a few flakes already drifting (one heading straight for it)
add_frozen(CX, CY, -1, 0)
for k in range(6):
    a = k * math.pi / 3 - math.pi / 2
    add_frozen(CX + 2 * BR * math.cos(a), CY + 2 * BR * math.sin(a), 0, 0)
reach = 3 * BR
for k in range(int(os.environ.get("NINIT", "16"))):
    a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(150, 380)
    th = rng.uniform(0, 2 * math.pi) if k else a + math.pi
    if k == 0: rr = 110
    fp = np.vstack([fp, [CX + rr * math.cos(a), CY + rr * math.sin(a)]])
    fv = np.vstack([fv, [SPEED * math.cos(th), SPEED * math.sin(th)]])
    fborn = np.concatenate([fborn, [-1 - k * 1e-3]])

dt = 1.0 / (FPS * SUB)
frame = 0
log = []
while True:
    for _ in range(SUB):
        if burst_pending is None and burst_t is None and t >= next_drop:
            launch()
            next_drop = round((t + beat_gap()) / beat_gap()) * beat_gap()
            if next_drop <= t: next_drop += beat_gap()
        physics_step(dt)
        if contact_t is not None and burst_pending is None:
            burst_pending = song.next_bar(t + 0.4)
        if burst_pending is not None and burst_t is None and t >= burst_pending:
            do_burst()
        for f in frags:
            f[0] += f[2] * dt; f[1] += f[3] * dt; f[7] += f[6] * dt
        t += dt
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if frame % 300 == 0:
        log.append((round(t), len(fp), len(cp), round(reach)))
    if PREVIEW and any(abs(t - pt) < 0.5 / FPS for pt in PREVIEW):
        draw(); surf.flush(); surf.write_to_png(f"prev_{t:05.1f}.png")
    if not SIM_ONLY:
        draw(); surf.flush()
        if first is None:
            first = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            c2 = cairo.Context(first); c2.set_source_surface(surf, 0, 0); c2.paint()
        ff.stdin.write(bytes(surf.get_data()))
    frame += 1
    if burst_t is not None and t >= burst_t + TAIL:
        break
    if t > 85:
        break

if ff:
    ff.stdin.close(); ff.wait()
print("seed", SEED, "log(t,free,frozen,reach)", log)
print("contact", contact_t and round(contact_t, 2), "burst", burst_t and round(burst_t, 2), "duration", round(t, 2),
      "launches", launches, "freezes", freezes, "frozen", len(cp))
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
