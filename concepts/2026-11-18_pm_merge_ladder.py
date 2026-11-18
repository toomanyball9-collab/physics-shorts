"""2026-11-18 18:00 — merge-ladder: "Merge Ladder"
Two clear rules, both visible:
  1. A glowing dropper at the top drops a small ball on the beat (on every beat, then every half beat,
     then every quarter beat as the song builds).
  2. Two balls of the SAME size and colour that touch merge into ONE bigger ball (area is conserved),
     climbing a 9-step colour ladder.
Balls fall under gravity into a neon bowl (circle). Every first-time new size gets a chime + flash.
It ends when the bowl is completely, visibly packed: the ring heats red, shakes, and bursts on a bar line.
Tail crossfades back to the opening frame.

usage: python3 concepts/2026-11-18_pm_merge_ladder.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 8
CX, CY, R = W / 2, 990, 440.0
G = 1100.0
R0 = 15.0
TIERS = 9
RADII = [R0 * math.sqrt(2) ** k for k in range(TIERS)]
FILL_END = float(os.environ.get("FILL_END", "0.70"))
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 3
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
MUSIC_SEED = 202611203
RECENT = [dict(genre="custom", bpm=100, key="C", mode="major", lead="sine"),
          dict(genre="space", bpm=88, key="G", mode="dorian", lead="glass")]
# drop-rate schedule (seconds -> drops per beat)
LATE = float(os.environ.get("LATE", "44"))
RATE_STEPS = [(0.0, 1), (float(os.environ.get("T2", "13")), 2), (float(os.environ.get("T3", "32")), 4)]

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)
song = music.random_song(MUSIC_SEED, avoid=RECENT)
SPEC = neon.PALETTES["spectrum"]["balls"]
TIER_COLS = [SPEC[5], SPEC[4], SPEC[3], SPEC[2], SPEC[1], SPEC[0], SPEC[6], (1.0, 0.55, 0.85), (1.0, 0.95, 0.85)]
PAL = dict(neon.PALETTES["spectrum"]); PAL["bg"] = ((0.02, 0.01, 0.06), (0.00, 0.00, 0.02))

# ---------------- state ----------------
p = np.zeros((0, 2)); v = np.zeros((0, 2)); tier = np.zeros(0, int); born = np.zeros(0)
t = 0.0
next_drop = 0.35
drops = 0
merges = 0
top_tier = -1
heat = 0.0
fill = 0.0
burst_pending = None
burst_t = None
frags, sparks, events, build_keys = [], [], [], []
emitter_x = CX
hit_cool = {}

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

def add_ball(x, y, k, vx=0.0, vy=0.0):
    global p, v, tier, born
    p = np.vstack([p, [x, y]]); v = np.vstack([v, [vx, vy]])
    tier = np.concatenate([tier, [k]]); born = np.concatenate([born, [t]])

def remove(idx):
    global p, v, tier, born
    keep = np.ones(len(p), bool); keep[list(idx)] = False
    p, v, tier, born = p[keep], v[keep], tier[keep], born[keep]

CRACKS = [(0.5 * math.pi + o, L) for o, L in
          [(0.0, 1.0), (0.22, 0.8), (-0.25, 0.85), (0.45, 0.6), (-0.5, 0.65), (0.1, 0.7), (-0.12, 0.75),
           (0.7, 0.5), (-0.75, 0.5), (0.33, 0.55), (-0.38, 0.6), (0.9, 0.4), (-0.95, 0.4), (0.58, 0.45)]]

def do_burst():
    """The bowl gives way under the weight: the bottom breaks first and everything falls down."""
    global burst_t, v
    burst_t = t
    lat = (p[:, 0] - CX) / R
    depth = np.clip((p[:, 1] - (CY - R)) / (2 * R), 0, 1)            # lower balls drop first / faster
    v = np.stack([lat * rng.uniform(60, 240, len(p)), 120 + 420 * depth + rng.uniform(0, 80, len(p))], 1)
    N = 26
    for m in range(N):
        ac = 2 * math.pi * (m + 0.5) / N
        ox, oy = math.cos(ac), math.sin(ac)
        if oy > 0.25:      # bottom of the bowl: blown down and out
            vx, vy = ox * rng.uniform(140, 320), oy * rng.uniform(250, 520) + 150
        else:              # sides / top: they lose support and fall
            vx, vy = ox * rng.uniform(40, 140), rng.uniform(-60, 40)
        frags.append([CX + R * ox, CY + R * oy, vx, vy, ac, 2 * math.pi / N * 0.85, 0.0, rng.uniform(-4, 4), t])
    for _ in range(60):
        a = rng.uniform(0.15 * math.pi, 0.85 * math.pi)
        sparks.append([CX + R * math.cos(a), CY + R * math.sin(a), rng.uniform(10, 26), t, (1, 1, 1)])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    song.sfx(t + 0.02, "thump", 0.0, 1.0)
    events.append((t, "burst", 0))

def physics_step(dt):
    global p, v, merges, top_tier, fill, heat, burst_pending
    if burst_t is not None:
        v[:, 1] += G * dt          # everything keeps falling
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
    # ball-ball contacts (2 relaxation passes)
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
    # bowl
    d = p - (CX, CY)
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    over = dist + r - R
    for i in np.where(over > 0)[0]:
        nrm = d[i] / dist[i]
        p[i] -= nrm * over[i]
        vn = np.dot(v[i], nrm)
        if vn > 0:
            v[i] -= (1.45 if vn > 140 else 1.0) * vn * nrm
            v[i] *= 0.995
            if vn > 160 and t - hit_cool.get(int(born[i] * 1e4), -9) > 0.12:
                hit_cool[int(born[i] * 1e4)] = t
                song.note(t, float(d[i, 0] / R), vel=min(1.0, 0.5 + vn / 900))
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
        k = tier[i] + 1
        cpos = (p[i] + p[j]) / 2
        cvel = (v[i] + v[j]) / 2 + np.array([0, -90.0])
        new.append((cpos, cvel, k))
    if new:
        remove(used)
        for cpos, cvel, k in new:
            add_ball(cpos[0], cpos[1], k, cvel[0], cvel[1])
            merges += 1
            pan = float((cpos[0] - CX) / R)
            song.sfx(t, "pop", pan, 0.55 + 0.05 * k)
            for _ in range(5 + k):
                sparks.append([cpos[0], cpos[1], rng.uniform(6, 12 + 2 * k), t, TIER_COLS[k]])
            events.append((t, "merge", (cpos[0], cpos[1], k)))
            if k > top_tier:
                top_tier = k
                if k >= 3:
                    song.sfx(t + 0.03, "chime", pan, 0.5 + 0.06 * k)
                    events.append((t, "newtier", k))
    # fill & tension
    area = np.sum(np.pi * rad() ** 2)
    fill = area / (np.pi * R * R)
    heat = float(np.clip((fill - (FILL_END - 0.16)) / 0.16, 0, 1))
    if fill >= FILL_END and burst_pending is None:
        burst_pending = song.next_bar(t)
        events.append((t, "full", 0))

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SPR = [neon.BallSprites([TIER_COLS[k]], RADII[k], glow=2.4 if k < 5 else 1.7, glow_alpha=0.5) for k in range(TIERS)]

def emitter_y():
    return CY - R + 70

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gcol = neon.mix((0.55, 0.45, 1.0), (1.0, 0.3, 0.35), heat)
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 950)
    ga = 0.04 + 0.14 * pr + 0.03 * math.sin(t * 2.0)
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
    ring_col = neon.mix((0.75, 0.70, 1.0), TIER_COLS[max(top_tier, 0)], 0.5)
    if burst_t is None:
        neon.ring(ctx, CX, CY, R + 3, ring_col, t, heat=heat)
        if heat > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ncr = int(math.ceil(heat * len(CRACKS)))
            for j, (ang, L) in enumerate(CRACKS[:ncr]):
                grow = min(1.0, heat * len(CRACKS) - j)
                ln = 70 * L * grow * (0.6 + 0.4 * heat)
                ux, uy = math.cos(ang), math.sin(ang); px_, py_ = -uy, ux
                pts = [(R + 3, 0), (R + 3 + ln * 0.35, 7), (R + 3 + ln * 0.7, -6), (R + 3 + ln, 3)]
                ins = [(R + 3, 0), (R + 3 - ln * 0.3, -6), (R + 3 - ln * 0.55, 5)]
                for w_, a_ in ((7, 0.18), (2.2, 0.85)):
                    ctx.set_source_rgba(1.0, 0.55 + 0.3 * (1 - heat), 0.45, a_ * grow); ctx.set_line_width(w_)
                    for path in (pts, ins):
                        ctx.move_to(CX + ux * path[0][0] + px_ * path[0][1], CY + uy * path[0][0] + py_ * path[0][1])
                        for r_, o_ in path[1:]:
                            ctx.line_to(CX + ux * r_ + px_ * o_, CY + uy * r_ + py_ * o_)
                        ctx.stroke()
            ctx.restore()
        # dropper
        ex, ey = emitter_x, emitter_y()
        pulse = max(0.0, 1 - (t - (next_drop - beat_gap())) / 0.25) if drops else 0.0
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        gr = cairo.RadialGradient(ex, ey, 0, ex, ey, 46)
        gr.add_color_stop_rgba(0, 1, 1, 1, 0.35 + 0.45 * pulse); gr.add_color_stop_rgba(1, *ring_col, 0)
        ctx.set_source(gr); ctx.arc(ex, ey, 46, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgba(*neon.mix(ring_col, (1, 1, 1), 0.6), 0.9); ctx.set_line_width(5)
        ctx.move_to(ex - 26, ey - 16); ctx.line_to(ex - 10, ey + 6); ctx.move_to(ex + 26, ey - 16); ctx.line_to(ex + 10, ey + 6); ctx.stroke()
        # faint drop guide
        ctx.set_source_rgba(*ring_col, 0.08); ctx.set_line_width(2)
        ctx.move_to(ex, ey + 10); ctx.line_to(ex, CY + R * 0.4); ctx.stroke()
    else:
        dt_b = t - burst_t
        sa = max(0.0, 0.7 - dt_b * 1.3)
        if sa > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(1, 1, 1, sa); ctx.set_line_width(22 * sa + 2)
            ctx.arc(CX, CY + R, 60 + 1800 * dt_b, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for fx, fy, _vx, _vy, ac, span, frot, _vr, ft0 in frags:
            fa = max(0.0, 1 - (t - ft0) / 2.2)
            ctx.save(); ctx.translate(fx, fy); ctx.rotate(frot)
            for w_, a_ in ((18, 0.15), (7, 0.9)):
                ctx.set_source_rgba(*neon.mix(ring_col, (1, .2, .2), 0.7), a_ * fa); ctx.set_line_width(w_)
                ctx.new_path(); ctx.arc(-R * math.cos(ac), -R * math.sin(ac), R + 3, ac - span / 2, ac + span / 2); ctx.stroke()
            ctx.restore()
        ctx.restore()
    # merge rings
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, info in events:
        if kind == "merge" and 0 <= t - et < 0.35:
            x, y, k = info; age = (t - et) / 0.35
            ctx.set_source_rgba(*neon.mix(TIER_COLS[k], (1, 1, 1), 0.5), 0.7 * (1 - age)); ctx.set_line_width(3 + 3 * (1 - age))
            ctx.new_path(); ctx.arc(x, y, RADII[k] * (1 + 0.6 * age), 0, 2 * math.pi); ctx.stroke()
        if kind == "newtier" and 0 <= t - et < 0.6:
            ctx.set_source_rgba(*TIER_COLS[info], 0.06 * (1 - (t - et) / 0.6)); ctx.paint()
    ctx.restore()
    # balls (big first so small ones stay visible on top)
    order = np.argsort(-tier, kind="stable")
    for k in range(TIERS - 1, -1, -1):
        idx = [i for i in order if tier[i] == k]
        if not idx: continue
        pos = []
        for i in idx:
            grow = min(1.0, (t - born[i]) / 0.12)
            pos.append((p[i][0], p[i][1]))
        SPR[k].draw(ctx, pos, [0] * len(pos), glow=len(p) < 400)
    # sparks
    live = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = live
    groups = {}
    for x, y, sz, st, c in live:
        al = 1 - (t - st) / 0.5
        groups.setdefault((c, round(al, 1)), []).append((x, y, sz * (0.6 + al)))
    for (c, al), q in groups.items():
        neon.sparkles(ctx, q, neon.mix(c, (1, 1, 1), 0.4), alpha=al * 0.9)
    ctx.restore()
    # live counter: merges
    if counter and burst_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(110)
        txt = f"{merges:,}"
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1660)
        ctx.text_path(txt)
        cc = neon.mix(neon.mix(TIER_COLS[max(top_tier, 0)], (1, 1, 1), 0.5), (1, .3, .3), heat)
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

# start with a handful of balls already tumbling into the bowl, so the first seconds have motion + merges
for k_, x_, y_ in [(0, -150, 120), (0, -120, 70), (1, -60, 160), (1, 10, 90), (0, 60, 200), (2, 140, 140),
                   (0, 190, 60), (2, -200, 230), (1, -20, 260), (0, 110, 290), (3, -90, 330), (0, 30, 360)]:
    add_ball(CX + x_, CY + y_ - 140, k_, rng.uniform(-60, 60), rng.uniform(-30, 30))

dt = 1.0 / (FPS * SUB)
frame = 0
log = []
while True:
    for _ in range(SUB):
        emitter_x = CX + (R - 120) * 0.8 * math.sin(t * 0.9) * math.cos(t * 0.23)
        if burst_pending is None and burst_t is None and t >= next_drop:
            k = int(rng.choice([0, 1, 1, 2, 2])) if t > LATE else (int(rng.choice([0, 0, 0, 1, 1, 2])) if t > 8 else int(rng.choice([0, 0, 1])))
            add_ball(emitter_x + rng.uniform(-3, 3), emitter_y() + 20, k, rng.uniform(-40, 40), 120)
            drops += 1
            song.sfx(t, "tick", float((emitter_x - CX) / R), 0.35)
            next_drop = round((t + beat_gap()) / beat_gap()) * beat_gap()
            if next_drop <= t: next_drop += beat_gap()
        physics_step(dt)
        if burst_pending is not None and burst_t is None and t >= burst_pending:
            do_burst()
        for f in frags:
            f[3] += G * dt; f[0] += f[2] * dt; f[1] += f[3] * dt; f[6] += f[7] * dt
        t += dt
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if frame % 300 == 0:
        log.append((round(t), len(p), round(fill, 2), top_tier, merges))
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
print("burst", burst_t and round(burst_t, 2), "duration", round(t, 2), "drops", drops, "merges", merges)
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
