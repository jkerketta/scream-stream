#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🔄 Resetting and restarting all servers..."
echo ""

echo "🛑 Stopping existing processes..."
pkill -f "tongue_detection" 2>/dev/null
pkill -f "http.server" 2>/dev/null
sleep 2

lsof -ti:8765,8000 2>/dev/null | xargs kill -9 2>/dev/null
echo "✅ Ports cleared"

rm -f /tmp/tongue_detection.log /tmp/webserver.log 2>/dev/null

echo ""
echo "🚀 Starting fresh servers..."
echo ""

echo "📹 Starting head tilt detection server (port 8765)..."
python3 tongue_detection_simple.py > /tmp/tongue_detection.log 2>&1 &
DETECTION_PID=$!
echo "   PID: $DETECTION_PID"
sleep 3

if ps -p $DETECTION_PID > /dev/null; then
    echo "   ✅ Detection server is running"
else
    echo "   ❌ Detection server failed to start"
    echo "   Check logs: tail -f /tmp/tongue_detection.log"
fi

echo ""
echo "🌐 Starting web server (port 8000)..."
python3 -m http.server 8000 > /tmp/webserver.log 2>&1 &
WEB_PID=$!
echo "   PID: $WEB_PID"
sleep 1

if ps -p $WEB_PID > /dev/null; then
    echo "   ✅ Web server is running"
else
    echo "   ❌ Web server failed to start"
    echo "   Check logs: tail -f /tmp/webserver.log"
fi

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "📹 Head Tilt Detection: http://localhost:8765 (WebSocket)"
echo "🌐 Web Server: http://localhost:8000"
echo ""
echo "🌍 Open in browser:"
echo "   http://localhost:8000/index.html"
echo ""
echo "📝 View logs:"
echo "   Detection: tail -f /tmp/tongue_detection.log"
echo "   Web: tail -f /tmp/webserver.log"
echo ""
echo "🛑 To stop servers:"
echo "   kill $DETECTION_PID $WEB_PID"
echo "   OR: ./stop_servers.sh"
echo ""

