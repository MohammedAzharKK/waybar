#!/usr/bin/env python3
import json
import urllib.request
import sys

def get_weather():
    try:
        # Get just the temperature string from wttr.in
        with urllib.request.urlopen("https://wttr.in/?format=%t") as url:
            temp = url.read().decode().strip()
            # wttr.in might return "+24°C" or "-5°C"
            return {"text": f" {temp}", "tooltip": "Click for Dashboard"}
    except Exception:
        return {"text": " Weather", "tooltip": "Could not fetch weather"}

if __name__ == "__main__":
    print(json.dumps(get_weather()))
