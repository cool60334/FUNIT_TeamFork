#!/bin/bash

# Ralph Loop Initialization Script
# Usage: ./scripts/ralph_loop.sh "Your prompt" --max-iterations 10 --completion-promise "DONE"

PROMPT=""
MAX_ITERATIONS="unlimited"
COMPLETION_PROMISE="DONE"

# Parse args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --max-iterations) MAX_ITERATIONS="$2"; shift ;;
        --completion-promise) COMPLETION_PROMISE="$2"; shift ;;
        *) 
            if [ -z "$PROMPT" ]; then
                PROMPT="$1"
            else
                echo "Unknown parameter: $1"
                exit 1
            fi
            ;;
    esac
    shift
done

if [ -z "$PROMPT" ]; then
    echo "Error: No prompt provided."
    echo "Usage: $0 \"prompt\" [--max-iterations N] [--completion-promise PROMISE]"
    exit 1
fi

# Save state
cat <<EOF > .ralph_state
PROMPT="$PROMPT"
MAX_ITERATIONS="$MAX_ITERATIONS"
COMPLETION_PROMISE="$COMPLETION_PROMISE"
CURRENT_ITERATION=0
EOF

echo "Ralph Loop initialized."
echo "Prompt: $PROMPT"
echo "Max Iterations: $MAX_ITERATIONS"
echo "Completion Promise: $COMPLETION_PROMISE"
echo "Sending initial prompt to agent..."
echo "$PROMPT"
