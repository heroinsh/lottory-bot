#!/bin/bash
# =========================================
# 🤖 Telegram Lottory Bot Installer by Shayan 🤖
#
# این اسکریپت جهت نصب و پیکربندی خودکار ربات تلگرامی Lottory
# طراحی شده است. این ربات جهت اجرای قرعه‌کشی در تلگرام ساخته شده.
#
# از توزیع‌های Ubuntu/Debian و Arch Linux پشتیبانی می‌کند.
# =========================================

set -e  # خروج در صورت بروز خطا

# تابع بررسی توزیع سیستم‌عامل
check_distribution() {
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_ID=$ID
    DISTRO_NAME=$NAME
    DISTRO_VERSION=$VERSION
  else
    echo "❌ Unable to detect distribution."
    exit 1
  fi
}

# نصب برای سیستم‌های Ubuntu/Debian
install_ubuntu_debian() {
  echo "🟢 Detected Ubuntu/Debian based system."
  echo "🔄 Updating and upgrading the system..."
  sudo apt update -y && sudo apt upgrade -y

  echo "📦 Installing required dependencies (git, python3, pip)..."
  sudo apt install -y git python3 python3-pip

  echo "📥 Cloning the Lottory Bot repository..."
  git clone https://github.com/heroinsh/lottory-bot.git
  cd lottory-bot || { echo "❌ Failed to enter directory lottory-bot."; exit 1; }

  echo "📦 Installing Python dependencies..."
  if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt
  else
    # نصب پکیج‌های مورد نیاز (توجه: برخی ماژول‌ها مانند logging، time، random، threading و sqlite3 از پیش نصب هستند)
    pip3 install pyTelegramBotAPI jdatetime pytz persiantools schedule
  fi

  echo -n "🤖 Enter your Telegram Bot Token: "
  read -r bot_token
  if [ -z "$bot_token" ]; then
      echo "❌ Bot token cannot be empty. Exiting..."
      exit 1
  fi

  echo -n "👤 Enter Admin Chat ID: "
  read -r admin_chat_id
  if [ -z "$admin_chat_id" ]; then
      echo "❌ Admin Chat ID cannot be empty. Exiting..."
      exit 1
  fi

  # به‌روزرسانی فایل lottory.py با استفاده از sed
  sed -i "s/^TOKEN = .*/TOKEN = '$bot_token'/" lottory.py
  sed -i "s/^ADMIN_USER_ID = .*/ADMIN_USER_ID = $admin_chat_id/" lottory.py

  echo "✅ Configuration updated successfully!"
  echo "🚀 Starting the Lottory Bot..."
  nohup python3 lottory.py > bot.log 2>&1 &
  echo "📜 Bot is running in the background. Check bot.log for logs."
}

# نصب برای سیستم‌های Arch Linux
install_arch() {
  echo "🟢 Detected Arch Linux based system."
  echo "🔄 Updating and upgrading the system..."
  sudo pacman -Syu --noconfirm

  echo "📦 Installing required dependencies (git, python, pip)..."
  sudo pacman -S --noconfirm git python python-pip

  echo "📥 Cloning the Lottory Bot repository..."
  git clone https://github.com/heroinsh/lottory-bot.git
  cd lottory-bot || { echo "❌ Failed to enter directory lottory-bot."; exit 1; }

  echo "📦 Installing Python dependencies..."
  if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt
  else
    pip3 install pyTelegramBotAPI jdatetime pytz persiantools schedule
  fi

  echo -n "🤖 Enter your Telegram Bot Token: "
  read -r bot_token
  if [ -z "$bot_token" ]; then
      echo "❌ Bot token cannot be empty. Exiting..."
      exit 1
  fi

  echo -n "👤 Enter Admin Chat ID: "
  read -r admin_chat_id
  if [ -z "$admin_chat_id" ]; then
      echo "❌ Admin Chat ID cannot be empty. Exiting..."
      exit 1
  fi

  sed -i "s/^TOKEN = .*/TOKEN = '$bot_token'/" lottory.py
  sed -i "s/^ADMIN_USER_ID = .*/ADMIN_USER_ID = $admin_chat_id/" lottory.py

  echo "✅ Configuration updated successfully!"
  echo "🚀 Starting the Lottory Bot..."
  nohup python3 lottory.py > bot.log 2>&1 &
  echo "📜 Bot is running in the background. Check bot.log for logs."
}

# تابع حذف ربات
remove_bot() {
  echo "🔍 Checking if Lottory Bot is running..."
  pkill -f "python3 lottory.py" || echo "ℹ️ No running bot process found."
  
  if [ -d "lottory-bot" ]; then
    echo "🗑 Removing the lottory-bot directory..."
    rm -rf lottory-bot
  else
    echo "ℹ️ lottory-bot directory does not exist."
  fi
  echo "✅ Lottory Bot has been removed successfully."
}

# -------------------------------
# Main Execution
# -------------------------------
clear
echo "========================================="
echo "🤖 Telegram Lottory Bot Installer by Shayan 🤖"
echo "========================================="
echo "1) Install Lottory Bot"
echo "2) Remove Lottory Bot"
echo "3) Exit"
echo -n "👉 Choose an option (1/2/3): "
read -r option

check_distribution
echo "Detected distribution: $DISTRO_NAME ($DISTRO_ID)"

case $option in
  1)
    if [[ "$DISTRO_ID" == "ubuntu" || "$DISTRO_ID" == "debian" ]]; then
      install_ubuntu_debian
    elif [[ "$DISTRO_ID" == "arch" ]]; then
      install_arch
    else
      echo "❌ Unsupported distribution: $DISTRO_NAME. Exiting..."
      exit 1
    fi
    ;;
  2)
    remove_bot
    ;;
  3)
    echo "👋 Exiting..."
    exit 0
    ;;
  *)
    echo "❌ Invalid option. Exiting..."
    exit 1
    ;;
esac
