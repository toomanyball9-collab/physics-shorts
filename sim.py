import math, sys, subprocess, wave
import numpy as np
import cairo
from scipy.spatial import cKDTree

# ---------------- settings ----------------
W, H, FPS = 1080, 1920, 60
SUB = 4
CX, CY, R = W / 2, 960, 470
SPEED = 520.0                 # constant ball speed
BALL_R = 14.0
PACK = 0.80                   # area fraction that counts as "completely full"
COOLDOWN = 0.5
AFTER_BURST = 2.2
MAX_T = 45.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7
SIM_ONLY = "--sim" in sys.argv
OUT = "out_noaudio.mp4"
FONT = "Noto Sans CJK KR"

rng = np.random.default_rng(SEED)
CAP = int(PACK * (R / BALL_R) ** 2)

a0 = rng.uniform(0, 2 * math.pi)
p = np.array([[CX, CY]])
v = np.array([[math.cos(a0) * SPEED, math.sin(a0) * SPEED]])
cd = np.array([0.0])
hue = np.array([rng.random()])

events = []      # (time, kind)
t = 0.0
burst_t = None
pop = 0.0
frags = None

surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
ff = None
if not SIM_ONLY:
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", OUT
    ], stdin=subprocess.PIPE)

def hsv(h, s=0.85, v_=1.0):
    i = int(h * 6) % 6; f = h * 6 - int(h * 6)
    p_, q, t_ = v_ * (1 - s), v_ * (1 - f * s), v_ * (1 - (1 - f) * s)
    return [(v_, t_, p_), (q, v_, p_), (p_, v_, t_), (p_, q, v_), (t_, p_, v_), (v_, p_, q)][i]

def text_center(txt, y, size, rgb, scale=1.0):
    ctx.save()
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size * scale)
    xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
    ctx.move_to(W / 2 - tw / 2 - xb, y)
    ctx.text_path(txt)
    ctx.set_source_rgba(0, 0, 0, 0.85); ctx.set_line_width(10 * scale)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke_preserve()
    ctx.set_source_rgb(*rgb); ctx.fill()
    ctx.restore()

bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
bc = cairo.Context(bg)
lg = cairo.LinearGradient(0, 0, 0, H)
lg.add_color_stop_rgb(0, 0.04, 0.05, 0.14)
lg.add_color_stop_rgb(1, 0.01, 0.01, 0.05)
bc.set_source(lg); bc.paint()

def draw():
    n = len(p)
    fill = n / CAP
    ctx.set_source_surface(bg); ctx.paint()
    ctx.save()
    shake = 0.0
    if burst_t is None and fill > 0.8:
        shake = 7 * ((fill - 0.8) / 0.2) ** 2
    if burst_t is not None:
        shake = 30 * math.exp(-(t - burst_t) * 6)
    if shake > 0:
        ctx.translate(rng.uniform(-shake, shake), rng.uniform(-shake, shake))

    if burst_t is None:
        k = max(0.0, (fill - 0.6) / 0.4)
        col = (1, 1 - 0.75 * k, 1 - 0.85 * k)
        pulse = 1 + 0.5 * k * (0.5 + 0.5 * math.sin(t * 24))
        for w_, a in [(30 * pulse, 0.07), (16 * pulse, 0.14), (6, 0.95)]:
            ctx.set_source_rgba(*col, a); ctx.set_line_width(w_)
            ctx.arc(CX, CY, R + 3, 0, 2 * math.pi); ctx.stroke()
    else:
        dt_b = t - burst_t
        sr = R + 2200 * dt_b
        sa = max(0.0, 0.7 - dt_b * 1.3)
        if sa > 0:
            ctx.set_source_rgba(1, 0.85, 0.6, sa); ctx.set_line_width(24 * sa + 2)
            ctx.arc(CX, CY, sr, 0, 2 * math.pi); ctx.stroke()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for fx, fy, ang, rot, span, _vx, _vy, _w in frags:
            ctx.save(); ctx.translate(fx, fy); ctx.rotate(rot)
            ctx.set_source_rgba(1, 0.4, 0.3, max(0, 1 - dt_b * 0.5)); ctx.set_line_width(7)
            ctx.arc(-R * math.cos(ang), -R * math.sin(ang), R + 3, ang - span / 2, ang + span / 2)
            ctx.stroke(); ctx.restore()

    for i in range(n):
        x, y = p[i]
        if -30 < x < W + 30 and -30 < y < H + 30:
            ctx.set_source_rgb(*hsv(hue[i]))
            ctx.arc(x, y, BALL_R, 0, 2 * math.pi); ctx.fill()
    ctx.restore()

    if burst_t is None:
        text_center(f"{n:,}", 1660, 160, (1, 1, 1), scale=1.0 + 0.2 * pop)
    else:
        fa = max(0.0, 0.5 - (t - burst_t) * 2.5)
        if fa > 0:
            ctx.set_source_rgba(1, 1, 1, fa); ctx.paint()

def do_burst():
    global burst_t, frags, v
    burst_t = t
    d = p - (CX, CY)
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    radial = d / dist[:, None]
    jit = rng.uniform(-0.3, 0.3, len(p))
    c, s = np.cos(jit), np.sin(jit)
    radial = np.stack([radial[:, 0] * c - radial[:, 1] * s, radial[:, 0] * s + radial[:, 1] * c], 1)
    v = v * 0.3 + radial * (rng.uniform(250, 1100, len(p)) * (0.4 + 0.6 * dist / R))[:, None]
    frags = []
    N = 22
    for k in range(N):
        ang = 2 * math.pi * (k + 0.5) / N
        sp = rng.uniform(600, 1100)
        frags.append([CX + R * math.cos(ang), CY + R * math.sin(ang), ang, 0.0,
                      2 * math.pi / N * 0.85, math.cos(ang) * sp, math.sin(ang) * sp, rng.uniform(-5, 5)])
    events.append((t, "burst"))

def collide():
    """ball-ball: push apart + elastic exchange along the normal"""
    global p, v
    if len(p) < 2:
        return
    pairs = cKDTree(p).query_pairs(2 * BALL_R, output_type="ndarray")
    if len(pairs) == 0:
        return
    i, j = pairs[:, 0], pairs[:, 1]
    d = p[j] - p[i]
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    nrm = d / dist[:, None]
    over = (2 * BALL_R - dist) * 0.5
    corr = nrm * over[:, None]
    np.add.at(p, i, -corr)
    np.add.at(p, j, corr)
    rel = np.sum((v[j] - v[i]) * nrm, axis=1)
    app = rel < 0
    imp = nrm[app] * rel[app, None]
    np.add.at(v, i[app], imp)
    np.add.at(v, j[app], -imp)

frame = 0
dt = 1.0 / (FPS * SUB)
log_next = 0
while True:
    for _ in range(SUB):
        p += v * dt
        cd -= dt
        if burst_t is None:
            collide()
            n = len(p)
            d = p - (CX, CY)
            dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
            over = dist + BALL_R - R
            hit = np.where(over > 0)[0]
            if len(hit):
                nrm = d[hit] / dist[hit, None]
                p[hit] -= nrm * over[hit, None]
                vn = np.sum(v[hit] * nrm, axis=1)
                out = vn > 0
                v[hit[out]] -= 2 * vn[out, None] * nrm[out]
                ready = hit[cd[hit] <= 0]
                room = CAP - n
                if len(ready) and room > 0:
                    ready = ready[:room]
                    ang = rng.uniform(0.3, 0.8, len(ready)) * rng.choice([-1, 1], len(ready))
                    c, s_ = np.cos(ang), np.sin(ang)
                    vv = v[ready]
                    nv = np.stack([vv[:, 0] * c - vv[:, 1] * s_, vv[:, 0] * s_ + vv[:, 1] * c], 1)
                    nrm_r = nrm[np.searchsorted(hit, ready)]
                    p = np.vstack([p, p[ready] - nrm_r * BALL_R])
                    v = np.vstack([v, nv])
                    cd[ready] = COOLDOWN
                    cd = np.concatenate([cd, np.full(len(ready), COOLDOWN)])
                    hue = np.concatenate([hue, (hue[ready] + rng.uniform(0.05, 0.15, len(ready))) % 1])
                    events.append((t, "note"))
                    pop = 1.0
            # keep everyone moving at a steady pace
            sp = np.hypot(v[:, 0], v[:, 1]) + 1e-6
            v *= (SPEED / sp)[:, None]
            if len(p) >= CAP:
                do_burst()
        else:
            for f in frags:
                f[0] += f[5] * dt; f[1] += f[6] * dt; f[3] += f[7] * dt
        t += dt
    pop *= 0.85
    if not SIM_ONLY:
        draw(); surf.flush()
        ff.stdin.write(bytes(surf.get_data()))
    frame += 1
    if SIM_ONLY and t >= log_next:
        print(f"t={t:5.1f}s balls={len(p)}"); log_next += 1
    if burst_t is not None and t >= burst_t + AFTER_BURST:
        break
    if t >= MAX_T:
        break

if ff:
    ff.stdin.close(); ff.wait()
print("duration", round(t, 2), "CAP", CAP, "burst_t", burst_t)

# ---------------- music ----------------
# Original chord loop (C - G - Am - F, 2 s each), soft pad + bass underneath,
# every split plays the next note of an arpeggio over the current chord.
if not SIM_ONLY:
    SR = 44100
    total = int((t + 1.5) * SR)
    L = np.zeros(total); Rr = np.zeros(total)
    def midi(m): return 440.0 * 2 ** ((m - 69) / 12)
    CHORDS = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]  # C G Am F
    BAR = 2.0
    # arpeggio pattern over chord tones (index into tones list spanning 2 octaves)
    PATTERN = [0, 1, 2, 3, 4, 3, 2, 1, 0, 2, 4, 5, 4, 2, 3, 1]

    def keys(f, dur, decay):
        n = int(dur * SR); tt = np.arange(n) / SR
        env = np.exp(-tt * decay) * np.minimum(1, tt * 200)
        return (np.sin(2*np.pi*f*tt) + 0.35*np.sin(4*np.pi*f*tt)*np.exp(-tt*6)
                + 0.12*np.sin(6*np.pi*f*tt)*np.exp(-tt*9)) * env

    def add(sig, start, gain, pan=0.0):
        s0 = int(start * SR)
        if s0 >= total: return
        seg = sig[: total - s0]
        L[s0:s0+len(seg)] += seg * gain * (1 - pan) ; Rr[s0:s0+len(seg)] += seg * gain * (1 + pan)

    end_music = (burst_t if burst_t else t)
    # pad + bass
    nbars = int(end_music / BAR) + 1
    for b in range(nbars):
        ch = CHORDS[b % 4]; st = b * BAR
        dur = BAR + 0.6
        n = int(dur * SR); tt = np.arange(n) / SR
        env = np.minimum(1, tt / 0.5) * np.clip((dur - tt) / 0.6, 0, 1)
        pad = sum(np.sin(2*np.pi*midi(m)*tt) + np.sin(2*np.pi*midi(m)*1.004*tt) for m in ch) * env
        add(pad, st, 0.025)
        add(keys(midi(ch[0] - 24), BAR, 1.2), st, 0.16)
    # melody notes on splits (rate limited so dense moments become fast arpeggios)
    last = -1.0; step = 0
    for et, kind in events:
        if kind != "note" or et - last < 0.085: continue
        last = et
        ch = CHORDS[int(et / BAR) % 4]
        tones = ch + [m + 12 for m in ch]
        m = tones[PATTERN[step % len(PATTERN)]] + 12
        step += 1
        add(keys(midi(m), 1.2, 3.5), et, 0.11, pan=rng.uniform(-0.3, 0.3))
    # burst: soft low thump + a bright chord swell
    if burst_t:
        n = int(2.0 * SR); tt = np.arange(n) / SR
        f = 55 * np.exp(-tt * 2) + 35
        thump = np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-tt * 3)
        add(thump, burst_t, 0.45)
        for m in [72, 76, 79, 84]:
            add(keys(midi(m), 2.0, 1.5), burst_t, 0.08, pan=rng.uniform(-0.4, 0.4))
    st = np.stack([L, Rr], 1)
    st = np.tanh(st * 1.5) / 1.5
    st *= 0.5 / (np.abs(st).max() + 1e-9)        # peak ~ -6 dBFS, not too loud
    with wave.open("audio.wav", "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((st * 32767).astype(np.int16).tobytes())
