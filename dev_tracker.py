#!/usr/bin/env python3
import os
import subprocess
import json
import time
from datetime import datetime

# Configuration
IDES = ["antigravity", "code", "vscodium", "nvim", "pycharm", "subl", "emacs", "zed"]
REPOS_SEARCH_PATH = os.path.expanduser("~")
SEARCH_DEPTH = 5

def get_coding_time():
    """
    Calculates coding time today by checking the start time of IDE processes.
    This is an approximation based on process uptime since today's start.
    """
    total_seconds = 0
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    try:
        # ps -e -o comm,lstart returns process name and start time
        output = subprocess.check_output(["ps", "-e", "-o", "comm,lstart"], stderr=subprocess.DEVNULL).decode()
        lines = output.strip().split("\n")[1:] # Skip header
        
        # We want to count each unique IDE once (the earliest start time today)
        # or sum up if there are multiple different IDEs.
        ide_starts = {}
        
        for line in lines:
            parts = line.split()
            if not parts: continue
            
            comm = parts[0]
            # ps lstart format: Day Mon Date hh:mm:ss Year
            # e.g., Mon Apr  6 17:00:00 2026
            lstart_str = " ".join(parts[1:])
            
            if any(ide in comm.lower() for ide in IDES):
                try:
                    start_time = datetime.strptime(lstart_str, "%a %b %d %H:%M:%S %Y")
                    # Only count if it started today
                    if start_time >= today_start:
                        if comm not in ide_starts or start_time < ide_starts[comm]:
                            ide_starts[comm] = start_time
                except Exception:
                    continue
        
        for comm, start_time in ide_starts.items():
            duration = (now - start_time).total_seconds()
            total_seconds += duration
            
    except Exception:
        pass
        
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f"{hours}h {minutes}m"

def get_git_commits():
    """
    Counts git commits made today across local repositories.
    """
    total_commits = 0
    
    try:
        # Find all .git directories excluding heavy noise directories
        find_cmd = [
            "find", REPOS_SEARCH_PATH, "-maxdepth", str(SEARCH_DEPTH),
            "(", "-name", ".cache", "-o", "-name", ".local", "-o", "-name", ".pub-cache", "-o", "-name", "node_modules", ")", "-prune",
            "-o", "-name", ".git", "-type", "d", "-print"
        ]
        
        result = subprocess.run(find_cmd, capture_output=True, text=True)
        repos = result.stdout.strip().split("\n")
        
        if not repos or repos == ['']:
            return 0
            
        for git_dir in repos:
            if not git_dir: continue
            repo_path = os.path.dirname(git_dir)
            try:
                # Count all commits in the repo since today 00:00:00
                commit_count = subprocess.check_output(
                    ["git", "-C", repo_path, "rev-list", "--count", "--since", "00:00:00", "--all", "--no-merges"],
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                
                if commit_count:
                    total_commits += int(commit_count)
            except Exception:
                continue
    except Exception:
        pass
        
    return total_commits

def main():
    coding_time = get_coding_time()
    commits = get_git_commits()
    
    # Premium icons: ⏱ (Coding Time), 🧠 (Commits)
    # Using Nerd Font icons compatible with system's style: 󱎫 (Timer), 󰊢 (Git)
    text = f"󱎫 {coding_time}  󰊢 {commits}"
    tooltip = f"Coding Activity Today\n-------------------\n⏱ Time: {coding_time}\n󰊢 Commits: {commits}"
    
    print(json.dumps({
        "text": text,
        "tooltip": tooltip,
        "class": "productivity"
    }))

if __name__ == "__main__":
    main()
