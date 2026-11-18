"""2026-11-19 18:00 — slicer: "Blade Cut"
A glowing pendulum blade hangs from the centre of a neon ring and swings back and forth. Three visible rules:
  1. When the blade passes through a ball, the ball is CUT into two halves (each half has half the
     area, so pieces get smaller every generation; colour shows the generation).
  2. Every cut gives the pendulum more energy: it swings WIDER and FASTER (until it goes over the top and
     spins), and it gets HOTTER (white → red).
  3. Pieces at the smallest size can't be cut any more; the blade just knocks them away.
Start: 4 big balls. Cuts snowball as the blade speeds up. Each cut also heats the blade; when it is
red-hot (after HEAT_CUTS cuts) it snaps on the bar line; its pieces fly out and the shockwave blows the
crumbs outward. The tail crossfades back to the opening frame for a clean loop.

usage: python3 concepts/2026-11-19_pm_blade_cut.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 4
CX, CY, R = W / 2, 960, 470.0
PX, PY = CX, CY                     # blade pivot: centre of the ring (a real pendulum)
BL = R - 16                         # blade reaches just short of the ring
KG = (2 * math.pi / float(os.environ.get("T0", "3.4"))) ** 2   # pendulum stiffness (small-swing period T0)
AMP0 = math.radians(float(os.environ.get("AMP", "35")))        # starting swing
DOM = float(os.environ.get("DOM", "0.0105"))                    # energy kick per cut (rad/s added to the swing)
OMAX = 7.5
R0 = 128.0
GENS = int(os.environ.get("GENS", "7"))   # gen 0..GENS, the last one is the smallest (can't be cut)
RAD = [R0 / math.sqrt(2) ** g for g in range(GENS + 1)]
V_BIG = float(os.environ.get("VB", "135"))
V_SMALL = float(os.environ.get("VS", "310"))
SPEED = [V_BIG + (V_SMALL - V_BIG) * g / GENS for g in range(GENS + 1)]   # big pieces move slowly, crumbs fast
IMMUNE = 0.35
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 2
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
MUSIC_SEED = 202611195
RECENT = [dict(genre="custom", bpm=100, key="C", mode="major", lead="sine"),
          dict(genre="space", bpm=88, key="G", mode="dorian", lead="glass"),
          dict(genre="citypop", bpm=102, key="E", mode="major", lead="ep"),
          dict(genre="tropical", bpm=112, key="A", mode="major", lead="marimba")]
PAL = neon.PALETTES["synthwave"]
GEN_COLS = [(0.35, 0.45, 1.0), (0.20, 0.85, 1.0), (0.25, 1.0, 0.65), (1.0, 0.92, 0.30),
            (1.0, 0.60, 0.20), (1.0, 0.30, 0.55), (0.85, 0.40, 1.0), (0.95, 0.95, 1.0)]

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)
song = music.random_song(MUSIC_SEED, avoid=RECENT)

# ---------------- state ----------------
t = 0.0
th = 0.0
om = math.sqrt(KG) * 2 * math.sin(AMP0 / 2)   # swinging through the bottom at start
cuts = 0
heat = 0.0
p = np.array([[CX - 175.0, CY + 215.0], [CX + 150.0, CY + 250.0], [CX - 40.0, CY - 120.0], [CX + 190.0, CY - 130.0]])
ang0 = rng.uniform(0, 2 * math.pi, 4)
v = np.stack([np.cos(ang0), np.sin(ang0)], 1) * SPEED[0]
gen = np.zeros(4, int)
immune = np.zeros(4)
burst_pending = None
burst_t = None
frags, sparks, events, build_keys = [], [], [], []
blade_prev = None
total_cuts = 4 * (2 ** GENS - 1)
HEAT_CUTS = int(os.environ.get("HEAT_CUTS", "465"))   # the blade overheats and snaps after this many cuts

def blade_angle(a):
    return a                                       # 0 = straight down

def blade_dir(a):
    return np.array([math.sin(a), math.cos(a)])    # from pivot towards the tip

def progress():
    if burst_t is not None:
        return 1.0
    return min(1.0, 0.1 + 0.9 * cuts / HEAT_CUTS)

def do_burst():
    global burst_t, v
    burst_t = t
    a = blade_angle(th)
    d = blade_dir(a)
    nseg = 9
    for k in range(nseg):
        s0 = BL * (k + 0.5) / nseg
        x, y = PX + d[0] * s0, PY + d[1] * s0
        out = np.array([x - CX, y - CY]); out = out / (np.linalg.norm(out) + 1e-6)
        sp = rng.uniform(500, 1000)
        frags.append([x, y, out[0] * sp + rng.uniform(-150, 150), out[1] * sp + rng.uniform(-150, 150),
                      math.atan2(d[1], d[0]), BL / nseg * 0.85, 0.0, rng.uniform(-9, 9), t])
    dd = p - (CX, CY)
    dist = np.hypot(dd[:, 0], dd[:, 1]) + 1e-6
    v = dd / dist[:, None] * rng.uniform(450, 1000, len(p))[:, None]
    for _ in range(70):
        s0 = rng.uniform(0, BL)
        sparks.append([PX + d[0] * s0, PY + d[1] * s0, rng.uniform(10, 26), t, (1.0, 0.8, 0.5)])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    events.append((t, "burst", 0))

def split(i, d_blade, nrm):
    """cut ball i along the blade: two halves pushed to both sides of the blade"""
    global p, v, gen, immune
    g = gen[i] + 1
    r2 = RAD[g]
    base_v = v[i]
    kick = 170.0
    new_p = [p[i] + nrm * r2 * 0.95, p[i] - nrm * r2 * 0.95]
    new_v = [base_v * 0.6 + nrm * kick, base_v * 0.6 - nrm * kick]
    keep = np.ones(len(p), bool); keep[i] = False
    p = np.vstack([p[keep], new_p]); v = np.vstack([v[keep], new_v])
    gen = np.concatenate([gen[keep], [g, g]]); immune = np.concatenate([immune[keep], [IMMUNE, IMMUNE]])

def physics_step(dt):
    global p, v, th, om, cuts, heat, burst_pending, blade_prev
    if burst_t is not None:
        p += v * dt
        return
    immune[:] -= dt
    old_a = blade_angle(th)
    om += -KG * math.sin(th) * dt                  # pendulum: gravity pulls the blade back down
    th += om * dt
    a = blade_angle(th)
    d_old, d_new = blade_dir(old_a), blade_dir(a)
    p += v * dt
    r = np.array([RAD[g] for g in gen])
    m = r ** 2
    # ball-ball
    n = len(p)
    dd = p[None, :, :] - p[:, None, :]
    dist = np.hypot(dd[..., 0], dd[..., 1])
    rr = r[None, :] + r[:, None]
    ii, jj = np.where(np.triu(dist < rr, 1))
    if len(ii):
        dij = dist[ii, jj] + 1e-6
        nrm = (p[jj] - p[ii]) / dij[:, None]
        over = np.minimum(rr[ii, jj] - dij, 6.0)
        wi = m[jj] / (m[ii] + m[jj])
        np.add.at(p, ii, -nrm * (over * wi)[:, None])
        np.add.at(p, jj, nrm * (over * (1 - wi))[:, None])
        rel = np.sum((v[jj] - v[ii]) * nrm, axis=1)
        app = rel < 0
        jimp = (2 * rel[app] / (1 / m[ii[app]] + 1 / m[jj[app]]))[:, None] * nrm[app]
        np.add.at(v, ii[app], jimp / m[ii[app], None])
        np.add.at(v, jj[app], -jimp / m[jj[app], None])
    # ring wall -> notes
    d = p - (CX, CY)
    dc = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    over = dc + r - R
    for i in np.where(over > 0)[0]:
        nr = d[i] / dc[i]
        p[i] -= nr * over[i]
        vn = np.dot(v[i], nr)
        if vn > 0:
            v[i] -= 2 * vn * nr
            song.note(t, float(d[i, 0] / R))
    # blade: cut balls whose centre it sweeps across (within the blade length)
    rel_old = p - (PX, PY)
    s_new = rel_old @ d_new
    n_old = np.array([-d_old[1], d_old[0]]); n_new = np.array([-d_new[1], d_new[0]])
    side_old = (rel_old - v * dt) @ n_old
    side_new = rel_old @ n_new
    crossed = np.where((np.sign(side_old) != np.sign(side_new)) & (s_new > 0) & (s_new < BL))[0]
    to_cut = [i for i in crossed if gen[i] < GENS and immune[i] <= 0]
    # smallest pieces are knocked by the blade instead
    small = np.where((gen == GENS) & (np.abs(side_new) < r) & (s_new > 0) & (s_new < BL))[0]
    for i in small:
        sgn = 1.0 if side_new[i] >= 0 else -1.0
        p[i] += n_new * sgn * (r[i] - abs(side_new[i]))
        vn = np.dot(v[i], n_new) * sgn
        if vn < 0:
            v[i] -= 2 * vn * n_new * sgn
    for i in sorted(to_cut, reverse=True):
        x, y = p[i]
        g = gen[i]
        split(i, d_new, n_new)
        cuts += 1
        om = max(-OMAX, min(OMAX, om + (DOM if om >= 0 else -DOM)))   # every cut adds energy
        pan = float((x - CX) / R)
        song.sfx(t, "slice", pan, 0.75)
        for _ in range(6 + 2 * (GENS - g)):
            sparks.append([x + rng.uniform(-8, 8), y + rng.uniform(-8, 8), rng.uniform(6, 14), t, (1.0, 0.95, 0.8)])
        events.append((t, "cut", (x, y, g)))
    heat = min(1.0, cuts / HEAT_CUTS)
    if burst_pending is None and cuts >= HEAT_CUTS:
        burst_pending = song.next_bar(t)
        events.append((t, "done", 0))
    sp = np.array([SPEED[g] for g in gen])
    cur = np.hypot(v[:, 0], v[:, 1]) + 1e-6
    v *= (sp / cur)[:, None]

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SPR = [neon.BallSprites([GEN_COLS[g]], RAD[g], glow=2.6 if g > 2 else 1.6, glow_alpha=0.5) for g in range(GENS + 1)]
trail_angles = []

def blade_col():
    return neon.mix((0.85, 0.95, 1.0), (1.0, 0.22, 0.18), min(1.0, heat ** 0.8))

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gcol = neon.mix((0.55, 0.40, 1.0), (1.0, 0.3, 0.3), heat)
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 950)
    ga = 0.04 + 0.14 * pr + 0.03 * math.sin(t * 2.0)
    if burst_t is not None:
        ga *= math.exp(-(t - burst_t) * 1.5)
    rg.add_color_stop_rgba(0, *gcol, ga); rg.add_color_stop_rgba(1, *gcol, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    shake = 0.0
    if burst_t is None and heat > 0.75:
        shake = 7 * ((heat - 0.75) / 0.25) ** 2
    if burst_t is not None:
        shake = 26 * math.exp(-(t - burst_t) * 6)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    neon.ring(ctx, CX, CY, R + 3, PAL["ring"], t, heat=0.0)
    # balls
    for g in range(GENS + 1):
        idx = np.where(gen == g)[0]
        if len(idx):
            SPR[g].draw(ctx, [tuple(p[i]) for i in idx], [0] * len(idx), glow=len(p) < 500)
    # blade
    if burst_t is None:
        a = blade_angle(th)
        d = blade_dir(a)
        bc = blade_col()
        trail_angles.append(a)
        del trail_angles[:-7]
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for k, ta in enumerate(trail_angles[:-1]):          # motion smear
            dd = blade_dir(ta)
            al = 0.05 * (k + 1) / len(trail_angles)
            ctx.set_source_rgba(*bc, al); ctx.set_line_width(14)
            ctx.move_to(PX, PY); ctx.line_to(PX + dd[0] * BL, PY + dd[1] * BL); ctx.stroke()
        pulse = 1.0 + 0.4 * heat * (0.5 + 0.5 * math.sin(t * 30))
        nx, ny = -d[1], d[0]
        lead = 1.0 if om >= 0 else -1.0          # cutting edge faces the swing direction
        prof = [(0.03, 9), (0.18, 19), (0.55, 16), (0.85, 9), (1.0, 0)]
        edge = [(PX + d[0] * BL * f + nx * w_ * lead, PY + d[1] * BL * f + ny * w_ * lead) for f, w_ in prof]
        back = [(PX + d[0] * BL * f - nx * w_ * 0.55 * lead, PY + d[1] * BL * f - ny * w_ * 0.55 * lead) for f, w_ in prof]
        def blade_path():
            ctx.move_to(*edge[0])
            for q in edge[1:]: ctx.line_to(*q)
            for q in reversed(back): ctx.line_to(*q)
            ctx.close_path()
        for wd, al in ((44, 0.05), (26, 0.10), (12, 0.22)):
            ctx.set_source_rgba(*bc, al * pulse); ctx.set_line_width(wd); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            blade_path(); ctx.stroke()
        ctx.restore()
        gl = cairo.LinearGradient(PX - nx * 20, PY - ny * 20, PX + nx * 20, PY + ny * 20)
        gl.add_color_stop_rgba(0, *neon.mix(bc, (0, 0, 0), 0.45), 0.92)
        gl.add_color_stop_rgba(0.5, *neon.mix(bc, (1, 1, 1), 0.35), 0.95)
        gl.add_color_stop_rgba(1, *neon.mix(bc, (0, 0, 0), 0.45), 0.92)
        ctx.set_source(gl); blade_path(); ctx.fill()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_source_rgba(*neon.mix(bc, (1, 1, 1), 0.8), 0.98); ctx.set_line_width(3.2)
        ctx.move_to(*edge[0])
        for q in edge[1:]: ctx.line_to(*q)
        ctx.stroke()
        # hub
        hg = cairo.RadialGradient(PX, PY, 0, PX, PY, 34)
        hg.add_color_stop_rgba(0, 1, 1, 1, 0.9); hg.add_color_stop_rgba(0.4, *bc, 0.6); hg.add_color_stop_rgba(1, *bc, 0)
        ctx.set_source(hg); ctx.arc(PX, PY, 34, 0, 2 * math.pi); ctx.fill()
        # heat sparks dripping off the blade
        if heat > 0.5 and fx_rng.random() < (heat - 0.5) * 1.6:
            s0 = fx_rng.uniform(0.3, 1.0) * BL
            sparks.append([PX + d[0] * s0, PY + d[1] * s0, fx_rng.uniform(5, 10), t, (1.0, 0.55, 0.3)])
    else:
        dt_b = t - burst_t
        sa = max(0.0, 0.75 - dt_b * 1.3)
        if sa > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(1.0, 0.75, 0.5, sa); ctx.set_line_width(20 * sa + 2)
            ctx.arc(CX, CY, 40 + 2200 * dt_b, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for fx, fy, _vx, _vy, ang, ln, frot, _vr, ft0 in frags:
            fa = max(0.0, 1 - (t - ft0) / 2.0)
            ctx.save(); ctx.translate(fx, fy); ctx.rotate(ang + frot)
            for wd, al in ((16, 0.2), (5, 0.95)):
                ctx.set_source_rgba(1.0, 0.35, 0.25, al * fa); ctx.set_line_width(wd)
                ctx.move_to(-ln / 2, 0); ctx.line_to(ln / 2, 0); ctx.stroke()
            ctx.restore()
        ctx.restore()
    # cut flashes (a bright slit along the cut)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    a_now = blade_angle(th); dnow = blade_dir(a_now)
    for et, kind, info in events[-300:]:
        if kind == "cut" and 0 <= t - et < 0.25:
            x, y, g = info; al = 1 - (t - et) / 0.25
            L = RAD[g] * 1.3
            ctx.set_source_rgba(1, 1, 1, 0.8 * al); ctx.set_line_width(3)
            ctx.move_to(x - dnow[0] * L, y - dnow[1] * L); ctx.line_to(x + dnow[0] * L, y + dnow[1] * L); ctx.stroke()
    ctx.restore()
    live = [s for s in sparks if t - s[3] < 0.45]
    sparks[:] = live
    groups = {}
    for x, y, sz, st, c in live:
        al = 1 - (t - st) / 0.45
        groups.setdefault((c, round(al, 1)), []).append((x, y, sz * (0.6 + al)))
    for (c, al), q in groups.items():
        neon.sparkles(ctx, q, c, alpha=al * 0.9)
    ctx.restore()
    # live counter: number of pieces
    if counter and burst_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(110)
        txt = f"{len(p):,}"
        xb, yb, tw, th_, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1660)
        ctx.text_path(txt)
        cc = neon.mix(neon.mix(blade_col(), (1, 1, 1), 0.35), (1, .3, .3), max(0, heat - 0.6))
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
log = []
maxom_log = []
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
        log.append((round(t), len(p), cuts, round(om, 2)))
    maxom_log.append(abs(om))
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
cut_times = [e[0] for e in events if e[1] == "cut"]
first10 = [round(x, 1) for x in cut_times if x < 12]
print("seed", SEED, "log(t,pieces,cuts,w)", log)
print("cuts in first 12s", first10)
loop_t = next((i / FPS for i, x in enumerate(maxom_log) if x > 2 * math.sqrt(KG)), None)
print("goes over the top at", loop_t and round(loop_t, 1))
print("done", [round(e[0], 1) for e in events if e[1] == "done"], "burst", burst_t and round(burst_t, 2), "duration", round(t, 2), "pieces", len(p))
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
