"""2026-11-25 18:00 — marble-race (variation): "Lift Laps"
One fixed screen, a looping neon course: 8 marbles roll down four ramps (bumper field, spinning bar) to the
bottom, where an air-jet LIFT shoots them back up to the top — lap after lap.
Rule: when every marble but one has finished the lap (= entered the lift), the TRAPDOOR at the end of the last
ramp opens (red) for the last marble: it rolls onto it and falls out of the race. Then it shuts again.
8 marbles -> 7 laps -> 1 winner: on the next bar the jet blasts the winner out of the top of the lift and the
whole course floods in its colour; tail crossfades back to the opening frame.
Colour dots at the top show the live race order (eliminated colours go grey); counter = marbles left.
Wall/ramp/bumper/spinner bounces = music (song.note); lift = whoosh; trapdoor = zap; fall = whoosh; finish = chime.

usage: python3 concepts/2026-11-25_pm_lift_laps.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 8
G = float(os.environ.get("GRAV", "2000"))
DRAG = G / float(os.environ.get("VT", "1300")) ** 2
MR = 21.0
XL, XR = 62.0, 1018.0
SH0, SH1 = 902.0, 1018.0          # lift shaft x-range
SH_TOP, SH_BOT = 300.0, 1720.0
JET = float(os.environ.get("JET", "7000"))
JET_V = float(os.environ.get("JETV", "2100"))
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
# random_song(2026112563, avoid=last 15 recipes incl. 08:00 desert) -> chiptune 124 F# mixolydian square
MUSIC_SEED = int(os.environ.get("MSEED", "2026112563"))
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
          dict(genre="trance_lite", bpm=123, key="F", mode="minor", lead="pluck"),
          dict(genre="bossa", bpm=96, key="G#", mode="major", lead="ep"),
          dict(genre="space", bpm=76, key="B", mode="lydian", lead="bell"),
          dict(genre="desert", bpm=104, key="F#", mode="phrygian_dominant", lead="flute")]
song = music.random_song(MUSIC_SEED, avoid=RECENT)
COLS = [(1.0, 0.25, 0.30), (1.0, 0.58, 0.18), (1.0, 0.92, 0.25), (0.45, 1.0, 0.35),
        (0.20, 0.90, 1.0), (0.30, 0.45, 1.0), (0.72, 0.38, 1.0), (1.0, 0.38, 0.78)]
PAL = {"bg": ((0.02, 0.01, 0.07), (0.00, 0.00, 0.03)), "ring": (0.8, 0.85, 1.0), "balls": COLS,
       "accent": (1.0, 0.95, 0.85)}
BASE_COL = (0.45, 0.55, 1.0)
LIFT_COL = (0.55, 0.95, 1.0)

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)

# ---------------- course (screen coordinates, fixed camera) ----------------
SEG = []     # x0, y0, x1, y1
BUMP = []    # x, y, R
SPIN = []    # cx, cy, half, omega, phase

def seg(x0, y0, x1, y1):
    SEG.append((x0, y0, x1, y1))
    return len(SEG) - 1

# top: lift exit hood, deflects marbles left onto ramp 1
seg(SH1, 400, 872, 300)
# ramp 1 (right -> left)
seg(SH0, 470, 200, 620)
# bumper field
for r_, xs in enumerate([[160, 340, 520, 700], [250, 430, 610, 790]]):
    for x in xs:
        BUMP.append((x, 725 + r_ * 115, 30))
# ramp 2 (left -> right)
seg(XL, 935, 740, 1080)
# spinning bar
SPIN.append((470, 1200, float(os.environ.get("SPH", "140")), float(os.environ.get("SPW", "1.7")), 0.4))
# ramp 3 (right -> left)
seg(SH0, 1315, 210, 1460)
# ramp 4 (left -> right) into the lift, trapdoor at its end
TD_X0, TD_X1 = 730.0, SH0
R4 = (XL, 1540, SH0, 1660)
def r4y(x):
    return R4[1] + (R4[3] - R4[1]) * (x - R4[0]) / (R4[2] - R4[0])
seg(R4[0], R4[1], TD_X0, r4y(TD_X0))
TD = seg(TD_X0, r4y(TD_X0), TD_X1, r4y(TD_X1))
# lift shaft: left wall from just above the ramp-4 entrance up to the top; floor under the entrance
SHAFT_L = seg(SH0, 1580, SH0, 470)
seg(SH0, 1660 + 2 * MR + 16, SH1, 1660 + 2 * MR + 16)      # lift floor (jet pad)
START_BAR = seg(526, 430, 526, 470 + 150 * (SH0 - 526) / (SH0 - 200))       # holds the pack at the top until t = 0.3
SEGA = np.array([[s[0], s[1]] for s in SEG]); SEGB = np.array([[s[2], s[3]] for s in SEG])
seg_on = np.ones(len(SEG), bool)
BUMPA = np.array([[b[0], b[1]] for b in BUMP]); BUMPR = np.array([b[2] for b in BUMP])
bump_flash = np.zeros(len(BUMP))
LAP_X = SH0 + 2            # crossing into the shaft = lap complete

# ---------------- marbles ----------------
NM = 8
order0 = rng.permutation(NM)
# start: lined up in the lift shaft? no — on ramp 1, behind a start bar
p = np.array([[870 - i * 2.05 * MR - rng.uniform(0, 3), 0.0] for i in range(NM)])
for i in range(NM):
    x = p[i, 0]
    y0 = 470 + (620 - 470) * (SH0 - x) / (SH0 - 200)
    p[i, 1] = y0 - MR - 1.0
v = np.zeros((NM, 2))
colour = order0.copy()
alive = np.ones(NM, bool)
falling = np.zeros(NM, bool)
out_t = np.full(NM, -1.0)
laps = np.zeros(NM, int)
in_lift = np.zeros(NM, bool)
hit_cool = np.zeros(NM) - 9
trail = [[] for _ in range(NM)]
doomed = None
td_open_t = None
td_state = 0                    # 0 closed, 1 open
t = 0.0
events, sparks, build_keys = [], [], []
winner = None
finish_t = None
payoff_pending = payoff_t = None
started = False
lead_hist = []
judge = [1]
acc_flag = np.zeros(NM, bool)
armed = [None]
accidents = 0
lapped = 0

def race_order():
    key = []
    for i in range(NM):
        if alive[i] or i == winner:
            prog = laps[i] + lap_frac(i)
            key.append((0 if i == winner else 1, -prog, i))
        else:
            key.append((2, -out_t[i], i))
    return [k[-1] for k in sorted(key)]

def lap_frac(i):
    """rough position along the lap (0 at the top, 1 at the lift entrance)."""
    x, y = p[i]
    if in_lift[i]:
        return 0.0 + 0.0 * y
    return float(np.clip((y - 300) / (1640 - 300), 0, 0.999))

def progress():
    if payoff_t is not None:
        return 1.0
    n_out = NM - int(alive.sum())
    return float(np.clip(0.1 * min(1, t / 6) + 0.82 * (n_out / (NM - 1)) + 0.12 * min(1, t / 60), 0, 1))

def open_trapdoor(i):
    global doomed, td_open_t, td_state
    doomed = i
    td_state = 1
    td_open_t = t
    seg_on[TD] = False
    song.sfx(t, "zap", 0.6, 0.7)
    events.append((t, "td_open", (i,)))

def physics_step(dt):
    global started, winner, finish_t, payoff_pending, doomed, td_state, lapped, accidents
    if not started and t >= 0.3:
        started = True
        seg_on[START_BAR] = False
        song.sfx(t, "whoosh", 0.3, 0.6)
    # fallen marbles just drop
    for i in np.where(falling)[0]:
        v[i, 1] += G * dt
        p[i] += v[i] * dt
    act = [i for i in range(NM) if (alive[i] or i == winner) and not falling[i]]
    for i in act:
        v[i, 1] += G * dt
        if SH0 + 2 < p[i, 0] < SH1 and SH_TOP < p[i, 1] < SH_BOT:
            # air jet: strong upward push, capped speed
            v[i, 1] -= JET * dt
            if v[i, 1] < -JET_V:
                v[i, 1] = -JET_V
            v[i, 0] *= 0.96
        sp = math.hypot(*v[i])
        v[i] -= v[i] * DRAG * sp * dt
        p[i] += v[i] * dt
    if winner is not None and payoff_t is not None:
        return
    # marble-marble
    for a in range(len(act)):
        for b in range(a + 1, len(act)):
            i, j = act[a], act[b]
            d = p[j] - p[i]
            dist = math.hypot(*d)
            if 1e-6 < dist < 2 * MR:
                nrm = d / dist
                over = 2 * MR - dist
                p[i] -= nrm * over / 2; p[j] += nrm * over / 2
                rel = np.dot(v[j] - v[i], nrm)
                if rel < 0:
                    imp = 0.9 * rel * nrm
                    v[i] += imp; v[j] -= imp
                    if -rel > 180:
                        song.sfx(t, "tick", float((p[i, 0] - 540) / 470), min(0.4, 0.15 + -rel / 2000))
    for i in act:
        near = seg_on & (np.minimum(SEGA[:, 1], SEGB[:, 1]) < p[i, 1] + 50) & (np.maximum(SEGA[:, 1], SEGB[:, 1]) > p[i, 1] - 50)
        for k in np.where(near)[0]:
            a, b = SEGA[k], SEGB[k]
            ab = b - a
            u = np.clip(np.dot(p[i] - a, ab) / np.dot(ab, ab), 0, 1)
            q = a + ab * u
            d = p[i] - q
            dist = math.hypot(*d)
            if 1e-6 < dist < MR:
                nrm = d / dist
                p[i] = q + nrm * MR
                vn = np.dot(v[i], nrm)
                if vn < 0:
                    vt = v[i] - vn * nrm
                    v[i] = vt * 0.99985 - 0.32 * vn * nrm
                    if -vn > 170 and t - hit_cool[i] > 0.09:
                        hit_cool[i] = t
                        song.note(t, float((p[i, 0] - 540) / 470), vel=min(1.0, 0.45 + -vn / 1400))
                        events.append((t, "hit", (float(q[0]), float(q[1]), int(colour[i]))))
        if len(BUMP):
            d = p[i] - BUMPA
            dist = np.hypot(d[:, 0], d[:, 1])
            for k in np.where(dist < BUMPR + MR)[0]:
                nrm = d[k] / (dist[k] + 1e-6)
                p[i] = BUMPA[k] + nrm * (BUMPR[k] + MR)
                vn = np.dot(v[i], nrm)
                if vn < 0:
                    v[i] = v[i] - 2.0 * vn * nrm
                    spd = math.hypot(*v[i])
                    if spd < 460:
                        v[i] *= 460 / (spd + 1e-6)
                    bump_flash[k] = 1.0
                    if t - hit_cool[i] > 0.06:
                        hit_cool[i] = t
                        song.note(t, float((p[i, 0] - 540) / 470), vel=0.9)
        for k in range(len(SPIN)):
            cx, cy, half, om, ph = SPIN[k]
            if abs(p[i, 1] - cy) > half + MR + 5:
                continue
            aa = ph + om * t
            A = np.array([cx - half * math.cos(aa), cy - half * math.sin(aa)])
            B = np.array([cx + half * math.cos(aa), cy + half * math.sin(aa)])
            ab = B - A
            u = np.clip(np.dot(p[i] - A, ab) / np.dot(ab, ab), 0, 1)
            q = A + ab * u
            d = p[i] - q
            dist = math.hypot(*d)
            if 1e-6 < dist < MR + 3:
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
                        events.append((t, "spin", (float(q[0]), float(q[1]), int(colour[i]))))
        # outer walls
        if p[i, 0] < XL + MR:
            p[i, 0] = XL + MR; v[i, 0] = abs(v[i, 0]) * 0.4
        if p[i, 0] > XR - MR:
            p[i, 0] = XR - MR; v[i, 0] = -abs(v[i, 0]) * 0.4
        if p[i, 1] < 270:
            p[i, 1] = 270; v[i, 1] = abs(v[i, 1]) * 0.3
        # the shaft wall is solid from both sides (no squeezing through it in a crowd)
        if 470 - MR < p[i, 1] < 1580 + MR * 0.5:
            if in_lift[i] and p[i, 0] < SH0 + MR:
                p[i, 0] = SH0 + MR; v[i, 0] = abs(v[i, 0]) * 0.3
            elif not in_lift[i] and SH0 - MR < p[i, 0] < SH0 + 2 and p[i, 1] > 480:
                p[i, 0] = SH0 - MR; v[i, 0] = -abs(v[i, 0]) * 0.3
        # lap line: entering the lift
        if not in_lift[i] and p[i, 0] > LAP_X and 1450 < p[i, 1] < 1700 and alive[i]:
            in_lift[i] = True
            laps[i] += 1
            pan = 0.8
            song.sfx(t, "whoosh", pan, 0.45)
            events.append((t, "lap", (i, int(laps[i]))))
            if doomed is not None and i != doomed:
                lapped += 1
        if in_lift[i] and p[i, 1] < SH_TOP + 60:
            in_lift[i] = False
        # trapdoor fall
        if td_state == 1 and i != doomed and TD_X0 < p[i, 0] < TD_X1 and p[i, 1] > r4y(p[i, 0]) + MR + 4 and not acc_flag[i]:
            acc_flag[i] = True
            accidents += 1
        if doomed == i and td_state == 1 and p[i, 1] > r4y(min(max(p[i, 0], TD_X0), TD_X1)) + MR + 4 and p[i, 0] > TD_X0 - 5:
            alive[i] = False
            falling[i] = True
            out_t[i] = t
            song.sfx(t, "whoosh", 0.4, 0.7)
            events.append((t, "out", (i,)))
            for _ in range(14):
                sparks.append([p[i, 0], p[i, 1], rng.uniform(8, 18), t, COLS[colour[i]]])
            doomed = None
    # trapdoor shuts again once the doomed marble has dropped
    if td_state == 1 and doomed is None and t - out_t.max() > 0.5:
        td_state = 0
        seg_on[TD] = True
        events.append((t, "td_close", 0))
    # elimination rule: the last alive marble to finish lap `judge[0]` is out
    if doomed is None and armed[0] is None and winner is None:
        al = [i for i in range(NM) if alive[i]]
        L = judge[0]
        if len(al) >= 2:
            done = [i for i in al if laps[i] >= L]
            if len(done) == len(al) - 1:
                last = [i for i in al if laps[i] < L][0]
                judge[0] += 1
                if len(al) == 2:
                    w = done[0]
                    winner = w
                    finish_t = t
                    song.sfx(t, "chime", 0.8, 1.0)
                    events.append((t, "finish", (w,)))
                    payoff_pending = song.next_bar(t + 0.25)
                armed[0] = last
    # the trapdoor opens under the last marble once it reaches the final ramp
    if armed[0] is not None and doomed is None:
        i = armed[0]
        if p[i, 1] > 1480 and p[i, 0] > TD_X0 - 260 and not in_lift[i]:
            armed[0] = None
            open_trapdoor(i)

def do_payoff():
    global payoff_t
    payoff_t = t
    song.accent(t)
    song.sfx(t, "shatter", 0.6, 0.6)
    # the jet blasts the winner out of the top
    if winner is not None:
        v[winner] = [-120, -1600]
        p[winner, 0] = (SH0 + SH1) / 2
    for _ in range(140):
        a = fx_rng.uniform(0, 2 * math.pi)
        rr = fx_rng.uniform(40, 700)
        sparks.append([540 + rr * math.cos(a), 950 + rr * math.sin(a) * 1.3, fx_rng.uniform(10, 28), t, COLS[colour[winner]]])
    events.append((t, "payoff", 0))

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SPR = neon.SkinSprites(COLS + [(0.45, 0.45, 0.52)], MR, skin="orb")
STARS = [(fx_rng.uniform(0, W), fx_rng.uniform(0, H), fx_rng.uniform(0.6, 2.0), fx_rng.uniform(0.06, 0.25)) for _ in range(260)]

def course_col():
    """course glows in the current leader's colour (blends as the lead changes)."""
    if payoff_t is not None:
        k = min(1.0, (t - payoff_t) / 0.5)
        return neon.mix(cur_col[0], COLS[colour[winner]], k)
    return cur_col[0]

cur_col = [BASE_COL]

def tube(pts, rgb, alpha=1.0, width=5.0, glowk=1.0):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for w, a in [(34, 0.05), (18, 0.10), (9, 0.25)]:
        ctx.set_source_rgba(*rgb, a * alpha * glowk); ctx.set_line_width(w * width / 5)
        ctx.move_to(*pts[0])
        for q in pts[1:]:
            ctx.line_to(*q)
        ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(*neon.mix(rgb, (1, 1, 1), 0.6), 0.92 * alpha); ctx.set_line_width(width)
    ctx.move_to(*pts[0])
    for q in pts[1:]:
        ctx.line_to(*q)
    ctx.stroke(); ctx.restore()

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    cc = course_col()
    rg = cairo.RadialGradient(540, H * 0.5, 0, 540, H * 0.5, 1100)
    ga = 0.04 + 0.09 * pr + 0.02 * math.sin(t * 2.0)
    if payoff_t is not None:
        ga = 0.2 * math.exp(-(t - payoff_t) * 0.8) + 0.06
    rg.add_color_stop_rgba(0, *cc, ga); rg.add_color_stop_rgba(1, *cc, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for x, y, rr, a in STARS:
        ctx.set_source_rgba(0.75, 0.8, 1.0, a * (0.7 + 0.3 * math.sin(t * 1.3 + x))); ctx.arc(x, y, rr, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    ctx.save()
    duel = int(alive.sum()) == 2 and winner is None
    shake = 16 * math.exp(-(t - payoff_t) * 6) if payoff_t is not None else (1.5 if duel else 0.0)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    # lift shaft: glass tube + rising jet chevrons
    jet_a = 0.5 + (0.5 if payoff_t is not None and t - payoff_t < 1.0 else 0.0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.LinearGradient(SH0, 0, SH1, 0)
    g.add_color_stop_rgba(0, *LIFT_COL, 0.0); g.add_color_stop_rgba(0.5, *LIFT_COL, 0.07 * (1 + jet_a)); g.add_color_stop_rgba(1, *LIFT_COL, 0.0)
    ctx.set_source(g); ctx.rectangle(SH0, SH_TOP, SH1 - SH0, SH_BOT - SH_TOP); ctx.fill()
    ctx.set_line_width(3); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    xm = (SH0 + SH1) / 2
    off = (t * 520) % 90
    for k in range(17):
        y = SH_BOT - 20 - k * 90 - off
        if y < SH_TOP + 30:
            continue
        a = 0.42 * jet_a * (0.6 + 0.4 * math.sin(k + t * 3))
        ctx.set_source_rgba(*LIFT_COL, a)
        ctx.move_to(xm - 22, y + 10); ctx.line_to(xm, y - 6); ctx.line_to(xm + 22, y + 10); ctx.stroke()
    ctx.restore()
    tube([(SH1, 400), (SH1, 1660 + 2 * MR + 16)], LIFT_COL, 0.8, 4.0)
    for x in (XL,):
        tube([(x, 300), (x, 1660)], neon.mix(cc, (0.5, 0.55, 0.9), 0.6), 0.5, 3.0)
    for k, (x0, y0, x1, y1) in enumerate(SEG):
        if k in (START_BAR,) and not seg_on[k]:
            continue
        if k == TD:
            continue
        col = LIFT_COL if k == SHAFT_L else cc
        tube([(x0, y0), (x1, y1)], col, 1.0, 5.5)
    # trapdoor
    x0, y0, x1, y1 = SEG[TD]
    if td_state == 0:
        age = t - max([e[0] for e in events if e[1] == "td_close"] or [-9])
        c = neon.mix((1.0, 0.25, 0.3), cc, min(1.0, age / 0.6))
        gk = 1.0
        if armed[0] is not None:
            # armed for the last marble: the trapdoor pulses red while it waits
            c = (1.0, 0.25, 0.3); gk = 1.2 + 0.6 * math.sin(t * 12)
        tube([(x0, y0), (x1, y1)], c, 1.0, 5.5, gk)
        ctx.save(); ctx.set_source_rgba(1, 1, 1, 0.7)
        for x_ in (x0, x1):
            ctx.arc(x_, r4y(x_), 5, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
    else:
        age = t - td_open_t
        # the two flaps swing down
        ang = min(1.0, age / 0.25) * 1.25
        L = (x1 - x0) / 2
        sl = math.atan2(y1 - y0, x1 - x0)
        flap = [((x0, y0), sl + ang), ((x1, y1), sl + math.pi - ang)]
        blink = 0.65 + 0.35 * math.sin(age * 20)
        for (hx, hy), a in flap:
            tube([(hx, hy), (hx + L * 0.98 * math.cos(a), hy + L * 0.98 * math.sin(a))], (1.0, 0.22, 0.25), blink, 5.5, 1.6)
    # bumpers
    for k, (x, y, R_) in enumerate(BUMP):
        f = bump_flash[k]
        c = neon.mix(cc, (1, 1, 1), 0.5 * f)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        for w, a in [(30, 0.06), (16, 0.12), (8, 0.3)]:
            ctx.set_source_rgba(*c, a * (1 + 1.5 * f)); ctx.set_line_width(w)
            ctx.new_path(); ctx.arc(x, y, R_, 0, 2 * math.pi); ctx.stroke()
        gr = cairo.RadialGradient(x, y, 0, x, y, R_)
        gr.add_color_stop_rgba(0, *c, 0.10 + 0.35 * f); gr.add_color_stop_rgba(1, *c, 0.02)
        ctx.set_source(gr); ctx.arc(x, y, R_, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        ctx.save(); ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.65), 0.9); ctx.set_line_width(3.5)
        ctx.new_path(); ctx.arc(x, y, R_ * (1 + 0.12 * f), 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    for k in range(len(SPIN)):
        cx, cy, half, om, ph = SPIN[k]
        aa = ph + om * t
        tube([(cx - half * math.cos(aa), cy - half * math.sin(aa)), (cx + half * math.cos(aa), cy + half * math.sin(aa))], cc, 1.0, 7.0, 1.3)
        ctx.save(); ctx.set_source_rgba(1, 1, 1, 0.9); ctx.arc(cx, cy, 7, 0, 2 * math.pi); ctx.fill(); ctx.restore()
    # hit flashes
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, data in events[-80:]:
        if kind in ("hit", "spin") and 0 <= t - et < 0.3:
            a = 1 - (t - et) / 0.3
            x, y, c = data
            gr = cairo.RadialGradient(x, y, 0, x, y, 40)
            gr.add_color_stop_rgba(0, *COLS[c], 0.5 * a); gr.add_color_stop_rgba(1, *COLS[c], 0)
            ctx.set_source(gr); ctx.arc(x, y, 40, 0, 2 * math.pi); ctx.fill()
        if kind == "lap" and 0 <= t - et < 0.5:
            a = 1 - (t - et) / 0.5
            i = data[0]
            ctx.set_source_rgba(*COLS[colour[i]], 0.6 * a); ctx.set_line_width(4)
            ctx.new_path(); ctx.arc(LAP_X, 1660, 20 + 50 * (1 - a), 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
    # trails
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(NM):
        if (not alive[i] and i != winner) or len(trail[i]) < 3:
            continue
        pts = trail[i]; n = len(pts)
        for k in range(1, n):
            if abs(pts[k][1] - pts[k - 1][1]) > 200:
                continue
            a = (k / n) ** 1.6
            ctx.set_source_rgba(*COLS[colour[i]], 0.38 * a); ctx.set_line_width(MR * 1.3 * a)
            ctx.move_to(*pts[k - 1]); ctx.line_to(*pts[k]); ctx.stroke()
    ctx.restore()
    pts, cis = [], []
    for i in range(NM):
        if not alive[i] and i != winner:
            age = t - out_t[i]
            if age > 1.6 or p[i, 1] > H + 60:
                continue
            ci = len(COLS) if age > 0.35 else colour[i]
        else:
            ci = colour[i]
        pts.append(tuple(p[i])); cis.append(ci)
    SPR.draw(ctx, pts, cis)
    dm = doomed if doomed is not None else armed[0]
    if dm is not None:
        x, y = p[dm]
        k = 0.5 + 0.5 * math.sin(t * 14)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_source_rgba(1.0, 0.25, 0.3, 0.35 + 0.35 * k); ctx.set_line_width(3)
        ctx.new_path(); ctx.arc(x, y, MR * (1.5 + 0.2 * k), 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    if winner is not None:
        x, y = p[winner]
        k = 0.5 + 0.5 * math.sin(t * 8)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_source_rgba(*COLS[colour[winner]], 0.35 + 0.25 * k); ctx.set_line_width(4)
        ctx.new_path(); ctx.arc(x, y, MR * (1.6 + 0.3 * k), 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    live = [s for s in sparks if t - s[3] < 0.6]
    sparks[:] = live
    by = {}
    for x, y, sz, st_, c in live:
        a = 1 - (t - st_) / 0.6
        by.setdefault((c, round(a, 1)), []).append((x, y, sz * (0.6 + a)))
    for (c, a), q in by.items():
        neon.sparkles(ctx, q, neon.mix(c, (1, 1, 1), 0.4), alpha=a * 0.9)
    ctx.restore()
    # race order dots
    order = race_order()
    for slot, i in enumerate(order):
        x = 540 + (slot - 3.5) * 100
        y = 160
        grey = not alive[i] and i != winner
        c = (0.42, 0.42, 0.5) if grey else COLS[colour[i]]
        big = 1.35 if i == winner else 1.0
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        gr = cairo.RadialGradient(x, y, 0, x, y, 42 * big)
        gr.add_color_stop_rgba(0, *c, 0.12 if grey else 0.45); gr.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(gr); ctx.arc(x, y, 42 * big, 0, 2 * math.pi); ctx.fill(); ctx.restore()
        ctx.save(); ctx.set_source_rgba(*c, 0.35 if grey else 1.0); ctx.arc(x, y, 18 * big, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.25 if grey else 0.7); ctx.arc(x - 5, y - 6, 5 * big, 0, 2 * math.pi); ctx.fill(); ctx.restore()
    if counter and payoff_t is None:
        n = int(alive.sum()) + (1 if winner is not None and not alive[winner] else 0)
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(110)
        txt = str(n)
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb - 40, 1840)
        ctx.text_path(txt)
        c2 = neon.mix(cc, (1, 1, 1), 0.45)
        ctx.set_source_rgba(*c2, 0.10); ctx.set_line_width(20); ctx.stroke_preserve()
        ctx.set_source_rgba(*c2, 0.95); ctx.fill()
        ctx.restore()
    if payoff_t is not None:
        dtp = t - payoff_t
        fa = max(0.0, 0.45 - dtp * 2.5)
        if fa > 0:
            ctx.set_source_rgba(*neon.mix(COLS[colour[winner]], (1, 1, 1), 0.7), fa); ctx.paint()
        if dtp < 1.3:
            a = 1 - dtp / 1.3
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*COLS[colour[winner]], 0.8 * a); ctx.set_line_width(4 + 18 * a)
            ctx.new_path(); ctx.arc((SH0 + SH1) / 2, SH_TOP, 40 + 1900 * dtp, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
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
leader = None
while True:
    for _ in range(SUB):
        physics_step(dt)
        if payoff_pending is not None and payoff_t is None and t >= payoff_pending:
            do_payoff()
        t += dt
    bump_flash *= 0.85
    for i in range(NM):
        trail[i].append((float(p[i, 0]), float(p[i, 1])))
        if len(trail[i]) > 12:
            trail[i].pop(0)
    # course colour follows the leader
    order = race_order()
    if order[0] != leader:
        leader = order[0]
        lead_hist.append((round(t, 1), int(colour[leader])))
    target = COLS[colour[leader]] if t > 1.0 else BASE_COL
    target = neon.mix(target, BASE_COL, 0.35)
    cur_col[0] = neon.mix(cur_col[0], target, 0.05)
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if PREVIEW and any(abs(t - pt) < 0.5 / FPS for pt in PREVIEW):
        draw(); surf.flush(); surf.write_to_png(f"prev_{t:05.1f}.png")
    if os.environ.get("DEBUG") and frame % 60 == 0:
        print(round(t), [(int(x), int(y)) for x, y in p], list(laps), list(alive.astype(int)))
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
outs = [(round(e[0], 1), int(colour[e[2][0]])) for e in events if e[1] == "out"]
print("seed", SEED, "outs (t, colour)", outs, "lapped", lapped, "accidents", accidents)
print("finish", finish_t and round(finish_t, 2), "payoff", payoff_t and round(payoff_t, 2), "duration", round(t, 2),
      "winner colour", winner is not None and int(colour[winner]), "laps", list(laps), "lead changes", len(lead_hist))
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
