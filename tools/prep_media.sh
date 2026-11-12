#!/usr/bin/env bash
# Builds the media folder used by the phones video from the original press files.
# The originals (Apple Newsroom, Samsung Newsroom) are not stored in the repository.
#   tools/prep_media.sh <folder with the original files> <output folder>
set -euo pipefail
SRC="$1"; OUT="$2"
mkdir -p "$OUT"
# photos are copied as they are
cp "$SRC"/apple_colors_*.jpg "$OUT/apple_colors.jpg"
cp "$SRC"/apple_2up_*.jpg "$OUT/apple_2up.jpg"
cp "$SRC"/samsung_images_Galaxy-S26Ultra_Family-scaled.jpg "$OUT/samsung_family.jpg"
cp "$SRC"/samsung_images_Galaxy-S26UltraBuds4-Pr0Buds4-scaled.jpg "$OUT/samsung_buds.jpg"
# clips become numbered JPEG frames (the page shows one frame per video frame)
frames() { # name file seconds
  mkdir -p "$OUT/$1"
  ffmpeg -y -loglevel error -t "$3" -i "$2" -vf "fps=30,scale=1920:1080:flags=lanczos" -q:v 3 "$OUT/$1/%04d.jpg"
}
frames vapor   "$(ls "$SRC"/apple_vapor_*.mp4)"  14
frames camera  "$(ls "$SRC"/apple_camera_*.mp4)" 10
frames privacy "$SRC/samsung_privacy.mp4"        17
echo "media ready in $OUT"; du -sh "$OUT"; for d in vapor camera privacy; do echo "$d: $(ls "$OUT/$d" | wc -l) frames"; done
