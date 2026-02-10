#!/bin/bash

# VST Green Machine Control Panel Installer
set -e

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$INSTALL_DIR/vst_venv"
SERVICE_NAME="gm_control_panel.service"
SERVICE_PATH="$INSTALL_DIR/$SERVICE_NAME"
SYSTEMD_PATH="/etc/systemd/system/$SERVICE_NAME"
RUN_SCRIPT="$INSTALL_DIR/run.sh"

echo "===== VST Green Machine Control Panel Installer ====="
echo "Installing in: $INSTALL_DIR"

# Step 1: Python & venv setup
echo -e "\n[1/4] Setting up virtual environment..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

echo "📦 Creating virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Step 2: Install requirements
echo -e "\n[2/4] Installing Python packages..."
if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r "$INSTALL_DIR/requirements.txt"
else
    echo "❌ requirements.txt not found!"
    exit 1
fi

# Step 3: Create systemd service file
echo -e "\n[3/4] Creating service file..."

CURRENT_USER=$(logname || whoami)
IS_ROOT=false
[ "$(id -u)" -eq 0 ] && IS_ROOT=true

chmod +x "$RUN_SCRIPT"

cat > "$SERVICE_PATH" << EOF
[Unit]
Description=Green Machine Control Panel Service
After=network.target

[Service]
WorkingDirectory=$INSTALL_DIR
ExecStartPre=/bin/sleep 2
ExecStart=/bin/bash $RUN_SCRIPT
Type=idle
User=$CURRENT_USER
StandardOutput=inherit
Environment="DISPLAY=:0"
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# Step 4: Install & start service
echo -e "\n[4/4] Installing and starting service..."

if $IS_ROOT; then
    echo "🔧 Installing service to systemd..."
    cp "$SERVICE_PATH" "$SYSTEMD_PATH"
    chmod 644 "$SYSTEMD_PATH"
    systemctl daemon-reload

    read -rp "Enable service at boot? (y/n): " enable
    [[ "$enable" =~ ^[Yy] ]] && systemctl enable "$SERVICE_NAME"

    read -rp "Start service now? (y/n): " start
    [[ "$start" =~ ^[Yy] ]] && {
        systemctl start "$SERVICE_NAME"
        echo "✅ Service started. Status:"
        systemctl status "$SERVICE_NAME" --no-pager
    }
else
    echo "⚠️ Not running as root. To install manually:"
    echo "sudo cp \"$SERVICE_PATH\" \"$SYSTEMD_PATH\""
    echo "sudo chmod 644 \"$SYSTEMD_PATH\""
    echo "sudo systemctl daemon-reload"
    echo "sudo systemctl enable \"$SERVICE_NAME\""
    echo "sudo systemctl start \"$SERVICE_NAME\""
fi

# Final: Ensure run.sh activates venv
echo -e "\n🔄 Updating run.sh to use virtual environment..."
if ! grep -q "source \"$VENV_DIR/bin/activate\"" "$RUN_SCRIPT"; then
    cp "$RUN_SCRIPT" "${RUN_SCRIPT}.bak"
    sed -i "s|#!/bin/bash|#!/bin/bash\n# Activate virtual environment\nsource \"$VENV_DIR/bin/activate\"|" "$RUN_SCRIPT"
    echo "📝 run.sh updated to include venv activation"
else
    echo "✔️ run.sh already activates the virtual environment"
fi

# Done
echo -e "\n🎉 Installation Complete!"
[ "$IS_ROOT" = false ] && echo "⚠️ Service must be installed manually as root."
echo "To run manually: ./run.sh"