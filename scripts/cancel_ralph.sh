#!/bin/bash

if [ -f .ralph_state ]; then
    rm .ralph_state
    echo "Ralph Loop canceled. State file removed."
else
    echo "No active Ralph Loop found."
fi
