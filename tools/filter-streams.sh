#!/bin/bash
# Filter reachable streams from m3u playlist

INPUT="${1:?usage: $0 input.m3u [output.m3u]}"
OUTPUT="${2:-filtered-$(basename "$INPUT")}"

> "$OUTPUT"

while IFS= read -r line; do
  if [[ "$line" == "#EXTINF"* ]]; then
    echo "$line" >> "$OUTPUT"
  elif [[ "$line" == "http"* ]]; then
    # GET, not HEAD: Shoutcast rejects bare HEAD with 400. Most Shoutcast
    # mounts ignore Range (Accept-Ranges:none) and just keep streaming, so
    # -o /dev/null would download the live stream until curl's own timeout
    # fires and reports failure even on a healthy 200. Check the captured
    # status line instead of curl's exit code, so a mid-download timeout on
    # an already-200 stream still counts as reachable.
    if timeout 5 curl -s -m 5 -L -r 0-0 -D - -o /dev/null -H "User-Agent: VLC/3.0.0" "$line" 2>/dev/null \
      | grep -qE "^HTTP/[0-9.]+ (200|206) "; then
      echo "$line" >> "$OUTPUT"
      echo "[OK] $line"
    else
      echo "[SKIP] $line"
    fi
  elif [[ -z "$line" ]]; then
    echo "" >> "$OUTPUT"
  else
    echo "$line" >> "$OUTPUT"
  fi
done < "$INPUT"

echo ""
echo "Output: $OUTPUT"
