#!/bin/bash
# Waybar Widget Toggle Script

SCRIPT_NAME=$1
SCRIPT_PATH="/home/azhar/.config/waybar/$SCRIPT_NAME"
PATTERN="python3 $SCRIPT_PATH"

# Check if the script is already running
if pgrep -f "$PATTERN" > /dev/null; then
    # Kill existing instances
    pkill -f "$PATTERN"
else
    # Start a new instance
    python3 "$SCRIPT_PATH" &
fi
