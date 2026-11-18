"""2026-11-19 08:00 — wall-split variation: "Kiss Spawn"
One clear, visible rule:
  When two CHARGED balls touch, a new ball pops out where they touched.
  Charged balls glow bright; right after spawning both parents go dim and slowly recharge
  (a small ring fills around them). Newborns start dim too.
Zero gravity, inside a slowly rotating neon hexagon. Wall hits play the music; spawns "pop".
The hexagon fills until it is completely packed, the walls heat red and shake, and the pressure
from inside bursts it outward on a bar line. The tail crossfades back to the opening frame.

usage: python3 concepts/2026-11-19_am_kiss_spawn.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 4
CX, CY = W / 2, 960
RH = 480.0                       # hexagon circumradius
AP = RH * math.cos(math.pi / 6)  # apothem
OMEGA = 0.10                     # hexagon rotation rad/s
R0 = 17.0
V0 = 520.0
CHG = float(os.environ.get("CHG", "4.0"))    # seconds to recharge after spawning
FILL_END = float(os.environ.get("FILL_END", "0.80"))
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
MUSIC_SEED = 20261123
RECENT = [dict(genre="custom", bpm=100, key="C", mode="major", lead="sine"),
          dict(genre="space", bpm=88, key="G", mode="dorian", lead="glass"),
          dict(genre="citypop", bpm=102, key="E", mode="major", lead="ep")]

rng = np.random.default_rng(SEED)          # physics
fx_rng = np.random.default_rng(SEED + 999)  # drawing only
song = music.random_song(MUSIC_SEED, avoid=RECENT)
PAL = dict(neon.PALETTES["sunset"])
COLS = PAL["balls"]
HEX_AREA = 3 * math.sqrt(3) / 2 * RH * RH

# ---------------- state ----------------
p = np.zeros((0, 2)); v = np.zeros((0, 2)); charge = np.zeros(0); col = np.zeros(0, int); born = np.zeros(0)
t = 0.0
spawns = 0
heat = 0.0
fill = 0.0
burst_pending = None
burst_t = None
frags, sparks, events, build_keys = [], [], [], []
wall_cool = np.zeros(0)


def add_ball(x, y, vx, vy, c, ch=0.0):
    global p, v, charge, col, born, wall_cool
    p = np.vstack([p, [x, y]]); v = np.vstack([v, [vx, vy]])
    charge = np.append(charge, ch); col = np.append(col, c); born = np.append(born, t)
    wall_cool = np.append(wall_cool, -9.0)


def angle_now():
    return OMEGA * t


def hex_pts(rr=RH, ang=None):
    a0 = angle_now() if ang is None else ang
    return [(CX + rr * math.cos(a0 + k * math.pi / 3), CY + rr * math.sin(a0 + k * math.pi / 3)) for k in range(6)]


def progress():
    if burst_t is not None:
        return 1.0
    return min(1.0, 0.2 * min(1, t / 12) + 0.8 * fill / FILL_END)


def do_burst():
    """Pressure from inside (zero gravity): the hexagon blows apart radially."""
    global burst_t, v
    burst_t = t
    d = p - (CX, CY)
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    sp = 250 + 900 * (dist / RH) + rng.uniform(0, 120, len(p))
    v = d / dist[:, None] * sp[:, None] + rng.normal(0, 40, (len(p), 2))
    a0 = angle_now()
    for k in range(6):
        for s in range(3):            # each edge breaks into 3 glowing pieces
            f0, f1 = s / 3, (s + 1) / 3
            ca, cb = a0 + k * math.pi / 3, a0 + (k + 1) * math.pi / 3
            A = np.array([CX + RH * math.cos(ca), CY + RH * math.sin(ca)])
            B = np.array([CX + RH * math.cos(cb), CY + RH * math.sin(cb)])
            P0, P1 = A + (B - A) * f0, A + (B - A) * f1
            mid = (P0 + P1) / 2
            out = (mid - (CX, CY)); out /= np.linalg.norm(out)
            vel = out * rng.uniform(500, 900) + rng.normal(0, 80, 2)
            frags.append([mid[0], mid[1], vel[0], vel[1], P0 - mid, P1 - mid, 0.0, rng.uniform(-5, 5)])
    for _ in range(80):
        a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0.85, 1.0) * AP
        sparks.append([CX + rr * math.cos(a), CY + rr * math.sin(a), rng.uniform(10, 28), t, (1, 1, 1)])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    song.sfx(t + 0.01, "pop", 0.0, 1.0)
    events.append((t, "burst", 0))


def physics_step(dt):
    global p, v, charge, spawns, fill, heat, burst_pending
    if burst_t is not None:
        p += v * dt
        v *= 0.995
        return
    n = len(p)
    p += v * dt
    charge = np.minimum(1.0, charge + dt / CHG)
    r = R0
    # ball-ball contacts
    tree = cKDTree(p)
    pairs = tree.query_pairs(2 * r, output_type="ndarray")
    if len(pairs):
        ii, jj = pairs[:, 0], pairs[:, 1]
        dvec = p[jj] - p[ii]
        dist = np.hypot(dvec[:, 0], dvec[:, 1]) + 1e-6
        nrm = dvec / dist[:, None]
        over = 2 * r - dist
        rel = np.sum((v[jj] - v[ii]) * nrm, axis=1)
        app = rel < 0
        imp = (0.985 * rel[app])[:, None] * nrm[app]
        np.add.at(v, ii[app], imp)
        np.add.at(v, jj[app], -imp)
        np.add.at(p, ii, -nrm * (over * 0.5)[:, None])
        np.add.at(p, jj, nrm * (over * 0.5)[:, None])
        # spawning: both charged, fresh contact
        if fill < FILL_END and burst_pending is None:
            ok = np.where(app & (charge[ii] >= 1.0) & (charge[jj] >= 1.0))[0]
            used = set()
            newb = []
            for q in ok:
                i, j = int(ii[q]), int(jj[q])
                if i in used or j in used:
                    continue
                used.update((i, j))
                charge[i] = 0.0; charge[j] = 0.0
                cpos = (p[i] + p[j]) / 2
                tang = np.array([-nrm[q, 1], nrm[q, 0]]) * (1 if rng.random() < 0.5 else -1)
                c = int((max(col[i], col[j]) + 1) % len(COLS))
                newb.append((cpos + tang * r * 0.6, tang * V0, c))
            for cpos, cv, c in newb:
                add_ball(cpos[0], cpos[1], cv[0], cv[1], c, 0.0)
                spawns += 1
                pan = float((cpos[0] - CX) / RH)
                song.sfx(t, "pop", pan, 0.5 if spawns > 60 else 0.7)
                for _ in range(6):
                    sparks.append([cpos[0], cpos[1], fx_rng.uniform(7, 15), t, COLS[c]])
                events.append((t, "spawn", (cpos[0], cpos[1], c)))
    # extra relaxation pass when crowded
    if fill > 0.45:
        for _ in range(2):
            tree = cKDTree(p)
            pairs = tree.query_pairs(2 * r, output_type="ndarray")
            if not len(pairs): break
            ii, jj = pairs[:, 0], pairs[:, 1]
            dvec = p[jj] - p[ii]
            dist = np.hypot(dvec[:, 0], dvec[:, 1]) + 1e-6
            nrm = dvec / dist[:, None]; over = 2 * r - dist
            np.add.at(p, ii, -nrm * (over * 0.5)[:, None]); np.add.at(p, jj, nrm * (over * 0.5)[:, None])
    # keep the gas lively (soft speed normalisation while not crowded)
    sp = np.hypot(v[:, 0], v[:, 1]) + 1e-6
    k = max(0.0, 1 - fill / 0.7)
    new_sp = sp + (V0 - sp) * min(1.0, k * 2.0 * dt)
    new_sp = np.minimum(new_sp, 1.5 * V0)
    v *= (new_sp / sp)[:, None]
    # hexagon walls (rotating)
    a0 = angle_now()
    d = p - (CX, CY)
    for e in range(6):
        na = a0 + (e + 0.5) * math.pi / 3
        nv = np.array([math.cos(na), math.sin(na)])
        s = d @ nv
        over = s + r - AP
        hit = np.where(over > 0)[0]
        if not len(hit): continue
        p[hit] -= nv * over[hit, None]
        d[hit] -= nv * over[hit, None]
        wv = OMEGA * np.stack([-d[hit, 1], d[hit, 0]], 1)        # wall velocity at the contact
        vr = v[hit] - wv
        vn = vr @ nv
        out = vn > 0
        hh = hit[out]
        v[hh] = wv[out] + vr[out] - 2 * vn[out, None] * nv
        for i, vni in zip(hh, vn[out]):
            if vni > 150 and t - wall_cool[i] > 0.15:
                wall_cool[i] = t
                song.note(t, float(d[i, 0] / RH), vel=min(1.0, 0.45 + vni / 1000))
    fill = len(p) * math.pi * r * r / HEX_AREA
    heat = float(np.clip((fill - 0.30) / (FILL_END - 0.30), 0, 1)) ** 1.3
    if fill >= FILL_END and burst_pending is None:
        burst_pending = song.next_bar(t + 1.2)
        events.append((t, "full", 0))


# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
BRIGHT = neon.BallSprites(COLS, R0, glow=3.0, glow_alpha=0.55)
DIM = neon.BallSprites([neon.mix(c, (0.15, 0.08, 0.2), 0.55) for c in COLS], R0, glow=2.0, glow_alpha=0.25)


def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gcol = neon.mix((1.0, 0.55, 0.35), (1.0, 0.25, 0.3), heat)
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 900)
    ga = 0.04 + 0.13 * pr + 0.02 * math.sin(t * 2.2)
    if burst_t is not None:
        ga *= math.exp(-(t - burst_t) * 1.5)
    rg.add_color_stop_rgba(0, *gcol, ga); rg.add_color_stop_rgba(1, *gcol, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    shake = 0.0
    if burst_t is None and heat > 0.4:
        shake = 9 * ((heat - 0.4) / 0.6) ** 2
    if burst_t is not None:
        shake = 26 * math.exp(-(t - burst_t) * 6)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    ring_col = PAL["ring"]
    if burst_t is None:
        neon.polygon_ring(ctx, hex_pts(RH + 4), ring_col, heat=heat, t=t)
    else:
        dt_b = t - burst_t
        sa = max(0.0, 0.75 - dt_b * 1.2)
        if sa > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(1, 1, 1, sa); ctx.set_line_width(24 * sa + 2)
            ctx.arc(CX, CY, AP + 1700 * dt_b, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        fa = max(0.0, 1 - dt_b / 2.2)
        for fx, fy, _vx, _vy, a, b, rot, _vr in frags:
            ca, sa_ = math.cos(rot), math.sin(rot)
            A = (fx + a[0] * ca - a[1] * sa_, fy + a[0] * sa_ + a[1] * ca)
            B = (fx + b[0] * ca - b[1] * sa_, fy + b[0] * sa_ + b[1] * ca)
            for w_, a_ in ((20, 0.14), (7, 0.9)):
                ctx.set_source_rgba(*neon.mix(ring_col, (1, .2, .2), 0.6), a_ * fa); ctx.set_line_width(w_)
                ctx.move_to(*A); ctx.line_to(*B); ctx.stroke()
        ctx.restore()
    # spawn flashes
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, info in events[-200:]:
        if kind == "spawn" and 0 <= t - et < 0.35:
            x, y, c = info; age = (t - et) / 0.35
            ctx.set_source_rgba(*neon.mix(COLS[c], (1, 1, 1), 0.5), 0.75 * (1 - age)); ctx.set_line_width(2 + 4 * (1 - age))
            ctx.new_path(); ctx.arc(x, y, R0 * (1 + 2.2 * age), 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
    # balls: dim (recharging) and bright (charged)
    n = len(p)
    if n:
        ch = charge >= 1.0
        idx_d = np.where(~ch)[0]; idx_b = np.where(ch)[0]
        DIM.draw(ctx, [tuple(p[i]) for i in idx_d], [int(col[i]) for i in idx_d], glow=n < 450)
        BRIGHT.draw(ctx, [tuple(p[i]) for i in idx_b], [int(col[i]) for i in idx_b], glow=True)
        # recharge arcs
        if burst_t is None:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_width(2.4)
            for i in idx_d:
                c = COLS[int(col[i])]
                ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.4), 0.75)
                ctx.new_path(); ctx.arc(p[i, 0], p[i, 1], R0 + 4, -math.pi / 2, -math.pi / 2 + 2 * math.pi * charge[i]); ctx.stroke()
            ctx.restore()
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
    if counter and burst_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(110)
        txt = f"{len(p):,}"
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1660)
        ctx.text_path(txt)
        cc = neon.mix(neon.mix(PAL["accent"], (1, 1, 1), 0.3), (1, .3, .3), heat)
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


ff = None
if not SIM_ONLY:
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", OUT
    ], stdin=subprocess.PIPE)

# opening: two charged balls heading for each other (first spawn within ~1 s) + two more drifting
add_ball(CX - 300, CY - 40, V0, 40, 0, 1.0)
add_ball(CX + 300, CY + 40, -V0, -40, 1, 1.0)
for c in (2, 3, 0, 2):
    a = rng.uniform(0, 2 * math.pi)
    add_ball(CX + rng.uniform(-200, 200), CY + rng.uniform(-300, 300), V0 * math.cos(a), V0 * math.sin(a), c, 1.0)

dt = 1.0 / (FPS * SUB)
frame = 0
log = []
while True:
    for _ in range(SUB):
        physics_step(dt)
        if burst_pending is not None and burst_t is None and t >= burst_pending:
            do_burst()
        for f in frags:
            f[0] += f[2] * dt; f[1] += f[3] * dt; f[6] += f[7] * dt
        t += dt
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if frame % 300 == 0:
        log.append((round(t), len(p), round(fill, 2)))
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
print("seed", SEED, "log(t,balls,fill)", log)
print("full", [round(e[0], 2) for e in events if e[1] == "full"], "burst", burst_t and round(burst_t, 2),
      "duration", round(t, 2), "spawns", spawns)
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
