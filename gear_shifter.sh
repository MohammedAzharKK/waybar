#!/bin/bash

# Get active workspace info from Hyprland
active_ws=$(hyprctl activeworkspace -j)
id=$(echo "$active_ws" | jq -r '.id')
name=$(echo "$active_ws" | jq -r '.name')

# Define the shifter layout
gears=("R" "N" "1" "2" "3" "4" "5" "6")

output="["
for i in "${!gears[@]}"; do
    gear="${gears[$i]}"
    is_active=false
    
    case "$gear" in
        "R")
            if [[ "$name" == special:* ]]; then is_active=true; fi
            ;;
        "N")
            # Active if id is not 1-6 and not special
            if [[ ! "$id" =~ ^[1-6]$ && ! "$name" == special:* ]]; then is_active=true; fi
            ;;
        *)
            if [[ "$id" == "$gear" ]]; then is_active=true; fi
            ;;
    esac

    if $is_active; then
        output+="<span color='#f38ba8'><b>$gear</b></span>"
    else
        output+="$gear"
    fi
    
    if [[ $i -lt $((${#gears[@]} - 1)) ]]; then
        output+=" "
    fi
done
output+="]"

echo "$output"
