#!/bin/bash
# ============================================================
# AI Lecture Generator - Stop All Servers
# Usage: ./stop_lecture.sh
# ============================================================

echo ""
echo "🛑 Stopping lecture servers..."

# Kill by PID files if they exist
if [ -f .qa_server.pid ]; then
    kill $(cat .qa_server.pid) 2>/dev/null
    rm .qa_server.pid
fi

if [ -f .web_server.pid ]; then
    kill $(cat .web_server.pid) 2>/dev/null
    rm .web_server.pid
fi

# Also kill by port (backup method)
lsof -ti:5001 | xargs kill -9 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null

echo "✅ All servers stopped"
echo ""
