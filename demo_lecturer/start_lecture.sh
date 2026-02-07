#!/bin/bash
# ============================================================
# AI Lecture Generator - Start Lecture Player
# Usage: ./start_lecture.sh
# ============================================================

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Ports
WEB_PORT=8897
QA_PORT=5001

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}   🎓 AI Lecture Player - Starting Servers${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Activate virtual environment
source /mnt/data0/data0/sriprabha/srijan/gurukul_ss/bin/activate


# ------------------------------------------------------------
# Check Ollama
# ------------------------------------------------------------
echo -e "${YELLOW}Checking Ollama...${NC}"
if curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama is running${NC}"
else
    echo -e "${RED}❌ Ollama is NOT running.${NC}"
    echo -e "${YELLOW}Start it in another screen pane:${NC}"
    echo "  export CUDA_VISIBLE_DEVICES=6"
    echo "  export OLLAMA_MODELS=/data0/sriprabha/srijan/ollama/models"
    echo "  export OLLAMA_HOST=127.0.0.1:11434"
    echo "  ollama serve"
    exit 1
fi
echo ""

# ------------------------------------------------------------
# Start Q&A server (5001)
# ------------------------------------------------------------
echo -e "${YELLOW}Starting Q&A server on ${QA_PORT}...${NC}"
python qa_handler.py --server > qa_server.log 2>&1 &
QA_PID=$!
sleep 2

if ps -p $QA_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Q&A server running (PID: $QA_PID)${NC}"
else
    echo -e "${RED}❌ Q&A server failed to start${NC}"
    echo -e "${YELLOW}See qa_server.log for details.${NC}"
fi
echo ""

# ------------------------------------------------------------
# Start or detect Web server (8897)
# ------------------------------------------------------------
echo -e "${YELLOW}Checking web server on ${WEB_PORT}...${NC}"

PORT_IN_USE=$(python - <<PY
import socket
s = socket.socket()
try:
    s.bind(("127.0.0.1", int("${WEB_PORT}")))
    print("0")   # free
except OSError:
    print("1")   # in use
finally:
    s.close()
PY
)

if [ "$PORT_IN_USE" = "1" ]; then
    echo -e "${GREEN}✅ Web server already running on ${WEB_PORT}${NC}"
    WEB_PID=""
else
    echo -e "${YELLOW}Starting web server on ${WEB_PORT}...${NC}"
    python -m http.server ${WEB_PORT} --bind 127.0.0.1 > web_server.log 2>&1 &
    WEB_PID=$!
    sleep 1

    if ps -p $WEB_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Web server started (PID: $WEB_PID)${NC}"
    else
        echo -e "${RED}❌ Web server failed to start${NC}"
        echo -e "${YELLOW}See web_server.log for details.${NC}"
    fi
fi
echo ""


# ------------------------------------------------------------
# Save PIDs (only if started here)
# ------------------------------------------------------------
echo "$QA_PID" > .qa_server.pid
[ -n "$WEB_PID" ] && echo "$WEB_PID" > .web_server.pid

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 Lecture player is ready!${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "🌐 Player URL (via SSH tunnel): ${CYAN}http://127.0.0.1:${WEB_PORT}/output/dynamic_player.html${NC}"
echo -e "🤖 Q&A URL (via SSH tunnel):     ${CYAN}http://127.0.0.1:${QA_PORT}/${NC}"
echo ""
echo -e "To stop the servers, run: ${CYAN}./stop_lecture.sh${NC}"
echo ""

# ------------------------------------------------------------
# Graceful shutdown
# ------------------------------------------------------------
trap "echo ''; echo 'Stopping servers...'; \
      kill $QA_PID 2>/dev/null; \
      [ -n \"$WEB_PID\" ] && kill $WEB_PID 2>/dev/null; \
      rm -f .qa_server.pid .web_server.pid; \
      echo 'Goodbye! 👋'; exit 0" INT

# Keep running
while true; do
    sleep 1
done
