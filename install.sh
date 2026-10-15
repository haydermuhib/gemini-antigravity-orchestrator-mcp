#!/usr/bin/env bash
# Antigravity MCP Orchestrator - Setup script for Linux, macOS, and Windows (WSL/Bash)

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Antigravity MCP Orchestrator - Installer${NC}"
echo "--------------------------------------------------"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS="$(uname -s)"
ARCH="$(uname -m)"

echo -e "[INFO] Directory: ${YELLOW}${REPO_DIR}${NC}"
echo -e "[INFO] Platform:  ${YELLOW}${OS} (${ARCH})${NC}"

# Check Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] python3 is not installed.${NC}"
    echo "Install Python 3.10 or higher to proceed."
    exit 1
fi

PYTHON_VALID=$(python3 -c "import sys; print('yes' if sys.version_info >= (3, 10) else 'no')")
if [ "$PYTHON_VALID" != "yes" ]; then
    echo -e "${RED}[ERROR] Python 3.10 or higher is required. Found: $(python3 --version)${NC}"
    exit 1
fi
echo -e "[OK]   Python:    ${GREEN}$(python3 --version)${NC}"

# Check cloudflared
if command -v cloudflared &> /dev/null; then
    echo -e "[OK]   Tunnel:    ${GREEN}$(cloudflared --version | head -n 1)${NC}"
else
    echo -e "${YELLOW}[WARN] cloudflared is not installed.${NC}"
    echo "cloudflared is required to create public HTTPS endpoints for Gemini Connected Apps."
    
    mkdir -p "$HOME/.local/bin"
    if [ "$OS" = "Linux" ] && [ "$ARCH" = "x86_64" ]; then
        echo "[INFO] Downloading cloudflared for Linux x86_64..."
        curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o "$HOME/.local/bin/cloudflared"
        chmod +x "$HOME/.local/bin/cloudflared"
        export PATH="$HOME/.local/bin:$PATH"
        echo -e "${GREEN}[OK]   Installed cloudflared to ~/.local/bin/cloudflared${NC}"
    elif [ "$OS" = "Darwin" ]; then
        echo -e "${YELLOW}[INFO] On macOS, install with:${NC} brew install cloudflared"
    else
        echo -e "${YELLOW}[INFO] Download cloudflared from: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-local-tunnel/${NC}"
    fi
fi

# Ensure executables have execute permissions
chmod +x "$REPO_DIR/server.py" \
         "$REPO_DIR/start_daemon.sh" \
         "$REPO_DIR/stop_daemon.sh" \
         "$REPO_DIR/status.sh"

# Install antigravity-mcp CLI wrapper
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
CLI_PATH="$BIN_DIR/antigravity-mcp"

cat << EOF > "$CLI_PATH"
#!/usr/bin/env bash
PROJECT_DIR="$REPO_DIR"
export PYTHONPATH="\$PROJECT_DIR:\$PYTHONPATH"

exec python3 "\$PROJECT_DIR/server.py" --workspace "\$PWD" "\$@"
EOF

chmod +x "$CLI_PATH"
echo -e "[OK]   CLI:       ${GREEN}${CLI_PATH}${NC}"

# Register in Antigravity IDE configuration if directory exists
CONFIG_DIR="$HOME/.gemini/config"
CONFIG_FILE="$CONFIG_DIR/mcp_config.json"

if [ -d "$CONFIG_DIR" ]; then
    echo "[INFO] Registering in Antigravity IDE configuration..."
    python3 - << PYEOF
import json
from pathlib import Path

config_path = Path("$CONFIG_FILE")
config_path.parent.mkdir(parents=True, exist_ok=True)

if config_path.is_file():
    try:
        data = json.loads(config_path.read_text())
    except Exception:
        data = {}
else:
    data = {}

if "mcpServers" not in data:
    data["mcpServers"] = {}

data["mcpServers"]["antigravity-orchestrator"] = {
    "command": "python3",
    "args": [
        "$REPO_DIR/server.py",
        "--stdio"
    ],
    "env": {
        "PYTHONUNBUFFERED": "1"
    },
    "disabled": False
}

config_path.write_text(json.dumps(data, indent=2))
print("[OK]   Antigravity IDE configuration updated.")
PYEOF
fi

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo -e "\n[NOTE] Add ~/.local/bin to PATH in your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo "--------------------------------------------------"
echo -e "${GREEN}Installation finished.${NC}"
echo "Start server:  antigravity-mcp start   (or ./start_daemon.sh)"
echo "Check status:  antigravity-mcp status  (or ./status.sh)"
echo "Stop server:   antigravity-mcp stop    (or ./stop_daemon.sh)"
echo "--------------------------------------------------"
