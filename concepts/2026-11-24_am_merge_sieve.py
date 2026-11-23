"""2026-11-24 08:00 — merge-ladder (variation): "Merge Sieve"
A tall neon capsule split in two by a SIEVE: a row of glowing pegs with gaps.
  Rule 1: the dropper at the top drops a ball on every beat (1 per beat, then 2, then 4 as the song builds).
  Rule 2: two balls of the same size touching merge into the next size up (9-step colour ladder, area conserved).
  Rule 3 (pure geometry): balls smaller than the gaps fall through the sieve; bigger ones stay on top.
So the sieve sorts: big warm balls pile up on top, small balls rain through and merge below. The top pile is
carried only by the sieve: as it packs, the pegs sag, heat red and shake; when the top chamber is completely
packed the sieve snaps on a bar line, the whole top pile crashes into the bottom chamber, and the impact breaks
the floor on the next bar — everything falls out downward. Tail crossfades back to the opening frame.

usage: python3 concepts/2026-11-24_am_merge_sieve.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 8
CX = W / 2
XL, XR = 170.0, 910.0             # capsule side walls
HW = (XR - XL) / 2
YTOP = 290.0                      # ceiling
YS = float(os.environ.get("YS", "950"))  # sieve height at the centre
SDY = float(os.environ.get("SDY", "220"))  # the sieve is TILTED: left end SDY higher, right end SDY lower
def sieve_y(x):
    return YS + SDY * (x - CX) / ((910.0 - 170.0) / 2)
YB = 1235.0                       # where the side walls meet the round floor
RB = HW                           # floor semicircle radius (centre (CX, YB))
G = 1000.0
R0 = float(os.environ.get("R0", "10.0"))
TIERS = int(os.environ.get("TIERS", "8"))
RADII = [R0 * math.sqrt(2) ** k for k in range(TIERS)]
NGAP = 12
PEG_R = 8.0
SLEN = math.hypot(XR - XL, 2 * SDY)
GAP = float(os.environ.get("GAP", "47"))
NGAP = int(round((SLEN + 2 * PEG_R) / (GAP + 2 * PEG_R)))
GAP = (SLEN - (NGAP - 1) * 2 * PEG_R) / NGAP
BLOCK = next(k for k in range(9) if 2 * R0 * math.sqrt(2) ** k > GAP)   # first size that can't pass
PEG_X = [XL + (XR - XL) * (GAP * (k + 1) + PEG_R * (2 * k + 1)) / SLEN for k in range(NGAP - 1)]
TOP_AREA = (XR - XL) * (YS - YTOP)      # (same for the tilted line: it pivots on the centre)
BOT_AREA = (XR - XL) * (YB - YS) + math.pi * RB ** 2 / 2
FILL_END = float(os.environ.get("FILL_END", "0.62"))
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
# random_song(2026112403, avoid=last 12 recipes) -> bossa 96 G# major; lead switched harp -> ep (harp was in jazzhop 2 videos ago)
song = music.Song.from_genre("bossa", seed=2026112403 * 1000 + 0, key="G#", mode="major", lead="ep")
BAR = song.chord_len
T2 = float(os.environ.get("T2", "4")); T3 = float(os.environ.get("T3", "14")); T4 = float(os.environ.get("T4", "30"))
P2 = float(os.environ.get("P2", "0.12"))   # share of big (blocked-size) drops
SMALL = [int(c) for c in os.environ.get("SMALL", "001")]

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)

# colour ladder (small -> big): rose -> coral -> amber -> gold -> lime -> mint -> cyan -> azure -> violet-white
LADDER = [(1.0, 0.42, 0.62), (1.0, 0.52, 0.42), (1.0, 0.70, 0.30), (1.0, 0.88, 0.32), (0.70, 1.0, 0.38),
          (0.35, 1.0, 0.70), (0.25, 0.85, 1.0), (0.40, 0.55, 1.0), (0.85, 0.80, 1.0)]
PAL = {"bg": ((0.05, 0.015, 0.05), (0.00, 0.00, 0.015)), "ring": (1.0, 0.8, 0.7), "balls": LADDER, "accent": (1, 0.95, 0.8)}
WALL_COL = (0.95, 0.62, 0.85)
SIEVE_COL = (1.0, 0.85, 0.55)

# ---------------- state ----------------
p = np.zeros((0, 2)); v = np.zeros((0, 2)); tier = np.zeros(0, int); born = np.zeros(0)
t = 0.0
next_drop = 0.2
drops = merges = passes = 0
top = -1
heat = 0.0          # sieve heat (top pile load)
fheat = 0.0         # floor heat (after the avalanche)
fill_top = fill_bot = 0.0
sag = 0.0
snap_pending = snap_t = None
floor_pending = floor_t = None
frags, sparks, events, build_keys = [], [], [], []
hit_cool = {}
DROP = (float(os.environ.get("DROPX", "330")), YTOP + 45)   # above the HIGH end of the sieve

def rad():
    return np.array([RADII[k] for k in tier]) if len(tier) else np.zeros(0)

def drops_per_beat(tt):
    return 1 if tt < T2 else (2 if tt < T3 else (4 if tt < T4 else 8))

def progress():
    if snap_t is not None:
        return 1.0
    return min(1.0, 0.25 * min(1, t / 14) + 0.75 * fill_top / FILL_END)

def peg_pos():
    """pegs sag under the load (parabolic, max in the middle)."""
    return [(x, sieve_y(x) + sag * (1 - ((x - CX) / HW) ** 2)) for x in PEG_X]

def add_ball(x, y, k, vx=0.0, vy=0.0):
    global p, v, tier, born
    p = np.vstack([p, [x, y]]); v = np.vstack([v, [vx, vy]])
    tier = np.concatenate([tier, [k]]); born = np.concatenate([born, [t + 1e-4 * len(born)]])

def remove(idx):
    global p, v, tier, born
    keep = np.ones(len(p), bool); keep[list(idx)] = False
    p, v, tier, born = p[keep], v[keep], tier[keep], born[keep]

def do_snap():
    """the sieve gives way under the top pile: pegs fall, the pile crashes down."""
    global snap_t
    snap_t = t
    for (x, y) in peg_pos():
        frags.append(["peg", x, y, (x - CX) / HW * rng.uniform(40, 140), rng.uniform(80, 260), 0.0, 0.0])
        for _ in range(8):
            sparks.append([x, y, rng.uniform(10, 24), t, (1, 1, 1)])
    top_idx = p[:, 1] < sieve_y(p[:, 0]) + 20
    v[top_idx, 1] += 160
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    song.sfx(t + 0.03, "whoosh", 0.0, 0.8)
    events.append((t, "snap", 0))

def do_floor():
    """the floor breaks under the impact: everything falls out downward."""
    global floor_t, v
    floor_t = t
    lat = (p[:, 0] - CX) / HW
    depth = np.clip((p[:, 1] - YTOP) / (YB + RB - YTOP), 0, 1)
    v = np.stack([lat * rng.uniform(40, 180, len(p)), 140 + 380 * depth + rng.uniform(0, 80, len(p))], 1)
    nseg = 14
    for j in range(nseg):          # round floor: blown down and out
        a0, a1 = math.pi * j / nseg, math.pi * (j + 1) / nseg
        x0, y0 = CX + RB * math.cos(a0), YB + RB * math.sin(a0)
        x1, y1 = CX + RB * math.cos(a1), YB + RB * math.sin(a1)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        frags.append(["seg", mx, my, (mx - CX) / HW * rng.uniform(120, 300), rng.uniform(380, 640),
                      [(x0 - mx, y0 - my), (x1 - mx, y1 - my)], rng.uniform(-3, 3)])
    for xw in (XL, XR):            # side walls lose support and fall
        nseg = 6
        for j in range(nseg):
            y0 = YTOP + (YB - YTOP) * j / nseg; y1 = YTOP + (YB - YTOP) * (j + 1) / nseg
            my = (y0 + y1) / 2
            frags.append(["seg", xw, my, (xw - CX) / HW * rng.uniform(30, 110), rng.uniform(-40, 80),
                          [(0, y0 - my), (0, y1 - my)], rng.uniform(-2, 2)])
    for _ in range(70):
        a = rng.uniform(0, math.pi)
        sparks.append([CX + RB * math.cos(a), YB + RB * math.sin(a), rng.uniform(10, 26), t, (1, 1, 1)])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    song.sfx(t + 0.02, "thump", 0.0, 1.0)
    events.append((t, "floor", 0))

def wall_hit(i, vn, x, y):
    key = int(born[i] * 1e4)
    if vn > 170 and t - hit_cool.get(key, -9) > 0.12:
        hit_cool[key] = t
        song.note(t, float((x - CX) / HW), vel=min(1.0, 0.45 + vn / 900))
        events.append((t, "hit", (float(x), float(y), int(tier[i]))))

def physics_step(dt):
    global p, v, merges, fill_top, fill_bot, heat, fheat, sag, snap_pending, floor_pending, top, passes
    n = len(p)
    if n == 0:
        return
    v[:, 1] += G * dt
    v *= 0.9995
    yprev = p[:, 1].copy()
    p += v * dt
    if floor_t is not None:
        return
    r = rad()
    m = r ** 2
    for _ in range(2):
        d = p[None, :, :] - p[:, None, :]
        dd = np.hypot(d[..., 0], d[..., 1])
        rr = r[None, :] + r[:, None]
        ii, jj = np.where(np.triu(dd < rr, 1))
        if len(ii) == 0:
            break
        dist = dd[ii, jj] + 1e-6
        nrm = (p[jj] - p[ii]) / dist[:, None]
        over = rr[ii, jj] - dist
        wi = m[jj] / (m[ii] + m[jj]); wj = 1 - wi
        np.add.at(p, ii, -nrm * (over * wi)[:, None] * 0.8)
        np.add.at(p, jj, nrm * (over * wj)[:, None] * 0.8)
        rel = np.sum((v[jj] - v[ii]) * nrm, axis=1)
        app = rel < 0
        jimp = (1.25 * rel[app] / (1 / m[ii[app]] + 1 / m[jj[app]]))[:, None] * nrm[app]
        np.add.at(v, ii[app], jimp / m[ii[app], None])
        np.add.at(v, jj[app], -jimp / m[jj[app], None])
    # side walls + ceiling
    for side, xw in ((-1, XL), (1, XR)):
        over = (p[:, 0] + r - xw) if side > 0 else (xw - (p[:, 0] - r))
        idx = np.where((over > 0) & (p[:, 1] < YB))[0]
        for i in idx:
            p[i, 0] -= side * over[i]
            vn = v[i, 0] * side
            if vn > 0:
                wall_hit(i, vn, xw, p[i, 1])
                v[i, 0] = -side * vn * (0.45 if vn > 140 else 0.0)
                v[i, 1] *= 0.97
    idx = np.where(p[:, 1] - r < YTOP)[0]
    for i in idx:
        p[i, 1] = YTOP + r[i]
        if v[i, 1] < 0: v[i, 1] *= -0.3
    # round floor
    dx = p[:, 0] - CX; dy = p[:, 1] - YB
    dc = np.hypot(dx, dy) + 1e-9
    idx = np.where((dy > 0) & (dc + r > RB))[0]
    for i in idx:
        u = np.array([dx[i], dy[i]]) / dc[i]
        p[i] -= (dc[i] + r[i] - RB) * u
        vn = v[i] @ u
        if vn > 0:
            wall_hit(i, vn, CX + u[0] * RB, YB + u[1] * RB)
            vt = v[i] - vn * u
            v[i] = vt * 0.97 - (0.45 if vn > 140 else 0.0) * vn * u
    # sieve pegs (static discs, sagging with the load)
    if snap_t is None:
        for (px, py) in peg_pos():
            dx = p[:, 0] - px; dy = p[:, 1] - py
            dc = np.hypot(dx, dy) + 1e-9
            idx = np.where(dc < r + PEG_R)[0]
            for i in idx:
                u = np.array([dx[i], dy[i]]) / dc[i]
                p[i] += (r[i] + PEG_R - dc[i]) * u
                vn = -(v[i] @ u)
                if vn > 0:
                    wall_hit(i, vn, px + u[0] * PEG_R, py + u[1] * PEG_R)
                    v[i] += (1 + (0.45 if vn > 140 else 0.0)) * vn * u
                    v[i] *= 0.98
        # count balls that slip through
        sy = sieve_y(p[:, 0])
        passes += int(np.sum((yprev < sy) & (p[:, 1] >= sy)))
    # merges: same tier touching
    d = p[None, :, :] - p[:, None, :]
    dd = np.hypot(d[..., 0], d[..., 1])
    rr = r[None, :] + r[:, None]
    same = tier[None, :] == tier[:, None]
    ii, jj = np.where(np.triu((dd < rr + 1.0) & same & (tier[:, None] < TIERS - 1), 1))
    used, new = set(), []
    for i, j in zip(ii, jj):
        if i in used or j in used:
            continue
        used.update((i, j))
        new.append(((p[i] + p[j]) / 2, (v[i] + v[j]) / 2 + np.array([0, -80.0]), tier[i] + 1))
    if new:
        remove(used)
        for cpos, cvel, k in new:
            # keep the merged ball on the side of the sieve where it formed (no tunnelling through pegs)
            if snap_t is None:
                rk = RADII[k]
                sy = sieve_y(cpos[0])
                if cpos[1] < sy and cpos[1] > sy - rk - PEG_R and k >= BLOCK:
                    cpos = np.array([cpos[0], sy - rk - PEG_R - 0.5])
            add_ball(cpos[0], cpos[1], k, cvel[0], cvel[1])
            merges += 1
            pan = float((cpos[0] - CX) / HW)
            song.sfx(t, "pop", pan, 0.45 + 0.06 * k)
            for _ in range(5 + k):
                sparks.append([cpos[0], cpos[1], rng.uniform(6, 12 + 2 * k), t, LADDER[k]])
            events.append((t, "merge", (cpos[0], cpos[1], k)))
            if k > top:
                top = k
                if k >= 3:
                    song.sfx(t + 0.03, "chime", pan, 0.45 + 0.07 * k)
                    events.append((t, "newtier", (k,)))
    r = rad()
    a = np.pi * r ** 2
    up = p[:, 1] < sieve_y(p[:, 0])
    fill_top = float(np.sum(a[up]) / TOP_AREA)
    fill_bot = float(np.sum(a[~up]) / BOT_AREA)
    if snap_t is None:
        heat = float(np.clip((fill_top - (FILL_END - 0.2)) / 0.2, 0, 1))
        sag = 22 * min(1.0, fill_top / FILL_END) ** 2
        if fill_top >= FILL_END and snap_pending is None:
            snap_pending = song.next_bar(t)
            events.append((t, "full", 0))
    else:
        fheat = min(1.0, fheat + dt / 1.2)

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SPR = [neon.BallSprites([LADDER[k]], RADII[k], glow=2.4 if k < 4 else 1.7, glow_alpha=0.5) for k in range(TIERS)]

def stroke_capsule(col, fh):
    """neon tube: ceiling-less capsule, the floor arc heats separately."""
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for part in ("walls", "floor"):
        h = 0.0 if part == "walls" else fh
        cc = neon.mix(col, (1.0, 0.22, 0.25), h)
        pulse = 1 + 0.35 * h * math.sin(t * 18)
        for w_, a_ in ((34, 0.05), (18, 0.12), (8, 0.35), (3.2, 0.95)):
            ctx.new_path()
            if part == "walls":
                ctx.move_to(XL, YTOP + 30); ctx.line_to(XL, YB)
                ctx.move_to(XR, YTOP + 30); ctx.line_to(XR, YB)
            else:
                ctx.arc(CX, YB, RB, 0.0, math.pi)
            c2 = neon.mix(cc, (1, 1, 1), 0.65) if w_ < 4 else cc
            ctx.set_source_rgba(*c2, min(1.0, a_ * pulse)); ctx.set_line_width(w_)
            ctx.stroke()
    ctx.restore()

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gcol = LADDER[max(0, top)] if top >= 0 else LADDER[0]
    gcol = neon.mix(gcol, (1.0, 0.3, 0.35), max(heat, fheat))
    rg = cairo.RadialGradient(CX, YS, 0, CX, YS, 1000)
    ga = 0.04 + 0.12 * pr + 0.03 * math.sin(t * 2.0)
    if floor_t is not None:
        ga *= math.exp(-(t - floor_t) * 1.5)
    rg.add_color_stop_rgba(0, *gcol, ga); rg.add_color_stop_rgba(1, *gcol, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    shake = 0.0
    if snap_t is None and heat > 0.5:
        shake = 7 * ((heat - 0.5) / 0.5) ** 2
    if snap_t is not None and floor_t is None:
        shake = 18 * math.exp(-(t - snap_t) * 5) + 7 * fheat ** 2
    if floor_t is not None:
        shake = 26 * math.exp(-(t - floor_t) * 6)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    if floor_t is None:
        stroke_capsule(WALL_COL, fheat)
        # dropper — pulses when it drops
        ex, ey = DROP
        last = max([e[0] for e in events[-60:] if e[1] == "drop"] or [-9])
        pulse = max(0.0, 1 - (t - last) / 0.25)
        cc = (1.0, 0.9, 0.85)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        gr = cairo.RadialGradient(ex, ey, 0, ex, ey, 52)
        gr.add_color_stop_rgba(0, *cc, 0.28 + 0.5 * pulse); gr.add_color_stop_rgba(1, *cc, 0)
        ctx.set_source(gr); ctx.arc(ex, ey, 52, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgba(*cc, 0.95); ctx.set_line_width(5)
        ctx.move_to(ex - 24, ey - 16); ctx.line_to(ex - 9, ey + 6); ctx.move_to(ex + 24, ey - 16); ctx.line_to(ex + 9, ey + 6); ctx.stroke()
    # sieve pegs
    if snap_t is None:
        sc = neon.mix(SIEVE_COL, (1.0, 0.22, 0.25), heat)
        pul = 1 + 0.4 * heat * math.sin(t * 20)
        pp = peg_pos()
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        # faint guide line through the pegs so the sieve reads as one grate
        ctx.set_source_rgba(*sc, 0.10 * pul); ctx.set_line_width(2)
        ctx.move_to(XL, sieve_y(XL))
        for x, y in pp: ctx.line_to(x, y)
        ctx.line_to(XR, sieve_y(XR)); ctx.stroke()
        for x, y in pp + [(XL, sieve_y(XL)), (XR, sieve_y(XR))]:
            gr = cairo.RadialGradient(x, y, 0, x, y, 30)
            gr.add_color_stop_rgba(0, *neon.mix(sc, (1, 1, 1), 0.5), min(1.0, 0.55 * pul)); gr.add_color_stop_rgba(1, *sc, 0)
            ctx.set_source(gr); ctx.arc(x, y, 30, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        for x, y in pp:
            ctx.set_source_rgba(*neon.mix(sc, (1, 1, 1), 0.7), 1.0); ctx.arc(x, y, PEG_R - 1.5, 0, 2 * math.pi); ctx.fill()
    # flying fragments
    if frags:
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for f in frags:
            if f[0] == "peg":
                _, x, y = f[:3]
                fa = max(0.0, 1 - (t - snap_t) / 1.8)
                ctx.set_source_rgba(*neon.mix(SIEVE_COL, (1, .3, .3), 0.7), 0.9 * fa)
                ctx.arc(x, y, PEG_R, 0, 2 * math.pi); ctx.fill()
            else:
                _, fx, fy, _vx, _vy, rel, frot = f[:7]
                fa = max(0.0, 1 - (t - floor_t) / 2.2)
                ctx.save(); ctx.translate(fx, fy); ctx.rotate(f[7] if len(f) > 7 else 0.0)
                for w_, a_ in ((18, 0.15), (7, 0.9)):
                    ctx.set_source_rgba(*neon.mix(WALL_COL, (1, .2, .2), 0.7), a_ * fa); ctx.set_line_width(w_)
                    ctx.move_to(*rel[0]); ctx.line_to(*rel[1]); ctx.stroke()
                ctx.restore()
        ctx.restore()
    if snap_t is not None:
        sa = max(0.0, 0.7 - (t - snap_t) * 1.3)
        if sa > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(1, 1, 1, sa * 0.8); ctx.set_line_width(18 * sa + 2)
            ctx.move_to(XL, sieve_y(XL)); ctx.line_to(XR, sieve_y(XR)); ctx.stroke(); ctx.restore()
    if floor_t is not None:
        dt_b = t - floor_t
        sa = max(0.0, 0.7 - dt_b * 1.3)
        if sa > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(1, 1, 1, sa); ctx.set_line_width(22 * sa + 2)
            ctx.arc(CX, YB + RB, 60 + 1800 * dt_b, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    # wall hit flashes + merge rings
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, *info in events[-260:]:
        info = info[0] if info else None
        if kind == "hit" and 0 <= t - et < 0.3:
            x, y, k = info; age = (t - et) / 0.3
            ctx.set_source_rgba(*neon.mix(LADDER[k], (1, 1, 1), 0.4), 0.5 * (1 - age)); ctx.set_line_width(2.5)
            ctx.new_path(); ctx.arc(x, y, 8 + 20 * age, 0, 2 * math.pi); ctx.stroke()
        if kind == "merge" and 0 <= t - et < 0.35:
            x, y, k = info; age = (t - et) / 0.35
            ctx.set_source_rgba(*neon.mix(LADDER[k], (1, 1, 1), 0.5), 0.7 * (1 - age)); ctx.set_line_width(3 + 3 * (1 - age))
            ctx.new_path(); ctx.arc(x, y, RADII[k] * (1 + 0.6 * age), 0, 2 * math.pi); ctx.stroke()
        if kind == "newtier" and 0 <= t - et < 0.6:
            k = info[0]
            ctx.set_source_rgba(*LADDER[k], 0.06 * (1 - (t - et) / 0.6)); ctx.paint()
    ctx.restore()
    for k in range(TIERS - 1, -1, -1):
        idx = np.where(tier == k)[0]
        if len(idx) == 0: continue
        SPR[k].draw(ctx, [(p[i][0], p[i][1]) for i in idx], [0] * len(idx), glow=len(p) < 420)
    live = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = live
    groups = {}
    for x, y, sz, st, c in live:
        al = 1 - (t - st) / 0.5
        groups.setdefault((c, round(al, 1)), []).append((x, y, sz * (0.6 + al)))
    for (c, al), q in groups.items():
        neon.sparkles(ctx, q, neon.mix(c, (1, 1, 1), 0.4), alpha=al * 0.9)
    ctx.restore()
    if counter and floor_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(96)
        txt = f"{merges:,}"
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1760)
        ctx.text_path(txt)
        cc = neon.mix(neon.mix(gcol, (1, 1, 1), 0.5), (1, .3, .3), max(heat, fheat))
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(22); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.95); ctx.fill()
        ctx.restore()
    for flash_t in (snap_t, floor_t):
        if flash_t is not None:
            fa = max(0.0, (0.35 if flash_t == snap_t else 0.5) - (t - flash_t) * 2.5)
            if fa > 0:
                ctx.set_source_rgba(1, 1, 1, fa); ctx.paint()
    if floor_t is not None:
        end = floor_t + TAIL
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

# opening: a few big balls already resting at the low end of the sieve, small ones raining through
for k_, x_, dy_ in [(3, 330, -50), (3, 260, -48), (4, 300, -130), (0, -170, -200), (1, -120, -320), (0, -60, -260),
                   (1, -200, -420), (0, -140, -520), (0, -100, 140), (1, 50, 160), (0, 200, 120), (1, -40, 260),
                   (2, 120, 300), (0, -60, 380)]:
    add_ball(CX + x_, sieve_y(CX + x_) + dy_, k_, rng.uniform(-60, 60), rng.uniform(-30, 60))

dt = 1.0 / (FPS * SUB)
frame = 0
log = []
while True:
    for _ in range(SUB):
        if snap_pending is None and snap_t is None and t >= next_drop:
            big = P2 * min(1.0, 0.5 + t / 30)
            k = BLOCK if rng.random() < big else int(rng.choice(SMALL))
            add_ball(DROP[0] + rng.uniform(-3, 3), DROP[1] + 26, k, rng.uniform(-90, 90), 140)
            drops += 1
            song.sfx(t, "tick", 0.0, 0.35)
            events.append((t, "drop", 0))
            next_drop = round((t + beat_gap()) / beat_gap()) * beat_gap()
            if next_drop <= t: next_drop += beat_gap()
        physics_step(dt)
        if snap_pending is not None and snap_t is None and t >= snap_pending:
            do_snap()
            floor_pending = song.next_bar(t + 1.0)
        if floor_pending is not None and floor_t is None and t >= floor_pending:
            do_floor()
        for f in frags:
            f[4] += G * dt; f[1] += f[3] * dt; f[2] += f[4] * dt
            if f[0] == "seg":
                if len(f) < 8: f.append(0.0)
                f[7] += f[6] * dt
        t += dt
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if frame % 300 == 0:
        log.append((round(t), len(p), round(fill_top, 2), round(fill_bot, 2), top, merges))
    if PREVIEW and any(abs(t - pt) < 0.5 / FPS for pt in PREVIEW):
        draw(); surf.flush(); surf.write_to_png(f"prev_{t:05.1f}.png")
    if not SIM_ONLY:
        draw(); surf.flush()
        if first is None:
            first = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            c2 = cairo.Context(first); c2.set_source_surface(surf, 0, 0); c2.paint()
        ff.stdin.write(bytes(surf.get_data()))
    frame += 1
    if floor_t is not None and t >= floor_t + TAIL:
        break
    if t > 85:
        break

if ff:
    ff.stdin.close(); ff.wait()
print("seed", SEED, "log(t,balls,ftop,fbot,top,merges)", log)
print("tiers", [(round(e[0], 1), e[2]) for e in events if e[1] == "newtier"], "full", [round(e[0], 1) for e in events if e[1] == "full"])
print("snap", snap_t and round(snap_t, 2), "floor", floor_t and round(floor_t, 2), "duration", round(t, 2),
      "drops", drops, "merges", merges, "passes", passes, "top", top)
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
