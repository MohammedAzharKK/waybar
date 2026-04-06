#!/bin/bash

# Get active workspace info from Hyprland
active_ws=$(hyprctl activeworkspace -j)
id=$(echo "$active_ws" | jq -r '.id')
name=$(echo "$active_ws" | jq -r '.name')

# Get CPU usage for "revving" effect
cpu_usage=$(grep 'cpu ' /proc/stat | awk '{print ($2+$4)*100/($2+$4+$5)}' | cut -d. -f1)

gears=("R" "N" "1" "2" "3" "4" "5" "6")

# Dynamic Colors based on "RPM" (CPU Usage)
if [[ $cpu_usage -gt 70 ]]; then
    ACTIVE_COLOR="#f38ba8" # High RPM Red
elif [[ $cpu_usage -gt 30 ]]; then
    ACTIVE_COLOR="#fab387" # Mid RPM Orange
else
    ACTIVE_COLOR="#f9e2af" # Low RPM Yellow
fi

R_COLOR="#f38ba8"
N_COLOR="#94e2d5"
D_COLOR="#89b4fa"

output="󱊟 <span color='#585b70'>[</span>"
for i in "${!gears[@]}"; do
    gear="${gears[$i]}"
    is_active=false
    
    case "$gear" in
        "R")
            if [[ "$name" == special:* ]]; then is_active=true; fi
            color=$R_COLOR
            ;;
        "N")
            # Neutral if no windows are open in current workspace
            windows=$(echo "$active_ws" | jq -r '.windows')
            if [[ "$windows" -eq 0 && ! "$name" == special:* ]]; then is_active=true; fi
            color=$N_COLOR
            ;;
        *)
            if [[ "$id" == "$gear" && "$name" != special:* ]]; then 
                # Only active if windows are present
                windows=$(echo "$active_ws" | jq -r '.windows')
                if [[ "$windows" -gt 0 ]]; then is_active=true; fi
            fi
            color=$D_COLOR
            ;;
    esac

    if $is_active; then
        output+="<span color='$ACTIVE_COLOR'><b>$gear</b></span>"
    else
        output+="<span color='$color'>$gear</span>"
    fi
    
    if [[ $i -lt $((${#gears[@]} - 1)) ]]; then
        output+="<span color='#45475a'>·</span>"
    fi
done
output+="<span color='#585b70'>]</span>"

echo "$output"
