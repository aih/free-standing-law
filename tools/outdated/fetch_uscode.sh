#!/usr/bin/env bash
# Download OLRC's USLM for every title at a release point and unzip it into data/uscode/xml.
# Usage: bash tools/outdated/fetch_uscode.sh 119-138
# The release point 119-138 zip had sha256
# 763c3ddf5668c42ba8b138b764c8e80942766af7f18d20fcef8c706faf09e152 (108,702,539 bytes) on 2026-11-12.
set -euo pipefail
rp="${1:?release point, for example 119-138}"
root="$(cd "$(dirname "$0")/../.." && pwd)"
congress="${rp%%-*}"; law="${rp#*-}"
zip="$root/data/uscode/xml_uscAll@$rp.zip"
mkdir -p "$root/data/uscode"
if [ ! -f "$zip" ]; then
  curl -fsSL -A "free-standing-law-research/0.1" -o "$zip" \
    "https://uscode.house.gov/download/releasepoints/us/pl/$congress/$law/xml_uscAll@$rp.zip"
fi
if [ "$rp" = "119-138" ]; then
  echo "763c3ddf5668c42ba8b138b764c8e80942766af7f18d20fcef8c706faf09e152  $zip" | sha256sum -c -
fi
rm -rf "$root/data/uscode/xml"
unzip -q "$zip" -d "$root/data/uscode/xml"
echo "unzipped to $root/data/uscode/xml"
