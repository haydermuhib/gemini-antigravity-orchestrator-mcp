#!/usr/bin/env bash
# ==============================================================================
# Antigravity MCP Orchestrator - Installer for Linux, macOS & Windows (WSL/Bash)
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛸 Antigravity MCP Orchestrator Installer${NC}"
echo -e "=================================================="

# 1. Detect Environment & Directory
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS="$(uname -s)"
ARCH="$(uname -m)"

echo -e "📁 Installing from: ${YELLOW}${REPO_DIR}${NC}"
echo -e "💻 Platform:        ${YELLOW}${OS} (${ARCH})${NC}"

# 2. Check Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 is not installed.${NC}"
    echo "Please install Python 3.10 or higher for your system."
    exit 1
fi

PYTHON_VALID=$(python3 -c "import sys; print('yes' if sys.version_info >= (3, 10) else 'no')")
if [ "$PYTHON_VALID" != "yes" ]; then
    echo -e "${RED}❌ Error: Python 3.10+ required. Found: $(python3 --version)${NC}"
    exit 1
fi
echo -e "🐍 Python:          ${GREEN}$(python3 --version)${NC}"

# 3. Check / Install cloudflared (for public HTTPS tunnel to Gemini)
if command -v cloudflared &> /dev/null; then
    echo -e "☁️  Cloudflared:     ${GREEN}$(cloudflared --version | head -n 1)${NC}"
else
    echo -e "${YELLOW}⚠️  cloudflared is not installed.${NC}"
    echo "Cloudflared is required to connect cloud-based Google Gemini to your local machine."
    
    mkdir -p "$HOME/.local/bin"
    if [ "$OS" = "Linux" ] && [ "$ARCH" = "x86_64" ]; then
        echo "Attempting automatic download of cloudflared for Linux x86_64..."
        curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o "$HOME/.local/bin/cloudflared"
        chmod +x "$HOME/.local/bin/cloudflared"
        export PATH="$HOME/.local/bin:$PATH"
        echo -e "${GREEN}✔ Installed cloudflared to ~/.local/bin/cloudflared${NC}"
    elif [ "$OS" = "Darwin" ]; then
        echo -e "${YELLOW}On macOS, please install via Homebrew:${NC} brew install cloudflared"
    else
        echo -e "${YELLOW}Please install cloudflared from: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-local-tunnel/${NC}"
    fi
fi

# 4. Make all scripts executable
chmod +x "$REPO_DIR/server.py" \
         "$REPO_DIR/start_daemon.sh" \
         "$REPO_DIR/stop_daemon.sh" \
         "$REPO_DIR/status.sh"

# 5. Create Global CLI command `antigravity-mcp`
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
CLI_PATH="$BIN_DIR/antigravity-mcp"

cat << EOF > "$CLI_PATH"
#!/usr/bin/env bash
# Antigravity MCP CLI Wrapper
PROJECT_DIR="$REPO_DIR"

case "\$1" in
    start)
        exec "\$PROJECT_DIR/start_daemon.sh" "\${@:2}"
        ;;
    stop)
        exec "\$PROJECT_DIR/stop_daemon.sh" "\${@:2}"
        ;;
    status)
        exec "\$PROJECT_DIR/status.sh" "\${@:2}"
        ;;
    tunnel)
        exec python3 "\$PROJECT_DIR/server.py" --tunnel "\${@:2}"
        ;;
    server)
        exec python3 "\$PROJECT_DIR/server.py" --http "\${2:-8080}"
        ;;
    stdio|--stdio)
        # Defaults to current directory if not specified
        exec python3 "\$PROJECT_DIR/server.py" --stdio --workspace "\$PWD" "\${@:2}"
        ;;
    *)
        exec python3 "\$PROJECT_DIR/server.py" "\$@"
        ;;
esac
EOF

chmod +x "$CLI_PATH"
echo -e "🚀 Installed CLI:   ${GREEN}${CLI_PATH}${NC}"

# 6. Self-Register in Antigravity IDE configuration if present
CONFIG_DIR="$HOME/.gemini/config"
CONFIG_FILE="$CONFIG_DIR/mcp_config.json"

if [ -d "$CONFIG_DIR" ]; then
    echo -e "🤖 Registering in Antigravity IDE (${CONFIG_FILE})..."
    python3 - << PYEOF
import json
import os
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
print("✔ Antigravity IDE configuration updated successfully.")
PYEOF
fi

# 7. PATH Notice
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo -e "\n${YELLOW}💡 Note:${NC} Make sure ${YELLOW}~/.local/bin${NC} is in your PATH."
    echo "Add this to your ~/.bashrc or ~/.zshrc if not already present:"
    echo -e "  export PATH=\"\$HOME/.local/bin:\$PATH\"\n"
fi

echo -e "\n${GREEN}🎉 Installation Complete!${NC}"
echo -e "--------------------------------------------------"
echo -e "To start background server for Google Gemini:"
echo -e "  ${YELLOW}antigravity-mcp start${NC}  (or ./start_daemon.sh)"
echo -e ""
echo -e "To check status & get public URL:"
echo -e "  ${YELLOW}antigravity-mcp status${NC} (or ./status.sh)"
echo -e ""
echo -e "To stop background server:"
echo -e "  ${YELLOW}antigravity-mcp stop${NC}   (or ./stop_daemon.sh)"
echo -e "=================================================="
