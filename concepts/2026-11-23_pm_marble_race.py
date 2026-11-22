"""2026-11-23 18:00 — marble-race (new family): "Gate Race"
Replaces 'Grow Escape' (user: looked like the same ring-escape video with new music).
8 neon marbles (one per colour) race down a tall neon course; the camera follows the pack downward.
Rule: the course has 7 gates. When every marble but one has passed a gate, the gate SHUTS (turns red) and the
last marble is out — it drops off the course. The last gate is the finish line: the first of the final two
to break the neon ribbon wins, and on the next bar the whole course lights up in the winner's colour.
Sections: zigzag ramps, bumper field, spinning bar, steep zigzag, bumper diamond, twin spinners, final run.
A row of colour dots at the top shows the live race order (eliminated colours go grey).

usage: python3 concepts/2026-11-23_pm_marble_race.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 8
G = 1400.0
DRAG = G / 1100.0 ** 2          # quadratic air drag: free-fall terminal ~1100 px/s
MR = 24.0
XL, XR = 70.0, 1010.0
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 13
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
MUSIC_SEED = 2026112348   # random_song(seed, avoid=last 11 recipes incl. 08:00 jazzhop) -> trance_lite / pluck
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
song = music.random_song(MUSIC_SEED, avoid=RECENT)
COLS = [(1.0, 0.25, 0.30), (1.0, 0.58, 0.18), (1.0, 0.92, 0.25), (0.45, 1.0, 0.35),
        (0.20, 0.90, 1.0), (0.30, 0.45, 1.0), (0.72, 0.38, 1.0), (1.0, 0.38, 0.78)]
PAL = {"bg": ((0.02, 0.01, 0.07), (0.00, 0.00, 0.03)), "ring": (0.8, 0.85, 1.0), "balls": COLS,
       "accent": (1.0, 0.95, 0.85)}
SEC_COLS = [(0.25, 0.85, 1.0), (0.55, 0.45, 1.0), (1.0, 0.40, 0.80), (0.30, 1.0, 0.75), (1.0, 0.65, 0.30),
            (0.40, 0.60, 1.0), (0.95, 0.90, 1.0)]
P = {k: float(os.environ.get(k, v)) for k, v in dict(NA="2", NB="3", NC="3", ND="3", NE="3", NF="3", NG="2", SPW="1.5", SPW2="1.9").items()}

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)

# ---------------- course ----------------
SEG = []        # x0, y0, x1, y1, section
BUMP = []       # x, y, R, section
SPIN = []       # cx, cy, half, omega, phase, section
GATES = []      # y, x0, x1
sec = 0

def seg(x0, y0, x1, y1, s=None):
    SEG.append((x0, y0, x1, y1, sec if s is None else s))

def zigzag(y, n, drop, pitch, start_left=True, gap=90):
    pitch = drop + 100              # always room for a marble under the end of the ramp above
    for i in range(n):
        yh = y + i * pitch
        if (i % 2 == 0) == start_left:
            seg(XL, yh, XR - gap, yh + drop)
        else:
            seg(XR, yh, XL + gap, yh + drop)
    return y + (n - 1) * pitch + drop

def funnel_gate(y, h=230, half=46, chute=130):
    seg(XL, y, 540 - half, y + h); seg(XR, y, 540 + half, y + h)
    seg(540 - half, y + h, 540 - half, y + h + chute); seg(540 + half, y + h, 540 + half, y + h + chute)
    GATES.append((y + h + chute * 0.55, 540 - half, 540 + half))
    return y + h + chute

START_Y = 220.0
START_SEG = len(SEG)
seg(250, START_Y, 830, START_Y, 0)           # start shelf (opens at t = 0.35)
seg(250, 60, 250, START_Y, 0); seg(830, 60, 830, START_Y, 0)
# A: zigzag ramps
y = zigzag(330, int(P["NA"]), 150, 175, True)
y = funnel_gate(y + 60)
# B: bumper field, then a ramp
sec = 1
y0 = y + 110
for row in range(4):
    xs = [190, 430, 670, 910] if row % 2 == 0 else [310, 550, 790]
    for x in xs:
        BUMP.append((x + (8 if row % 4 == 1 else 0), y0 + row * 150, 34, sec))
y = zigzag(y0 + 3 * 150 + 120, int(P["NB"]), 150, 175, False)
y = funnel_gate(y + 60)
# C: spinning bar, then ramps
sec = 2
SPIN.append((540, y + 360, 285, P["SPW"], 0.3, sec))
y = zigzag(y + 720, int(P["NC"]), 150, 175, True)
y = funnel_gate(y + 60)
# D: steep zigzag
sec = 3
y = zigzag(y + 90, int(P["ND"]), 190, 200, False, gap=95)
y = funnel_gate(y + 60)
# E: bumper diamond, then ramps
sec = 4
y0 = y + 120
rows = [[540], [400, 680], [260, 540, 820], [400, 680], [540]]
for r_, xs in enumerate(rows):
    for x in xs:
        BUMP.append((x, y0 + r_ * 140, 38, sec))
y = zigzag(y0 + 4 * 140 + 120, int(P["NE"]), 150, 175, True)
y = funnel_gate(y + 60)
# F: twin spinners (counter-rotating), then ramps
sec = 5
SPIN.append((305, y + 330, 215, P["SPW2"], 0.0, sec))
SPIN.append((775, y + 330, 215, -P["SPW2"], 1.2, sec))
y = zigzag(y + 640, int(P["NF"]), 150, 175, False)
y = funnel_gate(y + 60)
# G: final run
sec = 6
y = zigzag(y + 90, int(P["NG"]), 150, 175, True)
FIN_Y0 = y + 60
y = funnel_gate(FIN_Y0)
FINISH = len(GATES) - 1
COURSE_END = y + 400
SEGA = np.array([[s[0], s[1]] for s in SEG]); SEGB = np.array([[s[2], s[3]] for s in SEG])
SEGS = np.array([s[4] for s in SEG])
seg_on = np.ones(len(SEG), bool)
BUMPA = np.array([[b[0], b[1]] for b in BUMP]); BUMPR = np.array([b[2] for b in BUMP])
bump_flash = np.zeros(len(BUMP))
gate_state = [0] * len(GATES)      # 0 open, 1 closed (red), 2 finish broken
gate_passed = [set() for _ in GATES]
gate_t = [None] * len(GATES)
lead_t = []

# ---------------- marbles ----------------
NM = 8
order0 = rng.permutation(NM)
p = np.array([[290 + i * 71.4 + rng.uniform(-4, 4), START_Y - MR - 0.5] for i in range(NM)])
v = np.array([[rng.uniform(-15, 15), 0.0] for _ in range(NM)])
colour = order0.copy()            # colour index of each marble
alive = np.ones(NM, bool)
out_t = np.full(NM, -1.0)
hit_cool = np.zeros(NM) - 9
trail = [[] for _ in range(NM)]
STARS = [(fx_rng.uniform(0, W), fx_rng.uniform(-2000, 14000), fx_rng.uniform(0.6, 2.2), fx_rng.uniform(0.08, 0.3)) for _ in range(420)]
t = 0.0
events = []
sparks = []
winner = None
finish_t = None
payoff_pending = None
payoff_t = None
build_keys = []
cam_y, zoom = 700.0, 0.85
started = False

def spin_ends(k, tt):
    cx, cy, half, om, ph, _ = SPIN[k]
    a = ph + om * tt
    return (cx - half * math.cos(a), cy - half * math.sin(a)), (cx + half * math.cos(a), cy + half * math.sin(a))

def race_order():
    """alive marbles first (furthest gate passed, then lowest = furthest along), then eliminated by out time"""
    key = []
    for i in range(NM):
        gp = sum(1 for g in gate_passed if i in g)
        if alive[i] or i == winner:
            key.append((0 if i == winner else 1, -gp, -p[i, 1], i))
        else:
            key.append((2, -out_t[i], 0, i))
    return [k[-1] for k in sorted(key)]

def progress():
    if payoff_t is not None:
        return 1.0
    lead = max((p[i, 1] for i in range(NM) if alive[i]), default=COURSE_END)
    return float(np.clip((lead - 300) / (GATES[FINISH][0] - 300), 0, 1))

def eliminate(i, g):
    alive[i] = False
    out_t[i] = t
    gate_state[g] = 1
    gate_t[g] = t
    v[i] = [rng.uniform(-60, 60), 80]
    pan = float((p[i, 0] - 540) / 470)
    song.sfx(t, "zap", 0.0, 0.7)
    song.sfx(t + 0.05, "whoosh", pan, 0.6)
    events.append((t, "out", (i, g)))
    for _ in range(12):
        sparks.append([p[i, 0], p[i, 1], rng.uniform(8, 18), t, COLS[colour[i]]])

def physics_step(dt):
    global started, winner, finish_t, payoff_pending
    if not started and t >= 0.35:
        started = True
        seg_on[START_SEG] = False
        song.sfx(t, "whoosh", 0.0, 0.6)
        events.append((t, "start", 0))
    # eliminated marbles just fall (no collisions)
    dead = ~alive
    if winner is not None:
        dead[winner] = False
    v[dead, 1] += G * dt
    p[dead] += v[dead] * dt
    act = np.where(~dead)[0]
    if len(act) == 0:
        return
    v[act, 1] += G * dt
    spd = np.hypot(v[act, 0], v[act, 1])
    v[act] -= v[act] * (DRAG * spd * dt)[:, None]
    p[act] += v[act] * dt
    if winner is not None and finish_t is not None:
        # winner glides to a stop below the finish
        v[winner] *= 0.985
        return
    # marble-marble
    for a in range(len(act)):
        for b in range(a + 1, len(act)):
            i, j = act[a], act[b]
            d = p[j] - p[i]
            dist = math.hypot(*d)
            if dist < 2 * MR and dist > 1e-6:
                nrm = d / dist
                over = 2 * MR - dist
                p[i] -= nrm * over / 2; p[j] += nrm * over / 2
                rel = np.dot(v[j] - v[i], nrm)
                if rel < 0:
                    imp = 0.9 * rel * nrm
                    v[i] += imp; v[j] -= imp
                    if -rel > 160:
                        song.sfx(t, "tick", float((p[i, 0] - 540) / 470), min(0.4, 0.15 + -rel / 2000))
    # static segments
    for i in act:
        near = seg_on & (np.minimum(SEGA[:, 1], SEGB[:, 1]) < p[i, 1] + 60) & (np.maximum(SEGA[:, 1], SEGB[:, 1]) > p[i, 1] - 60)
        for k in np.where(near)[0]:
            a, b = SEGA[k], SEGB[k]
            ab = b - a
            u = np.clip(np.dot(p[i] - a, ab) / np.dot(ab, ab), 0, 1)
            q = a + ab * u
            d = p[i] - q
            dist = math.hypot(*d)
            if dist < MR and dist > 1e-6:
                nrm = d / dist
                p[i] = q + nrm * MR
                vn = np.dot(v[i], nrm)
                if vn < 0:
                    vt = v[i] - vn * nrm
                    v[i] = vt * 0.99985 - 0.32 * vn * nrm
                    if -vn > 170 and t - hit_cool[i] > 0.09:
                        hit_cool[i] = t
                        song.note(t, float((p[i, 0] - 540) / 470), vel=min(1.0, 0.45 + -vn / 1400))
                        events.append((t, "hit", (float(q[0]), float(q[1]), int(colour[i]), int(SEGS[k]))))
        # bumpers
        if len(BUMP):
            d = p[i] - BUMPA
            dist = np.hypot(d[:, 0], d[:, 1])
            for k in np.where(dist < BUMPR + MR)[0]:
                nrm = d[k] / (dist[k] + 1e-6)
                p[i] = BUMPA[k] + nrm * (BUMPR[k] + MR)
                vn = np.dot(v[i], nrm)
                if vn < 0:
                    v[i] = v[i] - 2.0 * vn * nrm
                    sp = math.hypot(*v[i])
                    if sp < 480:
                        v[i] *= 480 / (sp + 1e-6)
                    bump_flash[k] = 1.0
                    if t - hit_cool[i] > 0.06:
                        hit_cool[i] = t
                        song.note(t, float((p[i, 0] - 540) / 470), vel=0.9)
        # spinners (moving segments: reflect the relative velocity)
        for k in range(len(SPIN)):
            cx, cy, half, om, ph, s_ = SPIN[k]
            if abs(p[i, 1] - cy) > half + MR + 5:
                continue
            (ax, ay), (bx, by) = spin_ends(k, t)
            a = np.array([ax, ay]); b = np.array([bx, by]); ab = b - a
            u = np.clip(np.dot(p[i] - a, ab) / np.dot(ab, ab), 0, 1)
            q = a + ab * u
            d = p[i] - q
            dist = math.hypot(*d)
            if dist < MR + 3 and dist > 1e-6:
                nrm = d / dist
                p[i] = q + nrm * (MR + 3)
                vw = om * np.array([-(q[1] - cy), q[0] - cx])
                vr = v[i] - vw
                vn = np.dot(vr, nrm)
                if vn < 0:
                    vt = vr - vn * nrm
                    v[i] = vw + vt * 0.999 - 0.55 * vn * nrm
                    if -vn > 150 and t - hit_cool[i] > 0.08:
                        hit_cool[i] = t
                        song.note(t, float((p[i, 0] - 540) / 470), vel=min(1.0, 0.5 + -vn / 1400))
                        events.append((t, "spin", (float(q[0]), float(q[1]), int(colour[i]), k)))
    # walls
    for i in act:
        if p[i, 0] < XL + MR:
            p[i, 0] = XL + MR; v[i, 0] = abs(v[i, 0]) * 0.4
        if p[i, 0] > XR - MR:
            p[i, 0] = XR - MR; v[i, 0] = -abs(v[i, 0]) * 0.4
    # gates
    for g, (gy, gx0, gx1) in enumerate(GATES):
        if gate_state[g]:
            continue
        for i in act:
            if i not in gate_passed[g] and p[i, 1] > gy:
                gate_passed[g].add(i)
                pan = float((p[i, 0] - 540) / 470)
                if g == FINISH:
                    winner = i
                    finish_t = t
                    gate_state[g] = 2
                    gate_t[g] = t
                    song.sfx(t, "shatter", pan, 0.9)
                    song.sfx(t + 0.02, "chime", pan, 1.0)
                    events.append((t, "finish", (i, g)))
                    for _ in range(40):
                        sparks.append([rng.uniform(gx0, gx1), gy, rng.uniform(10, 24), t, COLS[colour[i]]])
                    payoff_pending = song.next_bar(t + 0.25)
                    for j in range(NM):
                        if alive[j] and j != i:
                            eliminate(j, g)
                    gate_state[g] = 2
                    alive[i] = False      # stays visible as winner
                    return
                song.sfx(t, "chime", pan, 0.35)
                events.append((t, "pass", (i, g)))
                if len(gate_passed[g]) == 1:
                    lead_t.append((round(t, 1), g))
        n_alive = int(alive.sum())
        behind = [i for i in range(NM) if alive[i] and i not in gate_passed[g]]
        if n_alive >= 2 and len(behind) == 1 and g != FINISH:
            eliminate(behind[0], g)

def do_payoff():
    global payoff_t
    payoff_t = t
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 0.6)
    gy = GATES[FINISH][0]
    for _ in range(120):
        a = fx_rng.uniform(0, 2 * math.pi)
        rr = fx_rng.uniform(40, 520)
        sparks.append([540 + rr * math.cos(a), gy + rr * math.sin(a), fx_rng.uniform(10, 28), t, COLS[colour[winner]]])
    events.append((t, "payoff", 0))

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
sprite_cache = {}

def sprites(rpx):
    q = max(5, int(round(rpx)))
    if q not in sprite_cache:
        sprite_cache[q] = neon.SkinSprites(COLS + [(0.45, 0.45, 0.52)], q, skin="orb")
    return sprite_cache[q]

def S(x, y):
    return 540 + (x - 540) * zoom, H * 0.47 + (y - cam_y) * zoom

def tube(pts, rgb, alpha=1.0, width=4.0, glowk=1.0):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for w, a in [(34, 0.05), (18, 0.10), (9, 0.25)]:
        ctx.set_source_rgba(*rgb, a * alpha * glowk); ctx.set_line_width(w * zoom * width / 4)
        ctx.move_to(*pts[0])
        for q in pts[1:]:
            ctx.line_to(*q)
        ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(*neon.mix(rgb, (1, 1, 1), 0.6), 0.92 * alpha); ctx.set_line_width(max(1.5, width * zoom))
    ctx.move_to(*pts[0])
    for q in pts[1:]:
        ctx.line_to(*q)
    ctx.stroke(); ctx.restore()

def sec_col(s):
    c = SEC_COLS[s % len(SEC_COLS)]
    if payoff_t is not None:
        k = min(1.0, (t - payoff_t) / 0.5)
        c = neon.mix(c, COLS[colour[winner]], 0.85 * k)
    return c

def view_y(y):
    return abs(y - cam_y) * zoom < H * 0.62

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gc = COLS[colour[winner]] if payoff_t is not None else sec_col(int(np.clip(pr * 6.99, 0, 6)))
    rg = cairo.RadialGradient(540, H * 0.5, 0, 540, H * 0.5, 1100)
    ga = 0.04 + 0.10 * pr + 0.02 * math.sin(t * 2.0)
    if payoff_t is not None:
        ga = 0.18 * math.exp(-(t - payoff_t) * 0.8) + 0.06
    rg.add_color_stop_rgba(0, *gc, ga); rg.add_color_stop_rgba(1, *gc, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()
    # parallax star dust (slower than the course -> sense of falling)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for x, y, rr, a in STARS:
        sy = H * 0.47 + (y - cam_y * 0.45) * 0.6
        sy = sy % (H + 200) - 100
        ctx.set_source_rgba(0.75, 0.8, 1.0, a); ctx.arc(x, sy, rr, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    # outer walls
    ytop, ybot = cam_y - H * 0.6 / zoom, cam_y + H * 0.6 / zoom
    for x in (XL, XR):
        tube([S(x, max(60, ytop)), S(x, min(COURSE_END, ybot))], (0.55, 0.62, 1.0), 0.5, 3.0)
    for k, (x0, y0, x1, y1, s_) in enumerate(SEG):
        if not seg_on[k] or not (view_y(y0) or view_y(y1)):
            continue
        tube([S(x0, y0), S(x1, y1)], sec_col(s_), 1.0, 5.5)
    # bumpers
    for k, (x, y, R, s_) in enumerate(BUMP):
        if not view_y(y):
            continue
        sx, sy = S(x, y)
        f = bump_flash[k]
        c = neon.mix(sec_col(s_), (1, 1, 1), 0.5 * f)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        for w, a in [(30, 0.06), (16, 0.12), (8, 0.3)]:
            ctx.set_source_rgba(*c, a * (1 + 1.5 * f)); ctx.set_line_width(w * zoom)
            ctx.new_path(); ctx.arc(sx, sy, R * zoom, 0, 2 * math.pi); ctx.stroke()
        g = cairo.RadialGradient(sx, sy, 0, sx, sy, R * zoom)
        g.add_color_stop_rgba(0, *c, 0.10 + 0.35 * f); g.add_color_stop_rgba(1, *c, 0.02)
        ctx.set_source(g); ctx.arc(sx, sy, R * zoom, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        ctx.save(); ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.65), 0.9); ctx.set_line_width(max(1.5, 3.5 * zoom))
        ctx.new_path(); ctx.arc(sx, sy, R * zoom * (1 + 0.12 * f), 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    # spinners
    for k in range(len(SPIN)):
        cx, cy, half, om, ph, s_ = SPIN[k]
        if not view_y(cy):
            continue
        a, b = spin_ends(k, t)
        tube([S(*a), S(*b)], sec_col(s_), 1.0, 7.0, 1.3)
        sx, sy = S(cx, cy)
        ctx.save(); ctx.set_source_rgba(1, 1, 1, 0.9); ctx.arc(sx, sy, 7 * zoom, 0, 2 * math.pi); ctx.fill(); ctx.restore()
    # gates
    for g, (gy, gx0, gx1) in enumerate(GATES):
        if not view_y(gy):
            continue
        st = gate_state[g]
        age = t - gate_t[g] if gate_t[g] is not None else 9
        if g == FINISH and st == 2:
            continue      # ribbon broken: drawn as sparks
        if st == 1:
            c = (1.0, 0.22, 0.25); alpha = 1.0; dash = None
            glow = 1.0 + 2.5 * math.exp(-age * 4)
        else:
            c = (1.0, 1.0, 1.0) if g == FINISH else (0.85, 0.95, 1.0)
            alpha = 0.85; dash = [10 * zoom, 8 * zoom] if g != FINISH else [6 * zoom, 6 * zoom]
            glow = 1.0 + 0.3 * math.sin(t * 6)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        for w, a in [(24, 0.08), (10, 0.25)]:
            ctx.set_source_rgba(*c, a * glow); ctx.set_line_width(w * zoom)
            ctx.move_to(*S(gx0 - 10, gy)); ctx.line_to(*S(gx1 + 10, gy)); ctx.stroke()
        ctx.restore()
        ctx.save()
        if dash:
            ctx.set_dash(dash, -t * 30 * zoom)
        ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.4), alpha); ctx.set_line_width(max(2, 5 * zoom))
        ctx.move_to(*S(gx0, gy)); ctx.line_to(*S(gx1, gy)); ctx.stroke(); ctx.restore()
    # hit flashes
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, data in events[-60:]:
        if kind in ("hit", "spin") and 0 <= t - et < 0.3:
            a = 1 - (t - et) / 0.3
            x, y, c, _ = data
            sx, sy = S(x, y)
            g = cairo.RadialGradient(sx, sy, 0, sx, sy, 40 * zoom)
            g.add_color_stop_rgba(0, *COLS[c], 0.5 * a); g.add_color_stop_rgba(1, *COLS[c], 0)
            ctx.set_source(g); ctx.arc(sx, sy, 40 * zoom, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    # light trails
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for i in range(NM):
        if (not alive[i] and i != winner) or len(trail[i]) < 3:
            continue
        pts = [S(x, y) for x, y in trail[i]]
        n = len(pts)
        for k in range(1, n):
            a = (k / n) ** 1.6
            ctx.set_source_rgba(*COLS[colour[i]], 0.38 * a); ctx.set_line_width(MR * zoom * 1.3 * a)
            ctx.move_to(*pts[k - 1]); ctx.line_to(*pts[k]); ctx.stroke()
    ctx.restore()
    # marbles (eliminated: grey, fading as they fall)
    spr = sprites(MR * zoom)
    pts, cis = [], []
    for i in range(NM):
        if not alive[i] and i != winner:
            age = t - out_t[i]
            if age > 1.6:
                continue
            ci = len(COLS) if age > 0.35 else colour[i]
        else:
            ci = colour[i]
        sx, sy = S(*p[i])
        if -60 < sy < H + 60:
            pts.append((sx, sy)); cis.append(ci)
    spr.draw(ctx, pts, cis)
    if winner is not None:
        sx, sy = S(*p[winner])
        k = 0.5 + 0.5 * math.sin(t * 8)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_source_rgba(*COLS[colour[winner]], 0.35 + 0.25 * k); ctx.set_line_width(4)
        ctx.new_path(); ctx.arc(sx, sy, MR * zoom * (1.6 + 0.3 * k), 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    # sparks
    live = [s for s in sparks if t - s[3] < 0.6]
    sparks[:] = live
    by = {}
    for x, y, sz, st_, c in live:
        a = 1 - (t - st_) / 0.6
        sx, sy = S(x, y)
        by.setdefault((c, round(a, 1)), []).append((sx, sy, sz * (0.6 + a) * max(0.6, zoom)))
    for (c, a), pts_ in by.items():
        neon.sparkles(ctx, pts_, neon.mix(c, (1, 1, 1), 0.4), alpha=a * 0.9)
    # race order dots (top)
    order = race_order()
    for slot, i in enumerate(order):
        x = 540 + (slot - 3.5) * 92
        y = 118
        grey = not alive[i] and i != winner
        c = (0.42, 0.42, 0.5) if grey else COLS[colour[i]]
        big = 1.35 if i == winner else 1.0
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        g = cairo.RadialGradient(x, y, 0, x, y, 40 * big)
        g.add_color_stop_rgba(0, *c, 0.12 if grey else 0.45); g.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(g); ctx.arc(x, y, 40 * big, 0, 2 * math.pi); ctx.fill(); ctx.restore()
        ctx.save(); ctx.set_source_rgba(*c, 0.35 if grey else 1.0); ctx.arc(x, y, 17 * big, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.25 if grey else 0.7); ctx.arc(x - 5, y - 6, 5 * big, 0, 2 * math.pi); ctx.fill(); ctx.restore()
    if counter and payoff_t is None:
        n = int(alive.sum()) + (1 if winner is not None else 0)
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(110)
        txt = str(n)
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1820)
        ctx.text_path(txt)
        cc = neon.mix(gc, (1, 1, 1), 0.45)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(20); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.95); ctx.fill()
        ctx.restore()
    if payoff_t is not None:
        fa = max(0.0, 0.45 - (t - payoff_t) * 2.5)
        if fa > 0:
            ctx.set_source_rgba(*neon.mix(COLS[colour[winner]], (1, 1, 1), 0.7), fa); ctx.paint()
        age = t - payoff_t
        if age < 1.3:
            sx, sy = S(540, GATES[FINISH][0])
            a = 1 - age / 1.3
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*COLS[colour[winner]], 0.8 * a); ctx.set_line_width(4 + 18 * a)
            ctx.new_path(); ctx.arc(sx, sy, 40 + 1800 * age, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
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
while True:
    for _ in range(SUB):
        physics_step(dt)
        if payoff_pending is not None and payoff_t is None and t >= payoff_pending:
            do_payoff()
        t += dt
    bump_flash *= 0.85
    for i in range(NM):
        trail[i].append((float(p[i, 0]), float(p[i, 1])))
        if len(trail[i]) > 14:
            trail[i].pop(0)
    # camera: frame every marble still in the race (and the winner at the end)
    ids = [i for i in range(NM) if alive[i]] or ([winner] if winner is not None else [0])
    if winner is not None:
        ids = [winner]
    ys = p[ids, 1]
    lo, hi = ys.min(), ys.max()
    zt = float(np.clip(1500 / (hi - lo + 800), 0.62, 0.95))
    if winner is not None:
        zt = 0.8
    ct = (lo + hi) / 2 + 120 / zt
    if frame == 0:
        cam_y, zoom = 650.0, 0.8
    cam_y += (ct - cam_y) * 0.08
    zoom += (zt - zoom) * 0.04
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if os.environ.get("DEBUG") and frame % 120 == 0:
        print(round(t), [(int(x), int(y)) for x, y in p], list(alive.astype(int)))
    if not SIM_ONLY:
        draw(); surf.flush()
        if first is None:
            first = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            c2 = cairo.Context(first); c2.set_source_surface(surf, 0, 0); c2.paint()
        ff.stdin.write(bytes(surf.get_data()))
    frame += 1
    if payoff_t is not None and t >= payoff_t + TAIL:
        break
    if t > 85:
        break

if ff:
    ff.stdin.close(); ff.wait()
outs = [(round(e[0], 1), e[2][1]) for e in events if e[1] == "out"]
print("seed", SEED, "outs (t, gate)", outs)
print("finish", finish_t and round(finish_t, 2), "payoff", payoff_t and round(payoff_t, 2), "duration", round(t, 2),
      "winner colour", winner is not None and int(colour[winner]), "course_end", round(COURSE_END), "gates", [round(g[0]) for g in GATES])
print("leader at gates", lead_t)
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
