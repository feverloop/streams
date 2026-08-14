#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "requests",
#   "dnspython",
# ]
# ///
import sys
import argparse
import requests
import dns.resolver
from pathlib import Path
from urllib3.util.connection import create_connection as _create_connection

def custom_create_connection(address, *args, **kwargs):
    host, port = address
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ["1.1.1.1"]
        ip = str(resolver.resolve(host, "A")[0])
        return _create_connection((ip, port), *args, **kwargs)
    except Exception:
        return _create_connection(address, *args, **kwargs)

import urllib3.util.connection
urllib3.util.connection.create_connection = custom_create_connection

def test_url(url, timeout=5):
    try:
        # GET with a 1-byte range, not HEAD: Shoutcast rejects bare HEAD with 400.
        # stream=True + immediate close avoids pulling a live stream's infinite body.
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "VLC/3.0.0", "Range": "bytes=0-0"},
            allow_redirects=True,
            stream=True,
        )
        resp.close()
        if resp.status_code in (200, 206):
            return True, None
        return False, f"HTTP {resp.status_code}"
    except requests.exceptions.InvalidURL:
        return False, "INVALID_URL"
    except requests.Timeout:
        return False, "TIMEOUT"
    except requests.ConnectionError as e:
        if "Name or service not known" in str(e):
            return False, "DNS_ERROR"
        return False, "CONNECTION_ERROR"
    except requests.RequestException as e:
        return False, type(e).__name__

def filter_m3u(input_file, output_file=None, keep_failed=False):
    if output_file is None:
        output_file = f"filtered-{Path(input_file).name}"

    extinf = None
    with open(input_file) as f, open(output_file, 'w') as out:
        for line in f:
            line = line.rstrip()

            if line.startswith("#EXTINF"):
                extinf = line
            elif line.startswith("http"):
                ok, reason = test_url(line)
                if ok:
                    if extinf:
                        out.write(extinf + "\n")
                    out.write(line + "\n")
                    print(f"[OK] {line}")
                elif keep_failed:
                    out.write(f"# [{reason}] Failed\n")
                    out.write(extinf.replace("#EXTINF", "##EXTINF") + "\n")
                    out.write(f"# {line}\n")
                    print(f"[{reason}] {line}")
                else:
                    print(f"[SKIP] {line}")
                extinf = None
            elif line.startswith("#"):
                out.write(line + "\n")
            elif line:
                extinf = None

    print(f"\nOutput: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter reachable streams from M3U playlists")
    parser.add_argument("input", help="Input .m3u file")
    parser.add_argument("-o", "--output", help="Output file (default: filtered-<input>)")
    parser.add_argument("--keep-failed", action="store_true", help="Comment out failed entries instead of discarding")
    args = parser.parse_args()

    filter_m3u(args.input, args.output, args.keep_failed)
