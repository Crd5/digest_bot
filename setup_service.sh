#!/bin/bash

# Telegram Read-Only AI Assistant - Service Setup Script
# This script generates a systemd service file for the bot.

# Get the absolute path of the project directory
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P) || exit 1
PROJECT_DIR="$SCRIPT_DIR"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
USER=$(whoami)
SERVICE_NAME="tg-digest-bot"

systemd_quote() {
    local value="$1"
    value="${value//\\/\\\\}"
    value="${value//\"/\\\"}"
    value="${value//%/%%}"
    printf '"%s"' "$value"
}

secure_private_file() {
    local file_path="$1"
    if [ -f "$file_path" ]; then
        if chmod 600 "$file_path"; then
            echo "Restricted permissions on $file_path."
        else
            echo "Warning: Could not restrict permissions on $file_path."
        fi
    fi
}

SYSTEMD_PROJECT_DIR=$(systemd_quote "$PROJECT_DIR")
SYSTEMD_VENV_PYTHON=$(systemd_quote "$VENV_PYTHON")

echo "--- Telegram Read-Only AI Assistant Service Setup ---"

# Restrict local secrets before any early exit.
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "Warning: .env file not found in $PROJECT_DIR."
    echo "Ensure you have configured your API keys before starting the service."
else
    secure_private_file "$PROJECT_DIR/.env"
fi

for ENV_CANDIDATE in "$PROJECT_DIR"/.env.*; do
    [ -e "$ENV_CANDIDATE" ] || continue
    [ "$ENV_CANDIDATE" = "$PROJECT_DIR/.env.example" ] && continue
    secure_private_file "$ENV_CANDIDATE"
done

# Check if the exact Telethon session file exists (Telethon needs interactive login once)
SESSION_FILE="$PROJECT_DIR/digest_session.session"
if [ ! -f "$SESSION_FILE" ]; then
    echo "Warning: digest_session.session file not found."
    echo "It is highly recommended to run 'python main.py' manually once to authenticate"
    echo "before starting the systemd service, as the service is non-interactive."
else
    secure_private_file "$SESSION_FILE"
fi

for DB_CANDIDATE in "$PROJECT_DIR"/digest_bot.db "$PROJECT_DIR"/digest_bot.db-journal "$PROJECT_DIR"/digest_bot.db-wal "$PROJECT_DIR"/digest_bot.db-shm; do
    [ -e "$DB_CANDIDATE" ] || continue
    secure_private_file "$DB_CANDIDATE"
done

for SESSION_CANDIDATE in "$PROJECT_DIR"/*.session "$PROJECT_DIR"/*.session-journal "$PROJECT_DIR"/*.session-wal "$PROJECT_DIR"/*.session-shm; do
    [ -e "$SESSION_CANDIDATE" ] || continue
    [ "$SESSION_CANDIDATE" = "$SESSION_FILE" ] && continue
    secure_private_file "$SESSION_CANDIDATE"
done

# Check if venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found at $PROJECT_DIR/venv"
    echo "Please create it first: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Generate the service file content
SERVICE_FILE_CONTENT="[Unit]
Description=Telegram Read-Only AI Assistant
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SYSTEMD_PROJECT_DIR
ExecStart=$SYSTEMD_VENV_PYTHON main.py
UMask=0077
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target"

# Write to file
echo "$SERVICE_FILE_CONTENT" > "$PROJECT_DIR/$SERVICE_NAME.service"

echo "Service file '$SERVICE_NAME.service' has been generated."
echo ""
echo "Steps to install and start the service:"
echo "1. Copy the service file to systemd directory:"
echo "   sudo cp $SERVICE_NAME.service /etc/systemd/system/"
echo ""
echo "2. Reload systemd daemon:"
echo "   sudo systemctl daemon-reload"
echo ""
echo "3. Enable the service to start on boot:"
echo "   sudo systemctl enable $SERVICE_NAME"
echo ""
echo "4. Start the service:"
echo "   sudo systemctl start $SERVICE_NAME"
echo ""
echo "5. Monitor logs:"
echo "   journalctl -u $SERVICE_NAME -f"
echo ""
echo "Installation complete!"
