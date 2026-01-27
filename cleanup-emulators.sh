#!/bin/bash
# Cleanup script to kill leftover Firebase emulator processes

echo "Cleaning up Firebase emulator processes..."

# Kill Java processes on emulator ports
for port in 8080 8085 9090 4000 5001 9199 9099; do
    pid=$(lsof -ti :$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)"
        kill -9 $pid 2>/dev/null
    fi
done

# Kill any remaining firebase processes
pkill -9 firebase 2>/dev/null

# Kill any Java processes that might be emulator-related
# (Be careful - this might kill other Java processes)
java_pids=$(pgrep -f "firebase.*emulator" 2>/dev/null)
if [ ! -z "$java_pids" ]; then
    echo "Killing Firebase emulator Java processes..."
    kill -9 $java_pids 2>/dev/null
fi

echo "Cleanup complete!"
echo ""
echo "To start emulators, run: npm run emulators"
