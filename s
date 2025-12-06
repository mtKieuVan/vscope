#!/bin/bash

# Get the directory of the current script
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# Execute s.py using python, passing all arguments
python "$SCRIPT_DIR/s.py" "$@"

