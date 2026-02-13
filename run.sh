#!/bin/bash

# Activate virtual environment
source "/home/cpx003/vst_gm_control_panel/vst_venv/bin/activate"
# 
# VST Green Machine Control Panel Launcher
#
# This script launches the application with display settings configured and
# from the correct directory to ensure all paths work properly.
#

# Set display to primary monitor
export DISPLAY=:0.0

# Change to the application directory
cd vst_gm_control_panel

# Check for developer mode flag
if [[ "$1" == "--dev" || "$1" == "-d" ]]; then
    echo "Running in developer mode..."
    python3 main.py --developer
    exit $?
fi

# Check for specific screen to start on
if [[ "$1" == "--screen" || "$1" == "-s" ]]; then
    if [[ -n "$2" ]]; then
        echo "Starting with screen: $2"
        python3 main.py --screen "$2"
        exit $?
    else
        echo "Error: Screen name required with --screen option"
        exit 1
    fi
fi

# Default run with no arguments
echo "Starting Green Machine Control Panel..."
python3 main.py "$@"
