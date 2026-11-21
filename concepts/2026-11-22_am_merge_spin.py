"""2026-11-22 08:00 — merge-ladder (variation): "Merge Spin"
One slowly SPINNING neon hexagon, gravity, one dropper.
  Rule 1: the dropper near the top drops a ball on every beat (1 per beat, then 2, then 4 as the song builds).
  Rule 2: two balls of the same size touching merge into the next size up (8-step colour ladder, area conserved).
The spinning walls keep tumbling the pile, so it keeps finding new pairs. It fills until it is completely,
visibly packed; then the side that is at the bottom gives way under the weight on a bar line and everything
falls out downward. Tail crossfades back to the opening frame.

usage: python3 concepts/2026-11-22_am_merge_spin.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 8
CX, CY = W / 2, 930.0
A = 405.0                        # hexagon apothem
RCIRC = A / math.cos(math.pi / 6)
OMEGA = float(os.environ.get("OMEGA", "0.22"))   # rad/s, counter-clockwise on screen
G = 1000.0
R0 = float(os.environ.get("R0", "14.0"))
TIERS = int(os.environ.get("TIERS", "9"))
RADII = [R0 * math.sqrt(2) ** k for k in range(TIERS)]
AREA = 2 * math.sqrt(3) * A ** 2
FILL_END = float(os.environ.get("FILL_END", "0.70"))
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
MUSIC_SEED = 2026112224            # random_song(seed, avoid=last 8 recipes) -> lofi / kalimba (checked vs rules)
RECENT = [dict(genre="space", bpm=88, key="G", mode="dorian", lead="glass"),
          dict(genre="citypop", bpm=102, key="E", mode="major", lead="ep"),
          dict(genre="tropical", bpm=112, key="A", mode="major", lead="marimba"),
          dict(genre="musicbox", bpm=95, key="E", mode="harmonic_minor", lead="celesta"),
          dict(genre="cinematic", bpm=78, key="A#", mode="minor", lead="harp"),
          dict(genre="waltz", bpm=93, key="D", mode="major", lead="ep"),
          dict(genre="synthwave", bpm=104, key="G#", mode="dorian", lead="saw"),
          dict(genre="gamelan", bpm=94, key="D#", mode="major", lead="bell")]
LATE = float(os.environ.get("LATE", "20"))
RATE_STEPS = [(0.0, 1), (float(os.environ.get("T2", "6")), 2), (float(os.environ.get("T3", "16")), 4)]
ROT0 = float(os.environ.get("ROT0", "0.0"))

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)
song = music.random_song(MUSIC_SEED, avoid=RECENT)

# colour ladder: violet -> blue -> cyan -> mint -> lime -> gold -> orange -> rose -> white-hot
LADDER = [(0.55, 0.30, 1.0), (0.30, 0.45, 1.0), (0.15, 0.80, 1.0), (0.20, 1.0, 0.75),
          (0.65, 1.0, 0.35), (1.0, 0.85, 0.25), (1.0, 0.55, 0.30), (1.0, 0.45, 0.65), (1.0, 0.92, 0.88)]
PAL = {"bg": ((0.02, 0.01, 0.07), (0.00, 0.00, 0.02)), "ring": (0.70, 0.75, 1.0), "balls": LADDER, "accent": (1, 0.95, 0.8)}
WALL_COL = (0.62, 0.68, 1.0)

# ---------------- state ----------------
p = np.zeros((0, 2)); v = np.zeros((0, 2)); tier = np.zeros(0, int); born = np.zeros(0)
t = 0.0
next_drop = 0.25
drops = 0
merges = 0
top = -1
heat = 0.0
fill = 0.0
burst_pending = None
burst_t = None
burst_edge = 0
frags, sparks, events, build_keys = [], [], [], []
hit_cool = {}
DROP = (CX, CY - 0.70 * A)

def rot(tt):
    return ROT0 + OMEGA * tt

def normals(tt):
    """outward normals of the 6 edges (angles)."""
    r = rot(tt)
    return [r + math.pi / 6 + k * math.pi / 3 for k in range(6)]

def corners(tt):
    r = rot(tt)
    return [(CX + RCIRC * math.cos(r + k * math.pi / 3), CY + RCIRC * math.sin(r + k * math.pi / 3)) for k in range(6)]

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
    tier = np.concatenate([tier, [k]]); born = np.concatenate([born, [t + 1e-4 * len(born)]])

def remove(idx):
    global p, v, tier, born
    keep = np.ones(len(p), bool); keep[list(idx)] = False
    p, v, tier, born = p[keep], v[keep], tier[keep], born[keep]

def do_burst():
    """The hexagon gives way under the weight: the edge at the bottom breaks first and everything falls down."""
    global burst_t, v, burst_edge
    burst_t = t
    cs = corners(t)
    mids = [((cs[k][1] + cs[(k + 1) % 6][1]) / 2) for k in range(6)]
    burst_edge = int(np.argmax(mids))
    lat = (p[:, 0] - CX) / A
    depth = np.clip((p[:, 1] - (CY - A)) / (2 * A), 0, 1)
    v = np.stack([lat * rng.uniform(60, 220, len(p)), 120 + 420 * depth + rng.uniform(0, 80, len(p))], 1)
    for k in range(6):
        a, b = cs[k], cs[(k + 1) % 6]
        nseg = 5
        for j in range(nseg):
            x0 = a[0] + (b[0] - a[0]) * j / nseg; y0 = a[1] + (b[1] - a[1]) * j / nseg
            x1 = a[0] + (b[0] - a[0]) * (j + 1) / nseg; y1 = a[1] + (b[1] - a[1]) * (j + 1) / nseg
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            if k == burst_edge:          # bottom edge: blown down and out
                vx, vy = (mx - CX) / A * rng.uniform(140, 320), rng.uniform(380, 640)
            else:                        # the rest loses support and falls
                vx, vy = (mx - CX) / A * rng.uniform(30, 120), rng.uniform(-60, 60) + (my - CY) / A * 80
            frags.append([mx, my, vx, vy, [(x0 - mx, y0 - my), (x1 - mx, y1 - my)], 0.0, rng.uniform(-3, 3)])
    a, b = cs[burst_edge], cs[(burst_edge + 1) % 6]
    for _ in range(60):
        s = rng.uniform(0, 1)
        sparks.append([a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s, rng.uniform(10, 26), t, (1, 1, 1)])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    song.sfx(t + 0.02, "thump", 0.0, 1.0)
    events.append((t, "burst", 0))

def physics_step(dt):
    global p, v, merges, fill, heat, burst_pending, top
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
    # spinning hexagon walls (moving walls: reflect the RELATIVE velocity, a little friction drags the pile)
    for ang in normals(t):
        u = np.array([math.cos(ang), math.sin(ang)])
        dn = (p - (CX, CY)) @ u
        over = dn + r - A
        idx = np.where(over > 0)[0]
        if len(idx) == 0:
            continue
        p[idx] -= over[idx, None] * u
        q = p[idx] + r[idx, None] * u
        vw = OMEGA * np.stack([-(q[:, 1] - CY), q[:, 0] - CX], 1)
        vr = v[idx] - vw
        vn = vr @ u
        hit = vn > 0
        if not np.any(hit):
            continue
        hi = idx[hit]; vnh = vn[hit]; vrh = vr[hit]
        e = np.where(vnh > 140, 0.45, 0.0)
        vt = vrh - vnh[:, None] * u
        v[hi] = vw[hit] + vrh - (1 + e)[:, None] * vnh[:, None] * u - 0.03 * vt
        for i, vni in zip(hi, vnh):
            key = int(born[i] * 1e4)
            if vni > 170 and t - hit_cool.get(key, -9) > 0.12:
                hit_cool[key] = t
                song.note(t, float((p[i, 0] - CX) / A), vel=min(1.0, 0.5 + vni / 900))
                events.append((t, "hit", (float(p[i, 0] + u[0] * r[i]), float(p[i, 1] + u[1] * r[i]), int(tier[i]))))
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
        new.append(((p[i] + p[j]) / 2, (v[i] + v[j]) / 2 + np.array([0, -90.0]), tier[i] + 1))
    if new:
        remove(used)
        for cpos, cvel, k in new:
            add_ball(cpos[0], cpos[1], k, cvel[0], cvel[1])
            merges += 1
            pan = float((cpos[0] - CX) / A)
            song.sfx(t, "pop", pan, 0.5 + 0.06 * k)
            for _ in range(5 + k):
                sparks.append([cpos[0], cpos[1], rng.uniform(6, 12 + 2 * k), t, LADDER[k]])
            events.append((t, "merge", (cpos[0], cpos[1], k)))
            if k > top:
                top = k
                if k >= 3:
                    song.sfx(t + 0.03, "chime", pan, 0.45 + 0.07 * k)
                    events.append((t, "newtier", (k,)))
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
SPR = [neon.BallSprites([LADDER[k]], RADII[k], glow=2.4 if k < 4 else 1.7, glow_alpha=0.5) for k in range(TIERS)]

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gcol = LADDER[max(0, top)] if top >= 0 else LADDER[0]
    gcol = neon.mix(gcol, (1.0, 0.3, 0.35), heat)
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 1000)
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
        cs = corners(t)
        # faint inner echo hexagon (shows the spin even when the pile hides the walls)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_source_rgba(*WALL_COL, 0.10); ctx.set_line_width(2)
        r2 = rot(t)
        for k in range(7):
            x, y = CX + RCIRC * 0.42 * math.cos(r2 + k * math.pi / 3), CY + RCIRC * 0.42 * math.sin(r2 + k * math.pi / 3)
            ctx.line_to(x, y) if k else ctx.move_to(x, y)
        ctx.stroke(); ctx.restore()
        neon.polygon_ring(ctx, cs, WALL_COL, heat=heat, t=t, width=6.0)
        # corner nodes
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        for x, y in cs:
            gr = cairo.RadialGradient(x, y, 0, x, y, 26)
            cc = neon.mix(WALL_COL, (1, .2, .2), heat)
            gr.add_color_stop_rgba(0, *neon.mix(cc, (1, 1, 1), 0.6), 0.8); gr.add_color_stop_rgba(1, *cc, 0)
            ctx.set_source(gr); ctx.arc(x, y, 26, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        # dropper — pulses when it drops
        ex, ey = DROP
        last = max([e[0] for e in events[-40:] if e[1] == "drop"] or [-9])
        pulse = max(0.0, 1 - (t - last) / 0.25)
        cc = (0.85, 0.85, 1.0)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        gr = cairo.RadialGradient(ex, ey, 0, ex, ey, 52)
        gr.add_color_stop_rgba(0, *cc, 0.28 + 0.5 * pulse); gr.add_color_stop_rgba(1, *cc, 0)
        ctx.set_source(gr); ctx.arc(ex, ey, 52, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgba(*cc, 0.95); ctx.set_line_width(5)
        ctx.move_to(ex - 24, ey - 16); ctx.line_to(ex - 9, ey + 6); ctx.move_to(ex + 24, ey - 16); ctx.line_to(ex + 9, ey + 6); ctx.stroke()
    else:
        dt_b = t - burst_t
        cs0 = corners(burst_t)
        a, b = cs0[burst_edge], cs0[(burst_edge + 1) % 6]
        sa = max(0.0, 0.7 - dt_b * 1.3)
        if sa > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(1, 1, 1, sa); ctx.set_line_width(22 * sa + 2)
            ctx.arc((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 60 + 1800 * dt_b, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        fa = max(0.0, 1 - dt_b / 2.2)
        for fx, fy, _vx, _vy, rel, frot, _vr in frags:
            ctx.save(); ctx.translate(fx, fy); ctx.rotate(frot)
            for w_, a_ in ((18, 0.15), (7, 0.9)):
                ctx.set_source_rgba(*neon.mix(WALL_COL, (1, .2, .2), 0.7), a_ * fa); ctx.set_line_width(w_)
                ctx.move_to(*rel[0]); ctx.line_to(*rel[1]); ctx.stroke()
            ctx.restore()
        ctx.restore()
    # wall hit flashes + merge rings
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, *info in events[-220:]:
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
        SPR[k].draw(ctx, [(p[i][0], p[i][1]) for i in idx], [0] * len(idx), glow=len(p) < 400)
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

# opening: a dozen small balls already tumbling, so the first merges happen in the first second
for k_, x_, y_ in [(0, -160, 120), (0, -120, 70), (0, 130, 100), (1, 170, 50), (1, -60, 180),
                   (1, 60, 160), (0, -20, 260), (2, 100, 280), (0, -200, 300), (2, 180, 230),
                   (1, -140, 330), (0, 20, 60)]:
    add_ball(CX + x_, CY + y_, k_, rng.uniform(-60, 60), rng.uniform(-30, 30))

dt = 1.0 / (FPS * SUB)
frame = 0
log = []
while True:
    for _ in range(SUB):
        if burst_pending is None and burst_t is None and t >= next_drop:
            k = int(rng.choice([0, 1, 2, 2])) if t > LATE else (int(rng.choice([0, 0, 1, 1])) if t > 8 else int(rng.choice([0, 0, 1])))
            add_ball(DROP[0] + rng.uniform(-3, 3), DROP[1] + 22, k, rng.uniform(-50, 50), 120)
            drops += 1
            song.sfx(t, "tick", 0.0, 0.35)
            events.append((t, "drop", 0))
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
        log.append((round(t), len(p), round(fill, 2), top, merges))
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
