#!/bin/bash

# =========================================
# 🤖 Telegram Lottory Bot Installer by Shayan 🤖
# =========================================
clear
echo "========================================="
echo "🤖 Telegram Lottory Bot Installer by Shayan 🤖"
echo "========================================="
echo "1️⃣ Install Telegram Bot"
echo "2️⃣ Remove Telegram Bot"
echo "3️⃣ Exit"
echo -n "👉 Choose an option (1/2/3): "
read option

# 🔍 تشخیص مدیریت پکیج سیستم
if command -v apt >/dev/null 2>&1; then
    PKG_MANAGER="apt"
elif command -v yum >/dev/null 2>&1; then
    PKG_MANAGER="yum"
elif command -v dnf >/dev/null 2>&1; then
    PKG_MANAGER="dnf"
elif command -v pacman >/dev/null 2>&1; then
    PKG_MANAGER="pacman"
elif command -v brew >/dev/null 2>&1; then
    PKG_MANAGER="brew"
else
    echo "❌ No supported package manager found. Exiting..."
    exit 1
fi

# ================================
# 🚀 **نصب ربات**
# ================================
if [ "$option" == "1" ]; then
    echo "🔄 Updating and upgrading the server..."
    if [[ "$PKG_MANAGER" == "apt" ]]; then
        sudo apt update && sudo apt upgrade -y
    elif [[ "$PKG_MANAGER" == "yum" || "$PKG_MANAGER" == "dnf" ]]; then
        sudo $PKG_MANAGER update -y
    elif [[ "$PKG_MANAGER" == "pacman" ]]; then
        sudo pacman -Syu --noconfirm
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        brew update
    fi

    echo "📦 Installing required dependencies..."
    if [[ "$PKG_MANAGER" == "apt" ]]; then
        sudo apt install -y git python3 python3-pip
    elif [[ "$PKG_MANAGER" == "yum" || "$PKG_MANAGER" == "dnf" ]]; then
        sudo $PKG_MANAGER install -y git python3 python3-pip
    elif [[ "$PKG_MANAGER" == "pacman" ]]; then
        sudo pacman -S --noconfirm git python python-pip
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        brew install git python
    fi

    # 📥 **کلون کردن پروژه از گیت‌هاب**
    echo "📥 Cloning the Lottory Bot repository..."
    git clone https://github.com/heroinsh/lottory-bot.git
    cd lottory-bot || { echo "❌ Failed to enter directory"; exit 1; }

    # 📦 **نصب کتابخانه‌های مورد نیاز پایتون**
    echo "📦 Installing required Python libraries..."
    pip3 install -r requirements.txt || pip3 install \
        telebot sqlite3 logging random time threading \
        jdatetime pytz persiantools schedule uuid

    # 📝 **دریافت توکن ربات از کاربر**
    echo -n "🤖 Enter your Telegram Bot Token: "
    read bot_token
    if [[ -z "$bot_token" ]]; then
        echo "❌ Token cannot be empty! Exiting..."
        exit 1
    fi
    sed -i "16s|TOKEN = ''|TOKEN = '$bot_token'|" lottory.py

    # 📝 **دریافت Chat ID ادمین**
    echo -n "👤 Enter Admin Chat ID: "
    read admin_chat_id
    if [[ -z "$admin_chat_id" ]]; then
        echo "❌ Admin Chat ID cannot be empty! Exiting..."
        exit 1
    fi
    sed -i "17s|ADMIN_USER_ID =|ADMIN_USER_ID = $admin_chat_id|" lottory.py

    # ✅ **تأیید و اجرای ربات**
    echo "✅ Configuration completed successfully!"
    echo "🚀 Starting the bot..."
    nohup python3 lottory.py > bot.log 2>&1 &

    echo "📜 Bot is running in the background! Use 'tail -f bot.log' to see logs."

# ================================
# ❌ **حذف ربات**
# ================================
elif [ "$option" == "2" ]; then
    echo "🔍 Checking if the bot is running..."
    pkill -f "python3 lottory.py"
    
    echo "🗑 Removing the bot directory..."
    rm -rf lottory-bot

    echo "✅ Lottory Bot has been removed successfully."

# ================================
# 🚪 **خروج**
# ================================
elif [ "$option" == "3" ]; then
    echo "👋 Exiting..."
    exit 0
else
    echo "❌ Invalid option! Please select 1, 2, or 3."
fi
