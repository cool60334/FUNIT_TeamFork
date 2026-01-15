#!/bin/bash
# Ralph Loop Stop Hook
# Intercepts exit, checks for completion promise, and re-prompts if necessary.

STATE_FILE=".ralph_state"

# 1. Check if Ralph Loop is active
if [ ! -f "$STATE_FILE" ]; then
    exit 0
fi

# Load state
source "$STATE_FILE"

# 2. Capture Last Output (from Stdin)
# We try to read stdin to check for the completion promise.
# If stdin is empty, we might not be able to check, but we'll proceed.
if [ -t 0 ]; then
    # Stdin is a terminal, meaning no input piped.
    LAST_OUTPUT=""
else
    LAST_OUTPUT=$(cat)
fi

# 3. Check for Completion Promise
if [[ "$LAST_OUTPUT" == *"$COMPLETION_PROMISE"* ]]; then
    echo "✅ Ralph Loop: Completion promise '$COMPLETION_PROMISE' verified."
    rm "$STATE_FILE"
    exit 0
fi

# 4. Increment Iteration
CURRENT_ITERATION=$((CURRENT_ITERATION + 1))

# Check max iterations
if [ "$MAX_ITERATIONS" != "unlimited" ] && [ "$CURRENT_ITERATION" -ge "$MAX_ITERATIONS" ]; then
    echo "🛑 Ralph Loop: Max iterations ($MAX_ITERATIONS) reached. Stopping loop."
    rm "$STATE_FILE"
    exit 0
fi

# Update state
cat <<EOF > "${STATE_FILE}.tmp"
PROMPT="$PROMPT"
MAX_ITERATIONS="$MAX_ITERATIONS"
COMPLETION_PROMISE="$COMPLETION_PROMISE"
CURRENT_ITERATION=$CURRENT_ITERATION
EOF
mv "${STATE_FILE}.tmp" "$STATE_FILE"

# 5. Re-trigger Prompt
echo "🔄 Ralph Loop: Iteration $CURRENT_ITERATION/$MAX_ITERATIONS"
echo "Promise '$COMPLETION_PROMISE' not found. Re-submitting task..."
echo "---------------------------------------------------"
echo "$PROMPT"
echo "---------------------------------------------------"

# Exit with non-zero to block the session exit and keep the loop alive (if supported)
exit 1
