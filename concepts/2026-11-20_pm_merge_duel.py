"""2026-11-20 18:00 — merge-ladder (variation): "Merge Duel"
Two teams, one tall neon capsule, gravity.
  Rule 1: two droppers at the top take turns on the beat — the left one drops TEAL balls, the right one AMBER
          (1 drop per beat, then 2, then 4 as the waltz builds).
  Rule 2: two balls of the same team AND the same size that touch merge into the next size up (area conserved).
          Teal never merges with amber — they just push each other around.
Which team builds the biggest ball? The capsule fills until it is completely, visibly packed; the bottom
cracks under the weight and gives way on a bar line, and everything falls out downward.
Tail crossfades back to the opening frame.

usage: python3 concepts/2026-11-20_pm_merge_duel.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 8
CX = W / 2
RC = 340.0                       # capsule half-width (radius of the round ends)
Y1, Y2 = 760.0, 1200.0           # centre line of the capsule (top / bottom circle centres)
G = 1100.0
R0 = float(os.environ.get("R0", "16.0"))
TIERS = 8
RADII = [R0 * math.sqrt(2) ** k for k in range(TIERS)]
AREA = math.pi * RC ** 2 + 2 * RC * (Y2 - Y1)
FILL_END = float(os.environ.get("FILL_END", "0.72"))
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
MUSIC_SEED = 202611201
RECENT = [dict(genre="custom", bpm=100, key="C", mode="major", lead="sine"),
          dict(genre="space", bpm=88, key="G", mode="dorian", lead="glass"),
          dict(genre="citypop", bpm=102, key="E", mode="major", lead="ep"),
          dict(genre="dreamwave", bpm=94, key="A#", mode="lydian", lead="celesta"),
          dict(genre="trance_lite", bpm=119, key="D#", mode="minor", lead="saw"),
          dict(genre="tropical", bpm=112, key="A", mode="major", lead="marimba"),
          dict(genre="musicbox", bpm=95, key="E", mode="harmonic_minor", lead="celesta"),
          dict(genre="cinematic", bpm=78, key="A#", mode="minor", lead="harp")]
LATE = float(os.environ.get("LATE", "33"))
RATE_STEPS = [(0.0, 1), (float(os.environ.get("T2", "10")), 2), (float(os.environ.get("T3", "26")), 4)]

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)
song = music.random_song(MUSIC_SEED, avoid=RECENT)

def ladder(c0, c1, c2):
    out = []
    for k in range(TIERS):
        x = k / (TIERS - 1)
        out.append(neon.mix(c0, c1, x / 0.6) if x < 0.6 else neon.mix(c1, c2, (x - 0.6) / 0.4))
    return out
TEAM_COLS = [ladder((0.10, 0.45, 1.0), (0.15, 0.95, 0.95), (0.80, 1.0, 0.95)),     # teal team
             ladder((1.0, 0.35, 0.15), (1.0, 0.72, 0.20), (1.0, 0.97, 0.75))]      # amber team
PAL = dict(neon.PALETTES["aurora"]); PAL["bg"] = ((0.02, 0.02, 0.06), (0.00, 0.00, 0.02))
WALL_COL = (0.75, 0.72, 1.0)

# ---------------- state ----------------
p = np.zeros((0, 2)); v = np.zeros((0, 2)); tier = np.zeros(0, int); team = np.zeros(0, int); born = np.zeros(0)
t = 0.0
next_drop = 0.3
drops = 0
merges = 0
top = [-1, -1]
heat = 0.0
fill = 0.0
burst_pending = None
burst_t = None
frags, sparks, events, build_keys = [], [], [], []
hit_cool = {}
slot = 0
DX = [CX - 150, CX + 150]
drop_x = list(DX)

def rad():
    return np.array([RADII[k] for k in tier]) if len(tier) else np.zeros(0)

def drops_per_beat(tt):
    r = 1
    for t0, k in RATE_STEPS:
        if tt >= t0: r = k
    return r

def progress():
    if burst_t is not None:
        return 1.0
    return min(1.0, 0.25 * min(1, t / 14) + 0.75 * fill / FILL_END)

def add_ball(x, y, k, tm, vx=0.0, vy=0.0):
    global p, v, tier, team, born
    p = np.vstack([p, [x, y]]); v = np.vstack([v, [vx, vy]])
    tier = np.concatenate([tier, [k]]); team = np.concatenate([team, [tm]]); born = np.concatenate([born, [t]])

def remove(idx):
    global p, v, tier, team, born
    keep = np.ones(len(p), bool); keep[list(idx)] = False
    p, v, tier, team, born = p[keep], v[keep], tier[keep], team[keep], born[keep]

def seg_closest(pts):
    """closest points on the capsule centre line."""
    cy = np.clip(pts[:, 1], Y1, Y2)
    return np.stack([np.full(len(pts), CX), cy], 1)

def outline(n=240):
    """capsule outline as points, starting at the bottom centre, going counter-clockwise on screen."""
    pts = []
    L = 2 * (Y2 - Y1) + 2 * math.pi * RC
    for i in range(n):
        s = L * i / n
        seg = [math.pi * RC / 2, Y2 - Y1, math.pi * RC, Y2 - Y1, math.pi * RC / 2]
        if s < seg[0]:                                     # bottom right quarter
            a = math.pi / 2 - s / RC; pts.append((CX + RC * math.cos(a), Y2 + RC * math.sin(a)))
        elif s < seg[0] + seg[1]:                          # right side going up
            pts.append((CX + RC, Y2 - (s - seg[0])))
        elif s < seg[0] + seg[1] + seg[2]:                 # top arc
            a = -(s - seg[0] - seg[1]) / RC; pts.append((CX + RC * math.cos(a), Y1 + RC * math.sin(a)))
        elif s < seg[0] + 2 * seg[1] + seg[2]:             # left side going down
            pts.append((CX - RC, Y1 + (s - seg[0] - seg[1] - seg[2])))
        else:                                              # bottom left quarter
            a = math.pi - (s - seg[0] - 2 * seg[1] - seg[2]) / RC; pts.append((CX + RC * math.cos(a), Y2 + RC * math.sin(a)))
    return pts
OUTLINE = outline()

CRACKS = [(0.5 * math.pi + o, L) for o, L in
          [(0.0, 1.0), (0.22, 0.8), (-0.25, 0.85), (0.45, 0.6), (-0.5, 0.65), (0.1, 0.7), (-0.12, 0.75),
           (0.7, 0.5), (-0.75, 0.5), (0.33, 0.55), (-0.38, 0.6), (0.9, 0.4), (-0.95, 0.4), (0.58, 0.45)]]

def do_burst():
    """The capsule gives way under the weight: the bottom breaks first and everything falls down."""
    global burst_t, v
    burst_t = t
    lat = (p[:, 0] - CX) / RC
    depth = np.clip((p[:, 1] - (Y1 - RC)) / (Y2 - Y1 + 2 * RC), 0, 1)
    v = np.stack([lat * rng.uniform(60, 220, len(p)), 120 + 420 * depth + rng.uniform(0, 80, len(p))], 1)
    N = 30
    n = len(OUTLINE)
    for m in range(N):
        chunk = [OUTLINE[(m * n // N + j) % n] for j in range(n // N + 1)]
        mx = sum(q[0] for q in chunk) / len(chunk); my = sum(q[1] for q in chunk) / len(chunk)
        rel = [(q[0] - mx, q[1] - my) for q in chunk]
        if my > Y2 + RC * 0.25:      # bottom: blown down and out
            vx, vy = (mx - CX) / RC * rng.uniform(140, 320), rng.uniform(250, 520) + 150
        else:                        # sides / top lose support and fall
            vx, vy = (mx - CX) / RC * rng.uniform(30, 120), rng.uniform(-60, 40)
        frags.append([mx, my, vx, vy, rel, 0.0, rng.uniform(-3, 3)])
    for _ in range(60):
        a = rng.uniform(0.15 * math.pi, 0.85 * math.pi)
        sparks.append([CX + RC * math.cos(a), Y2 + RC * math.sin(a), rng.uniform(10, 26), t, (1, 1, 1)])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    song.sfx(t + 0.02, "thump", 0.0, 1.0)
    events.append((t, "burst", 0))

def physics_step(dt):
    global p, v, merges, fill, heat, burst_pending
    if burst_t is not None:
        v[:, 1] += G * dt
        p += v * dt
        return
    n = len(p)
    if n == 0:
        return
    v[:, 1] += G * dt
    v *= 0.9995
    p += v * dt
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
    # capsule walls
    c = seg_closest(p)
    d = p - c
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    over = dist + r - RC
    for i in np.where(over > 0)[0]:
        nrm = d[i] / dist[i]
        p[i] -= nrm * over[i]
        vn = np.dot(v[i], nrm)
        if vn > 0:
            v[i] -= (1.45 if vn > 140 else 1.0) * vn * nrm
            v[i] *= 0.995
            key = int(born[i] * 1e4)
            if vn > 160 and t - hit_cool.get(key, -9) > 0.12:
                hit_cool[key] = t
                song.note(t, float((p[i, 0] - CX) / RC), vel=min(1.0, 0.5 + vn / 900))
                events.append((t, "hit", (float(p[i, 0] + nrm[0] * r[i]), float(p[i, 1] + nrm[1] * r[i]), int(team[i]))))
    # merges: same team + same tier touching
    d = p[None, :, :] - p[:, None, :]
    dd = np.hypot(d[..., 0], d[..., 1])
    rr = r[None, :] + r[:, None]
    same = (tier[None, :] == tier[:, None]) & (team[None, :] == team[:, None])
    ii, jj = np.where(np.triu((dd < rr + 1.0) & same & (tier[:, None] < TIERS - 1), 1))
    used, new = set(), []
    for i, j in zip(ii, jj):
        if i in used or j in used:
            continue
        used.update((i, j))
        new.append(((p[i] + p[j]) / 2, (v[i] + v[j]) / 2 + np.array([0, -90.0]), tier[i] + 1, team[i]))
    if new:
        remove(used)
        for cpos, cvel, k, tm in new:
            add_ball(cpos[0], cpos[1], k, tm, cvel[0], cvel[1])
            merges += 1
            pan = float((cpos[0] - CX) / RC)
            song.sfx(t, "pop", pan, 0.5 + 0.06 * k)
            for _ in range(5 + k):
                sparks.append([cpos[0], cpos[1], rng.uniform(6, 12 + 2 * k), t, TEAM_COLS[tm][k]])
            events.append((t, "merge", (cpos[0], cpos[1], k, tm)))
            if k > top[tm]:
                top[tm] = k
                if k >= 3:
                    song.sfx(t + 0.03, "chime", pan, 0.45 + 0.07 * k)
                    events.append((t, "newtier", (k, tm)))
    area = np.sum(np.pi * rad() ** 2)
    fill = area / AREA
    heat = float(np.clip((fill - (FILL_END - 0.16)) / 0.16, 0, 1))
    if fill >= FILL_END and burst_pending is None:
        burst_pending = song.next_bar(t)
        events.append((t, "full", 0))

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SPR = [[neon.BallSprites([TEAM_COLS[tm][k]], RADII[k], glow=2.4 if k < 4 else 1.7, glow_alpha=0.5) for k in range(TIERS)] for tm in (0, 1)]
DROP_Y = Y1 - RC + 80

def lead_team():
    if top[0] == top[1]:
        return None
    return 0 if top[0] > top[1] else 1

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    lt = lead_team()
    gcol = (0.55, 0.5, 1.0) if lt is None else TEAM_COLS[lt][4]
    gcol = neon.mix(gcol, (1.0, 0.3, 0.35), heat)
    rg = cairo.RadialGradient(CX, (Y1 + Y2) / 2, 0, CX, (Y1 + Y2) / 2, 1000)
    ga = 0.04 + 0.12 * pr + 0.03 * math.sin(t * 2.0)
    if burst_t is not None:
        ga *= math.exp(-(t - burst_t) * 1.5)
    rg.add_color_stop_rgba(0, *gcol, ga); rg.add_color_stop_rgba(1, *gcol, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    shake = 0.0
    if burst_t is None and heat > 0.5:
        shake = 8 * ((heat - 0.5) / 0.5) ** 2
    if burst_t is not None:
        shake = 26 * math.exp(-(t - burst_t) * 6)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    if burst_t is None:
        neon.polygon_ring(ctx, [(x, y) for x, y in OUTLINE], WALL_COL, heat=heat, t=t)
        if heat > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ncr = int(math.ceil(heat * len(CRACKS)))
            for j, (ang, L) in enumerate(CRACKS[:ncr]):
                grow = min(1.0, heat * len(CRACKS) - j)
                ln = 70 * L * grow * (0.6 + 0.4 * heat)
                ux, uy = math.cos(ang), math.sin(ang); px_, py_ = -uy, ux
                pts = [(RC, 0), (RC + ln * 0.35, 7), (RC + ln * 0.7, -6), (RC + ln, 3)]
                ins = [(RC, 0), (RC - ln * 0.3, -6), (RC - ln * 0.55, 5)]
                for w_, a_ in ((7, 0.18), (2.2, 0.85)):
                    ctx.set_source_rgba(1.0, 0.55 + 0.3 * (1 - heat), 0.45, a_ * grow); ctx.set_line_width(w_)
                    for path in (pts, ins):
                        ctx.move_to(CX + ux * path[0][0] + px_ * path[0][1], Y2 + uy * path[0][0] + py_ * path[0][1])
                        for r_, o_ in path[1:]:
                            ctx.line_to(CX + ux * r_ + px_ * o_, Y2 + uy * r_ + py_ * o_)
                        ctx.stroke()
            ctx.restore()
        # droppers (teal left, amber right) — the one that just dropped pulses
        for tm in (0, 1):
            ex, ey = drop_x[tm], DROP_Y
            last = max([e[0] for e in events[-30:] if e[1] == "drop" and e[2] == tm] or [-9])
            pulse = max(0.0, 1 - (t - last) / 0.25)
            cc = TEAM_COLS[tm][3]
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            gr = cairo.RadialGradient(ex, ey, 0, ex, ey, 50)
            gr.add_color_stop_rgba(0, *neon.mix(cc, (1, 1, 1), 0.5), 0.30 + 0.5 * pulse); gr.add_color_stop_rgba(1, *cc, 0)
            ctx.set_source(gr); ctx.arc(ex, ey, 50, 0, 2 * math.pi); ctx.fill()
            ctx.restore()
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_source_rgba(*neon.mix(cc, (1, 1, 1), 0.55), 0.95); ctx.set_line_width(5)
            ctx.move_to(ex - 24, ey - 16); ctx.line_to(ex - 9, ey + 6); ctx.move_to(ex + 24, ey - 16); ctx.line_to(ex + 9, ey + 6); ctx.stroke()
    else:
        dt_b = t - burst_t
        sa = max(0.0, 0.7 - dt_b * 1.3)
        if sa > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(1, 1, 1, sa); ctx.set_line_width(22 * sa + 2)
            ctx.arc(CX, Y2 + RC, 60 + 1800 * dt_b, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        fa = max(0.0, 1 - dt_b / 2.2)
        for fx, fy, _vx, _vy, rel, frot, _vr in frags:
            ctx.save(); ctx.translate(fx, fy); ctx.rotate(frot)
            for w_, a_ in ((18, 0.15), (7, 0.9)):
                ctx.set_source_rgba(*neon.mix(WALL_COL, (1, .2, .2), 0.7), a_ * fa); ctx.set_line_width(w_)
                ctx.move_to(*rel[0])
                for q in rel[1:]: ctx.line_to(*q)
                ctx.stroke()
            ctx.restore()
        ctx.restore()
    # wall hit flashes + merge rings
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, *info in events[-220:]:
        info = info[0] if info else None
        if kind == "hit" and 0 <= t - et < 0.3:
            x, y, tm = info; age = (t - et) / 0.3
            ctx.set_source_rgba(*neon.mix(TEAM_COLS[tm][3], (1, 1, 1), 0.4), 0.5 * (1 - age)); ctx.set_line_width(2.5)
            ctx.new_path(); ctx.arc(x, y, 8 + 20 * age, 0, 2 * math.pi); ctx.stroke()
        if kind == "merge" and 0 <= t - et < 0.35:
            x, y, k, tm = info; age = (t - et) / 0.35
            ctx.set_source_rgba(*neon.mix(TEAM_COLS[tm][k], (1, 1, 1), 0.5), 0.7 * (1 - age)); ctx.set_line_width(3 + 3 * (1 - age))
            ctx.new_path(); ctx.arc(x, y, RADII[k] * (1 + 0.6 * age), 0, 2 * math.pi); ctx.stroke()
        if kind == "newtier" and 0 <= t - et < 0.6:
            k, tm = info
            ctx.set_source_rgba(*TEAM_COLS[tm][k], 0.06 * (1 - (t - et) / 0.6)); ctx.paint()
    ctx.restore()
    # balls, big first
    for k in range(TIERS - 1, -1, -1):
        for tm in (0, 1):
            idx = np.where((tier == k) & (team == tm))[0]
            if len(idx) == 0: continue
            SPR[tm][k].draw(ctx, [(p[i][0], p[i][1]) for i in idx], [0] * len(idx), glow=len(p) < 400)
    live = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = live
    groups = {}
    for x, y, sz, st, c in live:
        al = 1 - (t - st) / 0.5
        groups.setdefault((c, round(al, 1)), []).append((x, y, sz * (0.6 + al)))
    for (c, al), q in groups.items():
        neon.sparkles(ctx, q, neon.mix(c, (1, 1, 1), 0.4), alpha=al * 0.9)
    ctx.restore()
    if counter and burst_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(100)
        txt = f"{merges:,}"
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1715)
        ctx.text_path(txt)
        cc = neon.mix(neon.mix(gcol, (1, 1, 1), 0.5), (1, .3, .3), heat)
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

def beat_gap():
    return song.beat / drops_per_beat(t)

ff = None
if not SIM_ONLY:
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", OUT
    ], stdin=subprocess.PIPE)

# opening: a dozen balls of both teams already tumbling down, so merges start in the first seconds
for tm_, k_, x_, y_ in [(0, 0, -160, 0), (0, 0, -120, -50), (1, 0, 130, -20), (1, 0, 170, -70), (0, 1, -60, 60),
                        (1, 1, 60, 40), (0, 1, -20, 140), (1, 1, 100, 160), (0, 0, -200, 180), (1, 2, 180, 230),
                        (0, 2, -140, 260), (1, 0, 20, 300)]:
    add_ball(CX + x_, Y1 + y_, k_, tm_, rng.uniform(-60, 60), rng.uniform(-30, 30))

dt = 1.0 / (FPS * SUB)
frame = 0
log = []
while True:
    for _ in range(SUB):
        drop_x[0] = DX[0] + 70 * math.sin(t * 0.8)
        drop_x[1] = DX[1] + 70 * math.sin(t * 0.8 + 2.1)
        if burst_pending is None and burst_t is None and t >= next_drop:
            tm = slot % 2
            k = int(rng.choice([0, 1, 1, 2])) if t > LATE else (int(rng.choice([0, 0, 1, 1])) if t > 8 else int(rng.choice([0, 0, 1])))
            add_ball(drop_x[tm] + rng.uniform(-3, 3), DROP_Y + 20, k, tm, rng.uniform(-40, 40), 120)
            drops += 1; slot += 1
            song.sfx(t, "tick", -0.4 if tm == 0 else 0.4, 0.35)
            events.append((t, "drop", tm))
            next_drop = round((t + beat_gap()) / beat_gap()) * beat_gap()
            if next_drop <= t: next_drop += beat_gap()
        physics_step(dt)
        if burst_pending is not None and burst_t is None and t >= burst_pending:
            do_burst()
        for f in frags:
            f[3] += G * dt; f[0] += f[2] * dt; f[1] += f[3] * dt; f[5] += f[6] * dt
        t += dt
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if frame % 300 == 0:
        log.append((round(t), len(p), round(fill, 2), tuple(top), merges))
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
print("seed", SEED, "log(t,balls,fill,top,merges)", log)
print("tiers", [(round(e[0], 1), e[2]) for e in events if e[1] == "newtier"], "full", [round(e[0], 1) for e in events if e[1] == "full"])
print("burst", burst_t and round(burst_t, 2), "duration", round(t, 2), "drops", drops, "merges", merges, "top", top)
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
