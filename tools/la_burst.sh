#!/bin/sh
# Capture N bursts of 6000 samples at 48 MHz (all 8 channels) into captures/NAME/burst_NN.sr, with a pause between runs
# (the FX2 needs about 3 s to re-enumerate). PulseView must be closed. Usage: tools/la_burst.sh NAME [N]
name=${1:?usage: la_burst.sh NAME [N]}; n=${2:-24}
cd "$(dirname "$0")/.." || exit 1
mkdir -p "captures/$name"
i=1
while [ "$i" -le "$n" ]; do
    sleep 3
    sigrok-cli --driver fx2lafw --config samplerate=48m --samples 6000 -o "captures/$name/burst_$(printf %02d "$i").sr" 2>&1 | tail -1
    i=$((i + 1))
done
ls "captures/$name" | wc -l
