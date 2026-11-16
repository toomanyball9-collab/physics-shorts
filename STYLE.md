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

## Sound — music is the hero; always use `music.py`
- Pick the music with `music.random_song(seed, avoid=recent_recipes, ...)` or `music.Song.from_genre(<genre>, seed)`. 20 genres are built in (lofi, synthwave, ambient, musicbox, chiptune, citypop, bossa, cinematic, celtic, japanese, desert, kpop_bright, jazzhop, dreamwave, waltz, gamelan, trance_lite, tropical, lullaby, space); each randomises bpm, key, mode, progression, chord voicing, lead instrument (14 voices), melody style (arp / motif / walk / call-and-response), melody scale (incl. pentatonic, in, hirajoshi, whole-tone, blues), drums, texture, 3/4 or 4/4, swing and an optional key lift at the climax.
- Events are snapped to the tempo grid and harmonised, so dense moments become fast melodies, never noise. Drums and texture arrive as the build rises — pass a `build` curve that matches the visual tension.
- Land the payoff on the beat: when the burst/climax condition is met, trigger it at `song.next_bar(t)` and call `song.accent(...)` there.
- Quiet and pleasant: render peaks at -6 dBFS (default). Never use existing songs or melodies.
- Theme days pick a fitting genre: New Year → kpop_bright/trance_lite; Lunar New Year → gamelan; Valentine's → citypop/lofi; St. Patrick's → celtic; Easter → lullaby; Earth Day → ambient; Chuseok → japanese/ambient; Halloween → desert/cinematic (minor); Thanksgiving → bossa/jazzhop; Christmas → musicbox/waltz.
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
## Seasonal themes — ONLY on the exact day (check the PUBLISH date, KST)
A theme is a layer on top of any concept family: ball skin (`neon.SkinSprites(..., skin=...)`), palette, music mood, plus a matching hashtag/caption line. Physics stays the same. Apply it ONLY when the publish date IS the day itself — never the days before or after, and no season-long themes. For movable dates, verify the exact date for that year with a quick web search.
| Day | Theme | Skin(s) | Palette / music |
|---|---|---|---|
| Jan 1 | New Year | firework, star | gold + white (mono-ice, gold accent); bright major, bell lead |
| Lunar New Year's Day (2027-02-06) | Lunar New Year | lantern, firework | red + gold; major pentatonic feel, pluck/bell |
| Feb 14 | Valentine's Day | heart | pink/red (synthwave/sunset); slow ep, major |
| Mar 17 | St. Patrick's Day | clover | greens (aurora); bright major, marimba |
| Easter Sunday (2027-03-28) | Easter | egg | pastels; light major, marimba/pluck |
| Apr 22 | Earth Day | earth | ocean; calm major, bell |
| Mid-Autumn / Chuseok day (2027-09-15) | Full moon | moon, lantern | deep blue + gold; dorian, bell |
| Oct 31 | Halloween | pumpkin | orange + purple; minor/dorian, marimba/bell, a little spooky |
| US Thanksgiving (4th Thu of Nov; 2026-11-26) | Thanksgiving | leaf | warm sunset; cosy major, ep |
| Dec 25 | Christmas | ornament, snowflake, star | red/green/gold or mono-ice; bell lead, major/lydian |
Every other day uses the default `orb` skin. Theme days do not count against the concept-family balance rules. Never use characters, logos or brands.

## Music must be different every time
- Log `song.recipe_str()` in the Music column of concepts.md.
- Never reuse a genre that appears in the last 7 videos; never repeat the same genre + key + mode + lead within 30 days (`random_song` enforces both when you pass the recent recipes).
- Change at least two of bpm / key / mode / lead vs the previous video and keep bpm at least 6 away.
- If a genre clearly performs well, it may come back after 7 days, with a different key, mode and lead.
## Posting
- Metricool brand blogId `8158935`, timezone Asia/Seoul. Publish 08:00 KST.
- One scheduled post per network so hashtags differ:
  - YouTube: type `short`, madeForKids false, title ends with `#shorts`; hashtags `#shorts #satisfying #physics #simulation #oddlysatisfying`
  - TikTok: hashtags `#fyp #satisfying #physics #simulation #oddlysatisfying #asmr`
  - Instagram: type `REEL`; hashtags `#reels #satisfying #physics #simulation #oddlysatisfying #asmr`
- Media URL: `https://raw.githubusercontent.com/toomanyball9-collab/physics-shorts/main/videos/<file>.mp4`
