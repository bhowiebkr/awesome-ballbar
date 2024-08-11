#!/bin/bash

# Get the current directory (where the script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define the path to your virtual environment (assumed to be in the current directory)
VENV_PATH="$SCRIPT_DIR/venv"

# Source the virtual environment
source "$VENV_PATH/bin/activate"

# Run the Python script
python awesome_ballbar.py

# Deactivate the virtual environment after the script finishes
deactivate
