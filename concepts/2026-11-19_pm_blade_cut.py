"""2026-11-19 18:00 — slicer: "Blade Cut" (v3)
A neon laser blade spins in the middle of the ring (inspired by the viral "spinning paddle doubles every
ball it touches" format). Visible rules:
  1. When the blade passes through a ball, the ball is CUT in half: the two half-discs fly apart and
     become two smaller balls (half the area each). Size + shade show how many times it was cut.
  2. Every cut makes the blade spin FASTER and glow hotter (pink → red).
  3. The smallest pieces are too small to cut — the laser passes right through them.
Start: ONE big ball. The outer ring zone is out of the blade's reach. When every piece has been cut down to the smallest size, the red-hot blade
snaps on the bar line and the pieces scatter. Tail crossfades back to the opening frame.

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
PX, PY = CX, CY                      # blade spins around the centre of the ring
BL = float(os.environ.get("BLF", "0.68")) * R    # half-length of the spinning blade (outer ring zone is safe)
OM0 = float(os.environ.get("OM0", "1.0"))         # spin speed at start (rad/s)
DOM = float(os.environ.get("DOM", "0.0008"))         # every cut makes it spin faster
OMAX = 6.5
GENS = int(os.environ.get("GENS", "8"))
R0 = float(os.environ.get("R0", "165"))
RAD = [R0 / math.sqrt(2) ** g for g in range(GENS + 1)]
VB = float(os.environ.get("VB", "34")); VS = float(os.environ.get("VS", "85"))
SPEED = [VB + (VS - VB) * g / GENS for g in range(GENS + 1)]
IMMUNE = 0.45
SPLIT_ANIM = 0.16
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
MUSIC_SEED = 202611195
RECENT = [dict(genre="custom", bpm=100, key="C", mode="major", lead="sine"),
          dict(genre="space", bpm=88, key="G", mode="dorian", lead="glass"),
          dict(genre="citypop", bpm=102, key="E", mode="major", lead="ep"),
          dict(genre="tropical", bpm=112, key="A", mode="major", lead="marimba")]
PAL = neon.PALETTES["ocean"]
# one colour family: deep blue (big) -> cyan -> pale mint (smallest)
GEN_COLS = [(0.36, 0.30, 1.0), (0.30, 0.42, 1.0), (0.25, 0.55, 1.0), (0.20, 0.68, 1.0), (0.18, 0.80, 1.0), (0.20, 0.90, 0.98), (0.25, 0.98, 0.90), (0.35, 1.0, 0.80), (0.50, 1.0, 0.72)]
BLADE_COOL, BLADE_HOT = (1.0, 0.35, 0.80), (1.0, 0.22, 0.12)

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)
song = music.random_song(MUSIC_SEED, avoid=RECENT)

# ---------------- state ----------------
t = 0.0
om = OM0
cuts = 0
total_cuts = 2 ** GENS - 1
HEAT_CUTS = int(os.environ.get("HEAT_CUTS", "215"))   # red-hot after this many cuts -> snaps
heat = 0.0
p = np.array([[CX + 120.0, CY - 60.0]])                  # ONE big ball, right next to the blade
v = np.array([[-0.8, 0.6]]) * SPEED[0]
th = math.atan2(120.0, -60.0) - 0.33                       # the blade reaches it ~0.4 s in
gen = np.zeros(1, int)
immune = np.zeros(1)
born = np.full(1, -9.0)
burst_pending = None
burst_t = None
frags, sparks, events, build_keys, splits = [], [], [], [], []

def blade_dir(a):
    return np.array([math.sin(a), math.cos(a)])

def progress():
    if burst_t is not None:
        return 1.0
    return min(1.0, 0.08 + 0.92 * cuts / HEAT_CUTS)

def do_burst():
    global burst_t, v
    burst_t = t
    d = blade_dir(th)
    nseg = 10
    for k in range(nseg):
        s0 = -BL + 2 * BL * (k + 0.5) / nseg
        x, y = PX + d[0] * s0, PY + d[1] * s0
        out = np.array([x - CX, y - CY]); out = out / (np.linalg.norm(out) + 1e-6)
        sp = rng.uniform(450, 950)
        frags.append([x, y, out[0] * sp + rng.uniform(-120, 120), out[1] * sp + rng.uniform(-120, 120),
                      math.atan2(d[1], d[0]), 2 * BL / nseg * 0.85, 0.0, rng.uniform(-8, 8), t])
    dd = p - (CX, CY)
    dist = np.hypot(dd[:, 0], dd[:, 1]) + 1e-6
    v = dd / dist[:, None] * rng.uniform(450, 950, len(p))[:, None]
    for _ in range(60):
        s0 = rng.uniform(0, BL)
        sparks.append([PX + d[0] * s0, PY + d[1] * s0, rng.uniform(10, 24), t, (1.0, 0.7, 0.5)])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    events.append((t, "burst", 0))

def split(i, nrm, ang):
    global p, v, gen, immune, born
    g = gen[i] + 1
    r2 = RAD[g]
    kick = float(os.environ.get("KICK", "90"))
    new_p = [p[i] + nrm * r2 * 0.75, p[i] - nrm * r2 * 0.75]
    new_v = [v[i] * 0.5 + nrm * kick, v[i] * 0.5 - nrm * kick]
    splits.append((t, p[i].copy(), RAD[g - 1], ang, gen[i], nrm.copy()))
    keep = np.ones(len(p), bool); keep[i] = False
    p = np.vstack([p[keep], new_p]); v = np.vstack([v[keep], new_v])
    gen = np.concatenate([gen[keep], [g, g]]); immune = np.concatenate([immune[keep], [IMMUNE, IMMUNE]])
    born = np.concatenate([born[keep], [t, t]])

def physics_step(dt):
    global p, v, th, om, cuts, heat, burst_pending
    if burst_t is not None:
        p += v * dt
        return
    immune[:] -= dt
    old = th
    th += om * dt
    d_old, d_new = blade_dir(old), blade_dir(th)
    p += v * dt
    r = np.array([RAD[g] for g in gen]); m = r ** 2
    # ball-ball
    dd = p[None, :, :] - p[:, None, :]
    dist = np.hypot(dd[..., 0], dd[..., 1])
    rr = r[None, :] + r[:, None]
    ii, jj = np.where(np.triu(dist < rr, 1))
    if len(ii):
        dij = dist[ii, jj] + 1e-6
        nrm = (p[jj] - p[ii]) / dij[:, None]
        over = np.minimum(rr[ii, jj] - dij, 6.0)
        wi = m[jj] / (m[ii] + m[jj])
        np.add.at(p, ii, -nrm * (over * wi)[:, None]); np.add.at(p, jj, nrm * (over * (1 - wi))[:, None])
        rel = np.sum((v[jj] - v[ii]) * nrm, axis=1); app = rel < 0
        jimp = (2 * rel[app] / (1 / m[ii[app]] + 1 / m[jj[app]]))[:, None] * nrm[app]
        np.add.at(v, ii[app], jimp / m[ii[app], None]); np.add.at(v, jj[app], -jimp / m[jj[app], None])
    # ring -> notes
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
    # blade
    rel = p - (PX, PY)
    s_along = rel @ d_new
    n_old = np.array([-d_old[1], d_old[0]]); n_new = np.array([-d_new[1], d_new[0]])
    side_old = (rel - v * dt) @ n_old
    side_new = rel @ n_new
    on_blade = np.abs(s_along) < BL
    crossed = np.where((np.sign(side_old) != np.sign(side_new)) & on_blade)[0]
    to_cut = [i for i in crossed if gen[i] < GENS and immune[i] <= 0]
    # the rod and the blade knock away what they can't cut
    small = np.zeros(0, int)        # the smallest pieces are too small to cut: the laser passes through them
    for i in small:
        sgn = 1.0 if side_new[i] >= 0 else -1.0
        p[i] += n_new * sgn * (r[i] - abs(side_new[i]))
        vn = np.dot(v[i], n_new) * sgn
        if vn < 0:
            v[i] -= 2 * vn * n_new * sgn
    for i in sorted(to_cut, reverse=True):
        x, y = p[i]; g = gen[i]
        split(i, n_new, th)
        cuts += 1
        om = min(OMAX, om + DOM)
        song.sfx(t, "slice", float((x - CX) / R), 0.8)
        for _ in range(8 + 2 * (GENS - g)):
            sparks.append([x + rng.uniform(-6, 6), y + rng.uniform(-6, 6), rng.uniform(6, 14), t, (1.0, 0.9, 0.95)])
        events.append((t, "cut", g))
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
SPR = [neon.BallSprites([GEN_COLS[g]], RAD[g], glow=2.2, glow_alpha=0.45) for g in range(GENS + 1)]
blade_trail = []

def blade_col():
    return neon.mix(BLADE_COOL, BLADE_HOT, min(1.0, heat ** 1.3))

def half_disc(x, y, r, ang, nrm, sign, col, alpha):
    """one half of a ball that is being cut (clipped by the blade line)"""
    ctx.save()
    ctx.translate(x, y)
    base = math.atan2(nrm[1], nrm[0]) if sign > 0 else math.atan2(-nrm[1], -nrm[0])
    ctx.move_to(0, 0)
    ctx.arc(0, 0, r, base - math.pi / 2, base + math.pi / 2)
    ctx.close_path()
    g = cairo.RadialGradient(-r * 0.3, -r * 0.35, r * 0.05, 0, 0, r)
    g.add_color_stop_rgba(0, *neon.mix(col, (1, 1, 1), 0.8), alpha)
    g.add_color_stop_rgba(0.5, *neon.mix(col, (1, 1, 1), 0.2), alpha)
    g.add_color_stop_rgba(1, *neon.mix(col, (0, 0, 0), 0.35), alpha)
    ctx.set_source(g); ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.9 * alpha); ctx.set_line_width(2.5); ctx.stroke()
    ctx.restore()

def draw_blade(a, bc, alpha=1.0):
    d = blade_dir(a)
    x0, y0 = PX - d[0] * BL, PY - d[1] * BL
    x1, y1 = PX + d[0] * BL, PY + d[1] * BL
    pulse = 1.0 + 0.5 * heat * (0.5 + 0.5 * math.sin(t * 28))
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for wd, al in ((58, 0.05), (34, 0.10), (19, 0.22), (10, 0.45)):
        ctx.set_source_rgba(*bc, al * pulse * alpha); ctx.set_line_width(wd * (0.9 + 0.25 * heat))
        ctx.move_to(x0, y0); ctx.line_to(x1, y1); ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(*neon.mix(bc, (1, 1, 1), 0.78), 0.97 * alpha); ctx.set_line_width(6)
    ctx.move_to(x0, y0); ctx.line_to(x1, y1); ctx.stroke()
    ctx.restore()

def draw_spin_disc(bc):
    """faint disc swept by the blade so the danger zone is readable"""
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.RadialGradient(PX, PY, BL * 0.2, PX, PY, BL)
    al = 0.025 + 0.05 * min(1.0, om / 4)
    g.add_color_stop_rgba(0, *bc, al * 0.4); g.add_color_stop_rgba(0.97, *bc, al); g.add_color_stop_rgba(1, *bc, 0)
    ctx.set_source(g); ctx.arc(PX, PY, BL, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*bc, 0.10 + 0.08 * heat); ctx.set_line_width(1.5)
    ctx.set_dash([10, 14], t * 40); ctx.arc(PX, PY, BL, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gcol = neon.mix((0.3, 0.5, 1.0), (1.0, 0.3, 0.35), heat ** 1.5)
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 950)
    ga = 0.04 + 0.13 * pr + 0.03 * math.sin(t * 2.0)
    if burst_t is not None:
        ga *= math.exp(-(t - burst_t) * 1.5)
    rg.add_color_stop_rgba(0, *gcol, ga); rg.add_color_stop_rgba(1, *gcol, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    shake = 0.0
    if burst_t is None and heat > 0.8:
        shake = 6 * ((heat - 0.8) / 0.2) ** 2
    if burst_t is not None:
        shake = 26 * math.exp(-(t - burst_t) * 6)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    neon.ring(ctx, CX, CY, R + 3, PAL["ring"], t, heat=0.0)
    if burst_t is None:
        draw_spin_disc(blade_col())
    # balls (pieces that were just cut are drawn as flying half-discs first)
    for g in range(GENS + 1):
        idx = [i for i in np.where(gen == g)[0] if t - born[i] >= SPLIT_ANIM or burst_t is not None]
        if idx:
            SPR[g].draw(ctx, [tuple(p[i]) for i in idx], [0] * len(idx))
    for st, pos, r0, ang, g0, nrm in splits[-60:]:
        age = t - st
        if 0 <= age < SPLIT_ANIM and burst_t is None:
            k = age / SPLIT_ANIM
            off = r0 * 0.35 * k
            for sgn in (1, -1):
                half_disc(pos[0] + nrm[0] * off * sgn, pos[1] + nrm[1] * off * sgn, r0 * (1 - 0.25 * k), ang, nrm, sgn,
                          GEN_COLS[g0], 1.0)
            # slit flash along the cut
            d = blade_dir(ang)
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_source_rgba(1, 1, 1, 0.9 * (1 - k)); ctx.set_line_width(4)
            ctx.move_to(pos[0] - d[0] * r0 * 1.3, pos[1] - d[1] * r0 * 1.3); ctx.line_to(pos[0] + d[0] * r0 * 1.3, pos[1] + d[1] * r0 * 1.3)
            ctx.stroke(); ctx.restore()
    # blade on top
    if burst_t is None:
        bc = blade_col()
        blade_trail.append(th); del blade_trail[:-8]
        for k_, ta in enumerate(blade_trail[:-1]):
            draw_blade(ta, bc, alpha=0.13 * (k_ + 1) / len(blade_trail))
        draw_blade(th, bc)
        hg = cairo.RadialGradient(PX, PY, 0, PX, PY, 34)
        hg.add_color_stop_rgba(0, 1, 1, 1, 0.95); hg.add_color_stop_rgba(0.35, *bc, 0.7); hg.add_color_stop_rgba(1, *bc, 0)
        ctx.set_source(hg); ctx.arc(PX, PY, 34, 0, 2 * math.pi); ctx.fill()
        if heat > 0.55 and fx_rng.random() < (heat - 0.55) * 1.8:
            d = blade_dir(th); s0 = fx_rng.uniform(-1.0, 1.0) * BL
            sparks.append([PX + d[0] * s0, PY + d[1] * s0, fx_rng.uniform(5, 10), t, (1.0, 0.55, 0.3)])
    else:
        dt_b = t - burst_t
        sa = max(0.0, 0.75 - dt_b * 1.3)
        if sa > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*BLADE_HOT, sa); ctx.set_line_width(20 * sa + 2)
            ctx.arc(CX, CY, 40 + 2200 * dt_b, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for fx, fy, _vx, _vy, ang, ln, frot, _vr, ft0 in frags:
            fa = max(0.0, 1 - (t - ft0) / 2.0)
            ctx.save(); ctx.translate(fx, fy); ctx.rotate(ang + frot)
            for wd, al in ((22, 0.18), (6, 0.95)):
                ctx.set_source_rgba(*BLADE_HOT, al * fa); ctx.set_line_width(wd)
                ctx.move_to(-ln / 2, 0); ctx.line_to(ln / 2, 0); ctx.stroke()
            ctx.restore()
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
    # live counter: pieces
    if counter and burst_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(110)
        txt = f"{len(p):,}"
        xb, yb, tw, th_, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1660)
        ctx.text_path(txt)
        cc = neon.mix(neon.mix(PAL["ring"], (1, 1, 1), 0.5), blade_col(), heat ** 2)
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
ct = [round(e[0], 1) for e in events if e[1] == "cut"]
print("seed", SEED, "log(t,pieces,cuts,deg,om)", log)
print("cut times", ct)
print("done", [round(e[0], 1) for e in events if e[1] == "done"], "burst", burst_t and round(burst_t, 2), "duration", round(t, 2), "pieces", len(p))
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
