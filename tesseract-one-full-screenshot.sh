#!/usr/bin/env bash

INPUT_IMAGE="/home/dad84/Documents/2026/screenshots/test5/2026-08-01-21:00-28_2560x1380.jpg"

magick "$INPUT_IMAGE" \
    -colorspace Gray \
    -resize 200% \
    tif:- | tesseract stdin stdout --dpi 300
