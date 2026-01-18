#!/bin/bash

# Kill Zombie Python Processes
echo "Searching for stuck Python processes..."

# Find python processes that are NOT the current script and NOT the VS Code language server extensions
# We look for "multiprocessing" spawn processes or just general loose python scripts
# Be careful not to kill the main app if it's running legitimately, but for now we want to clean up

# Kill the specific zombie we found earlier if it exists
if ps -p 6475 > /dev/null; then
    echo "Killing known zombie PID 6475..."
    kill -9 6475
fi

# Find and kill other potential zombies (careful approach)
# Look for "multiprocessing.spawn" which is a strong indicator of a stuck worker
pids=$(ps aux | grep "multiprocessing.spawn" | grep -v grep | awk '{print $2}')

if [ -n "$pids" ]; then
    echo "Found stuck multiprocessing workers: $pids"
    echo "$pids" | xargs kill -9
    echo "Killed."
else
    echo "No other stuck multiprocessing workers found."
fi

echo "Cleanup complete."
