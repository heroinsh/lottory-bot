#!/bin/bash

# Author: Shayan
# This script automates the installation and setup of a Telegram bot

set -e  # Exit on error

BOT_DIR=~/lottory-bot  # Bot directory
GITHUB_REPO="https://github.com/heroinsh/lottory-bot.git"  # GitHub repo link
BOT_FILE="lottory.py"  # Main bot script

echo "========================================="
echo "🤖 Telegram Bot Installer by Shayan 🤖"
echo "========================================="
echo "1️⃣ Install Telegram Bot"
echo "2️⃣ Remove Telegram Bot"
echo "3️⃣ Exit"
read -p "👉 Choose an option (1/2/3): " choice

# INSTALLATION
if [[ $choice == "1" ]]; then
    echo "🔄 Updating and upgrading the server..."
    sudo apt update && sudo apt upgrade -y

    echo "📦 Installing required dependencies..."
    sudo apt install -y git python3 python3-pip

    echo "📥 Cloning the bot from GitHub..."
    git clone $GITHUB_REPO $BOT_DIR || { echo "⚠️ Cloning failed! Check your GitHub URL."; exit 1; }

    cd $BOT_DIR

    echo "📦 Installing required Python libraries..."
    pip3 install -r requirements.txt || {
        echo "⚠️ Failed to install dependencies. Installing manually..."
        pip3 install telebot sqlite3 logging random time threading jdatetime pytz persiantools schedule uuid
    }

    # Get bot token
    while true; do
        read -p "✏️ Enter your Telegram Bot Token: " BOT_TOKEN
        if [[ ! -z "$BOT_TOKEN" ]]; then break; fi
        echo "⚠️ Token cannot be empty! Try again."
    done

    # Get admin chat ID
    while true; do
        read -p "✏️ Enter your Telegram Admin Chat ID: " ADMIN_ID
        if [[ ! -z "$ADMIN_ID" ]]; then break; fi
        echo "⚠️ Chat ID cannot be empty! Try again."
    done

    echo "🔄 Updating bot configuration..."
    sed -i "s|TOKEN = ''|TOKEN = '$BOT_TOKEN'|" $BOT_FILE
    sed -i "s|ADMIN_USER_ID =|ADMIN_USER_ID = $ADMIN_ID|" $BOT_FILE

    echo "✅ Configuration updated successfully!"

    # Create systemd service
    SERVICE_FILE="/etc/systemd/system/telegram-bot.service"
    sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Telegram Bot
After=network.target

[Service]
ExecStart=/usr/bin/python3 $BOT_DIR/$BOT_FILE
WorkingDirectory=$BOT_DIR
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

    echo "🔄 Enabling bot service..."
    sudo systemctl daemon-reload
    sudo systemctl enable telegram-bot
    sudo systemctl start telegram-bot

    echo "✅ Bot installed and running as a systemd service!"
    echo "📌 Use 'sudo systemctl status telegram-bot' to check the bot's status."

# UNINSTALLATION
elif [[ $choice == "2" ]]; then
    echo "❌ Stopping and removing the Telegram bot..."

    # Stop and disable service
    sudo systemctl stop telegram-bot || echo "ℹ️ No running bot found."
    sudo systemctl disable telegram-bot || echo "ℹ️ Service not found."
    sudo rm -f /etc/systemd/system/telegram-bot.service

    # Remove project directory
    if [ -d "$BOT_DIR" ]; then
        echo "🗑️ Removing bot directory..."
        rm -rf "$BOT_DIR"
    else
        echo "ℹ️ Bot directory not found."
    fi

    echo "🔄 Updating the server..."
    sudo apt update && sudo apt upgrade -y

    echo "✅ Bot removed successfully!"

# EXIT OPTION
elif [[ $choice == "3" ]]; then
    echo "👋 Exiting..."
    exit 0

else
    echo "❌ Invalid option! Please run the script again."
    exit 1
fi
