#!/bin/bash
SCRIPT_PATH="$(dirname "$(readlink -f "$0")")"
export DISPLAY=:1
export XAUTHORITY=$HOME/.Xauthority
source $SCRIPT_PATH/venv/bin/activate
$SCRIPT_PATH/wallpaper.py