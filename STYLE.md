# physics-shorts — style & production rules

Accounts: TikTok `toomanyball`, Instagram `toomanyball9`, YouTube Shorts channel. Audience is global: every caption, title, hashtag and on-screen text is in English.

## Video
- 1080x1920, 60 fps, H.264 (`-preset veryfast -crf 21 -pix_fmt yuv420p`), AAC audio. Keep the file under 90 MB (raise CRF if needed).
- Length: 61–70 s (TikTok Creator Rewards only pays for videos over 1 minute). Never pad with dead time — the length must come from a slower, richer build-up.

## Retention (keep people watching to the end)
- Slow burn: growth starts slow and steadily accelerates; tune spawn rules/cooldowns so the climax lands at roughly 55–65 s.
- Something visibly changes every ~5–8 s: palette drifting, a new phase/rule kicking in, arena slowly rotating or shrinking, trails appearing, background glow intensifying.
- Music builds with it: start sparse (pad + few notes), add bass, then denser arpeggios, chord changes speeding up near the climax.
- Clear rising tension in the last ~10 s (ring reddening, shaking, near-full), then a satisfying payoff (burst/release).
- First 2 seconds must already be interesting (motion + sound immediately, no empty intro).
- Short tail after the payoff (1–3 s) that fades back toward the opening look so the video loops nicely on replay.
- Artistic, delicate, NEON look — always render with `neon.py` (see `concepts/2026-11-17_neon_reference.py`):
  - near-black gradient background with vignette (`neon.background`), or `neon.fade` for light trails
  - neon-tube arena outline with layered additive glow (`neon.ring` / `neon.polygon_ring`), heating to red before a burst
  - every ball = soft additive glow halo + glossy core (bright centre, coloured body, thin bright rim, small specular) via `neon.BallSprites`
  - harmonious palettes from `neon.PALETTES` (synthwave, aurora, sunset, ocean, spectrum, mono-ice) — vary per video, 3–7 colours max, never random rainbow noise unless the concept is "spectrum"
  - small details: sparkles on hits/bursts (`neon.sparkles`), shockwave ring, fragments glowing as they fly
- On-screen text: NO title/hook text, NO "BOOM"/"POP" text, NO "N reached!" banners. The only allowed text is a live counter number near the bottom (optional).
- Ball speed moderate (~450–600 px/s). No gravity unless the concept needs it.
- When the concept fills a container, it must end only when the container is *completely, visibly packed* (use real ball–ball collisions so balls stack, not overlap). Then the container bursts: brief white flash, shockwave ring, container fragments flying out, balls spreading outward.
- The hook comes from the rule itself and the growing tension (ring turning red and shaking as it nears full).

## Sound — always use `music.py`
- It must feel like music, not beeps: `music.Song` snaps every event to a tempo grid (16ths), picks notes from the current chord with an arpeggio pattern, and lays them over a soft pad + marimba bass, with soft hats arriving as the build rises, ping-pong delay and reverb.
- Vary per video: bpm (80–118), key, mode (major/minor/dorian/lydian/mixolydian), progression (`music.PROGRESSIONS`), lead voice (pluck, bell, marimba, ep).
- Big moments: `song.accent(t)` (soft low thump + bright chord swell).
- Quiet and pleasant: render peaks at -6 dBFS (default). Never use existing songs or melodies.

## Concept mix (lean on what works, but stay balanced)
- Before choosing, check recent performance in Metricool analytics (views, likes, comments, average watch time if available) for the last 7–14 days and record it in concepts.md.
- Over any 7 days: about half the videos may be variations of the best-performing concept families; the other half must be different families (new ideas or rotating older ones).
- Never the same concept family two days in a row, and at most 3 videos of one family per 7 days.
- A "variation" must still look clearly new (different arena, palette, twist on the rule).

## Concept ideas (rotate, never repeat back-to-back; log every one in concepts.md)
Families (use the family name in concepts.md):
- wall-split: wall hit doubles / triples / x1.5 the ball (done 2026-11-17)
- escape: concentric rotating rings with gaps; each ring breaks with a chord when a ball gets out; escaped balls may spawn 2 more
- ring-break: ball breaks layer after layer of a regenerating wall ("will it escape?")
- shrinking-arena: arena shrinks while balls multiply or grow
- growing-ball: each bounce makes the ball bigger/faster until it fills the arena
- spinning-shape: balls inside a rotating hexagon / triangle / star / square
- slicer: a line sweeps or cuts across the circle; every cut doubles the pieces
- color-battle: colour teams race to fill the arena / take over territory (no real flags or brands)
- marble-race: original coloured marbles race down an obstacle course; elimination rounds
- plinko: Galton board — hundreds of balls fall through pegs and build a glowing bell curve
- pendulum-wave: rainbow row of pendulum balls drifting in and out of wave patterns (spectrum look)
- polyrhythm: concentric arcs/rings where each ball bounces at its own tempo and pitch; they realign at the end
- converge: chaotic bouncing balls that, by time-reversal, snap into a perfect shape / one point / a picture, then scatter again
- chaos-divergence: many double pendulums or balls starting 0.001 apart, rainbow-coloured, fanning into chaos
- orbits: balls orbiting a gravity well, slingshots, collapsing into one core
- trails: balls leave fading light trails that paint spirals / spectrum art
- spawner-plays-melody: every bounce plays the next note of an ORIGINAL melody, speeding up as balls multiply
- newtons-cradle / chain reactions: dominoes of balls, cascades, sand-like ball piles
## Posting
- Metricool brand blogId `8158935`, timezone Asia/Seoul. Publish 08:00 KST.
- One scheduled post per network so hashtags differ:
  - YouTube: type `short`, madeForKids false, title ends with `#shorts`; hashtags `#shorts #satisfying #physics #simulation #oddlysatisfying`
  - TikTok: hashtags `#fyp #satisfying #physics #simulation #oddlysatisfying #asmr`
  - Instagram: type `REEL`; hashtags `#reels #satisfying #physics #simulation #oddlysatisfying #asmr`
- Media URL: `https://raw.githubusercontent.com/toomanyball9-collab/physics-shorts/main/videos/<file>.mp4`
