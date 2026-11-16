import sys, numpy as np, wave, subprocess
sys.path.insert(0, '.')
import music
def events(dur, seed):
    r = np.random.default_rng(seed); t = 0.2; out = []
    while t < dur:
        rate = 1.5 + 14 * (t / dur) ** 2
        t += r.exponential(1 / rate); out.append((t, r.uniform(-.6, .6)))
    return out
# smoke test every genre
for i, g in enumerate(music.GENRES):
    s = music.Song.from_genre(g, seed=i)
    for t, p in events(4, i): s.note(t, p)
    s.render('/tmp/t.wav', 4)
print("all genres OK:", len(music.GENRES))
picks = ["lofi", "musicbox", "synthwave", "japanese", "bossa", "cinematic"]
parts = []
for i, g in enumerate(picks):
    s = music.Song.from_genre(g, seed=100 + i)
    D = 9.0
    for t, p in events(D - 1.2, i): s.note(t, p)
    s.accent(D - 1.2)
    fn = f'./samp_{i}.wav'
    s.render(fn, D, build=lambda t, D=D: min(1, t / (D - 1.2)))
    parts.append(fn); print(i + 1, s.recipe_str())
# concat with short fades
filt = "".join(f"[{i}:a]atrim=0:{9.6},afade=t=in:d=0.05,afade=t=out:st=9.0:d=0.6[a{i}];" for i in range(len(parts)))
filt += "".join(f"[a{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=0:a=1[out]"
cmd = ["ffmpeg", "-y", "-loglevel", "error"] + sum([["-i", p] for p in parts], []) + ["-filter_complex", filt, "-map", "[out]", "-c:a", "aac", "-b:a", "192k", "./music_sampler.m4a"]
subprocess.run(cmd, check=True)
