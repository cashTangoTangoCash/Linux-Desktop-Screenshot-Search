#!/usr/bin/env bash

# Replace these 4 values with your measurements from GIMP

CROP_W=1603
CROP_H=31
CROP_X=323
CROP_Y=56

INPUT_IMAGE="/home/dad84/Documents/2026/screenshots/test4/craigslist/2026-01-21-10:19-52_2560x1440.jpg"

# Execute pre-processing + OCR pipeline
# convert "$INPUT_IMAGE" \
#     -crop "${CROP_W}x${CROP_H}+${CROP_X}+${CROP_Y}" +repage \
#     -colorspace Gray \
#     -resize 200% \
#     -contrast-stretch 0x50% \
#     tif:- | tesseract stdin stdout --dpi 300

magick "$INPUT_IMAGE" \
    -crop "${CROP_W}x${CROP_H}+${CROP_X}+${CROP_Y}" +repage \
    -colorspace Gray \
    -resize 200% \
    tif:- | tesseract stdin stdout --dpi 300
