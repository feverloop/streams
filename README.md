# streams

Curated, empirically verified internet-radio stream playlists in M3U format.

Every URL here was confirmed live at the date noted in its section — HTTP 200
plus `ffprobe` on real fetched bytes (a segment for HLS, a range request for
Icecast), not just "the URL looks right" or copied from a third-party list.

## Layout

Playlists are grouped by broadcaster/provider, one directory per provider,
one `.m3u` per station family:

```
radiofrance/
  fip.m3u        # FIP main + 10 themed channels
bassdrive/
  bassdrive.m3u  # Bassdrive - highest-bitrate mirrors
```

## Format convention

Extended M3U (`#EXTM3U`), one `#EXTINF` line per stream:

```
#EXTINF:-1,<Station> <Channel> - <optional genre note> (<bitrate> <codec/transport>)
<url>
```

- Duration is always `-1` — these are continuous live streams.
- Each channel appears **once per available quality tier**, so a player can
  offer the choice rather than the playlist picking one:
  - direct MP3 Icecast mounts — play in anything, including dumb hardware
    players and minimal embedded clients
  - HLS (`.m3u8`) — higher bitrate, needs an HLS-capable player (VLC, mpv,
    ffmpeg-backed clients; many simple players will not handle these)
- Genre notes are appended only where the channel name alone is unclear to a
  non-French speaker (e.g. `FIP Monde - World music`).

## Verification

To re-check a playlist before trusting it:

```bash
# Icecast MP3 mount: expect 200 + icy-br + audio/mpeg
curl -sA "Mozilla/5.0" -m 5 -D - -o /dev/null -r 0-0 "<mp3-url>" \
  | grep -i "^HTTP/\|^icy-\|^content-type"

# HLS: pull one segment, measure the real encoded bitrate
curl -sA "Mozilla/5.0" "<m3u8-url>" | grep -m1 '^/'
curl -sA "Mozilla/5.0" -o seg.ts "https://<host><path-from-above>"
ffprobe -v error -select_streams a \
  -show_entries stream=codec_name,sample_rate,bit_rate \
  -of default=noprint_wrappers=1 seg.ts
```

Note on HLS bitrate: do not derive it from `Content-Length / duration` — the
`.ts` segment container adds roughly 25% overhead over the raw audio and will
overstate the rate. Use `ffprobe`'s per-stream `bit_rate`.

## Tools

`tools/` — scripts to re-check a playlist's reachability before trusting it.
Both use GET with a 1-byte range, not HEAD (Shoutcast rejects bare HEAD with
400), and stop reading after the response headers arrive rather than
downloading a live stream's body (most Shoutcast mounts ignore `Range` and
just keep streaming, so a naive full-body GET would hang until timeout).

- `tools/filter-streams.py` — `uv run tools/filter-streams.py <input.m3u>
  [-o output.m3u] [--keep-failed]`. Self-installs deps via inline `uv`
  script metadata (`requests`, `dnspython`), no venv setup needed. Pins DNS
  resolution to `1.1.1.1`. Default drops unreachable entries; `--keep-failed`
  keeps them, commented out with a reason (`HTTP <code>`, `TIMEOUT`,
  `DNS_ERROR`, `CONNECTION_ERROR`, `INVALID_URL`).
- `tools/filter-streams.sh` — `tools/filter-streams.sh <input.m3u>
  [output.m3u]`. Simpler bash/curl equivalent: OK/SKIP only, no
  reason-tagging, no DNS override, drops failed entries silently.

## Playlists

### `radiofrance/fip.m3u`

FIP (Radio France) — main station plus 10 themed channels: Rock, Jazz, Groove,
Monde, Nouveautés, Reggae, Pop, Électro, Hip-Hop, Metal. 22 entries (11
channels × 2 quality tiers). Verified 2026-07-28.

- **128k MP3** — `http://icecast.radiofrance.fr/<slug>-midfi.mp3`. This is the
  quality ceiling for plain MP3; no `-hifi.mp3` / `-lofi.mp3` mounts exist
  (all 404).
- **192k AAC HLS** — `https://stream.radiofrance.fr/<slug>/<slug>_hifi.m3u8`,
  measured ~194.5–194.8 kbps AAC, 48 kHz stereo.

The `direct.fipradio.fr/live/*.mp3` URLs commonly found in other lists are an
alias layer that 301-redirects to these Icecast mounts; the direct mounts are
used here instead. Not every channel has an alias — FIP Metal has none.

Caveats worth knowing if you edit this file:

- `_midfi.m3u8` (HLS, ~96 kbps) and `-midfi.mp3` (Icecast, 128 kbps) are
  **different streams** despite the shared "midfi" label. Do not conflate them.
- `_lofi.m3u8` variants exist (~32–35 kbps) but are excluded as too low to be
  useful.
- `icecast.radiofrance.fr/status-json.xsl` returns 403, so mounts cannot be
  enumerated from a directory listing — new channels have to be found by
  probing the slug guessed from the channel's French name.

### `bassdrive/bassdrive.m3u`

Bassdrive (bassdrive.com) — single station, no themed sub-channels. Two
mirrors at the quality ceiling, kept both for failover. Verified 2026-08-14.

- **192k MP3** — `http://chi.bassdrive.co:80` (Chicago) and
  `http://au.bassdrive.co:8000` (Australia). Highest bitrate offered.

Other mirrors/tiers exist but are excluded as below the ceiling: `icecast
ice.bassdrive.net:80/stream` (128k MP3), `bassdrive.radioca.st:8702` (128k
MP3), `stream.bassdrive.uk:8200` (128k MP3), `ice.bassdrive.net:80/stream56`
and `/stream32` (56k/32k AAC+, for low-bandwidth listening).

The site's `bassdrive.m3u`/`bassdrive3.m3u`/`bassdrive6.m3u` playlist files
(linked from bassdrive.com/radio) resolve to `ice.bassdrive.net` mounts only —
the higher-bitrate regional mirrors used here aren't linked from the site and
were found by testing known Bassdrive mirror hostnames directly with
`icy-br`/`curl -I` probes.
