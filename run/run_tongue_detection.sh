#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🚀 Starting Tongue Detection System..."
echo ""

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "📦 Checking dependencies..."
python3 -c "import cv2, mediapipe, websockets" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📥 Installing required packages..."
    pip3 install opencv-python mediapipe websockets
fi

echo "✅ Dependencies ready!"
echo ""
echo "🎬 Starting tongue detection server..."
echo "   - WebSocket server will run on ws://localhost:8765"
echo "   - Camera window will open"
echo "   - Press 'q' to quit"
echo ""

python3 tongue_detection_simple.py

