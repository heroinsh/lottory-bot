import telebot
import sqlite3
import logging
from telebot import types
import random
import time
import threading
import jdatetime
import pytz
from persiantools.jdatetime import JalaliDateTime
import schedule
from datetime import datetime, timedelta
import uuid

# Bot settings
TOKEN = ''
ADMIN_USER_ID = 
DB_NAME = 'lottery_bot.db'

# Logging setup
logging.basicConfig(filename='bot.log', level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create bot instance
bot = telebot.TeleBot(TOKEN)

# Database connection
def get_db_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

# Create necessary tables
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        join_date TEXT,
        referred_by INTEGER,
        points INTEGER DEFAULT 1,
        invites INTEGER DEFAULT 0,
        invite_link TEXT,
        last_bonus_date TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS channels (
        channel_id TEXT PRIMARY KEY,
        channel_name TEXT,
        channel_link TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lottery_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        winners TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scheduled_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT,
        schedule_time TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS blocked_users (
        user_id INTEGER PRIMARY KEY
    )
    ''')
    conn.commit()
    conn.close()

create_tables()

# کنترل وضعیت قرعه‌کشی
LOTTERY_ACTIVE = True
def is_lottery_ended(lottery_id):
    global LOTTERY_ACTIVE
    return not LOTTERY_ACTIVE

texts = {
    'welcome_message': """🎉 سلام {first_name} عزیز!

به ربات قرعه‌کشی ما خوش آمدید! شما با موفقیت در قرعه‌کشی شرکت کردید.

🆔 چت آی‌دی شما: `{user_id}`

🔗 لینک دعوت شخصی شما:
{invite_link}

💌 از این لینک برای دعوت دوستان خود استفاده کنید و امتیاز بیشتری کسب کنید!

هر روز با دریافت جایزه روزانه، شرکت در قرعه‌کشی‌ها و دعوت دوستان، شانس برنده شدن خود را افزایش دهید!""",
    'already_registered': "⚠️ شما قبلاً در قرعه‌کشی ثبت‌نام کرده‌اید. می‌توانید از منوی اصلی استفاده کنید.",
    'join_channels_message': """👋 سلام {first_name} عزیز!

🎁 برای شرکت در قرعه‌کشی، ابتدا در کانال‌های ما عضو شوید:

⚠️ بعد از عضویت، روی دکمه «تایید عضویت» کلیک کنید.""",
    'user_blocked': "⛔️ متأسفانه دسترسی شما به ربات مسدود شده است. در صورت نیاز به اطلاعات بیشتر، با پشتیبانی تماس بگیرید.",
    'not_member_all_channels': "⚠️ شما هنوز عضو همه کانال‌ها نشده‌اید! لطفاً ابتدا عضو شوید و سپس روی دکمه «تایید عضویت» کلیک کنید.",
    'user_profile': """👤 پروفایل شما:

🆔 چت آی‌دی: `{user_id}`
👤 نام: {name}
📧 یوزرنیم: @{username}
⭐️ امتیاز: {points}
👥 تعداد دعوت‌ها: {invites}
🎲 شانس شما در قرعه‌کشی: {chance}%

برای افزایش شانس خود، دوستانتان را دعوت کنید و هر روز جایزه روزانه خود را دریافت کنید!""",
    'user_not_found': "⚠️ اطلاعات شما یافت نشد! لطفاً دوباره /start را ارسال کنید.",
    'leaderboard_title': "🏆 جدول امتیازات برتر:",
    'leaderboard_entry': "{rank}. {name} - ⭐️ {points} امتیاز\n",
    'help_text': """📚 راهنمای استفاده از ربات:

1️⃣ برای شرکت در قرعه‌کشی، ابتدا در کانال‌های ما عضو شوید.
2️⃣ با دعوت دوستان خود، امتیاز بیشتری کسب کنید.
3️⃣ هر امتیاز، شانس شما را در قرعه‌کشی افزایش می‌دهد.
4️⃣ در بخش پروفایل، اطلاعات و شانس خود را ببینید.
5️⃣ در لیدربورد، رتبه خود را در میان سایر شرکت‌کنندگان مشاهده کنید.
6️⃣ هر روز جایزه روزانه خود را دریافت کنید تا امتیاز بیشتری کسب کنید.

❓ سوالات متداول:
س: چگونه امتیاز بیشتری کسب کنم؟
ج: با دعوت دوستان، دریافت جایزه روزانه و فعالیت مستمر در ربات.

س: هر چند وقت یکبار قرعه‌کشی انجام می‌شود؟
ج: قرعه‌کشی‌ها به صورت دوره‌ای توسط ادمین اعلام می‌شوند. مطمئن شوید اعلان‌های ربات را فعال کرده‌اید تا از زمان قرعه‌کشی‌ها مطلع شوید.

س: اگر در قرعه‌کشی برنده شوم، چگونه مطلع شوم؟
ج: برندگان از طریق پیام خصوصی در ربات مطلع خواهند شد. همچنین نتایج در کانال اصلی ما نیز اعلام می‌شود.""",
    'activity_history': """📋 تاریخچه فعالیت شما:

📅 تاریخ عضویت: {join_date}
⭐️ امتیاز فعلی: {points}
👥 تعداد دعوت‌ها: {invites}

🏆 قرعه‌کشی‌های اخیر:""",
    'recent_lotteries': "قرعه‌کشی‌های اخیر که شرکت کرده‌اید:",
    'lottery_won': "🎉 {date}: شما برنده شدید!\n",
    'lottery_participated': "📅 {date}: شرکت کردید\n",
    'no_lotteries': "- هنوز در هیچ قرعه‌کشی شرکت نکرده‌اید.",
    'main_menu': """🎉 سلام {first_name} عزیز!

🆔 چت آی‌دی شما: `{user_id}`

🔗 لینک دعوت شخصی شما:
{invite_link}

💌 از این لینک برای دعوت دوستان خود استفاده کنید و امتیاز کسب کنید!

چه کاری می‌توانم برایتان انجام دهم؟""",
    'about_us': """ℹ️ درباره ما:

این ربات توسط تیم ما برای مدیریت قرعه‌کشی و جذب مخاطب طراحی شده است. هدف ما ایجاد یک تجربه سرگرم‌کننده و عادلانه برای همه شرکت‌کنندگان است.

ویژگی‌های ربات ما:
• سیستم امتیازدهی پویا
• قرعه‌کشی‌های منظم با جوایز ارزشمند
• سیستم دعوت دوستان برای کسب امتیاز بیشتر
• جایزه روزانه برای کاربران فعال
• شفافیت در نتایج قرعه‌کشی

👨‍💻 سازنده ربات: @H0lwin_P
🔗 کانال رسمی: @your_channel

از اعتماد شما به ربات ما سپاسگزاریم. امیدواریم تجربه خوبی داشته باشید!""",
    'bonus_already_claimed': "⚠️ شما جایزه روزانه خود را اخیراً دریافت کرده‌اید. لطفاً 24 ساعت بعد دوباره امتحان کنید!",
    'bonus_claimed': "🎁 تبریک! شما 2 امتیاز جایزه روزانه دریافت کردید.",
    'admin_access_denied': "⛔️ شما دسترسی لازم برای این عملیات را ندارید!",
    'admin_panel': """👨‍💻 پنل مدیریت

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:""",
    'enter_winner_count': "🎲 لطفاً تعداد برندگان قرعه‌کشی را وارد کنید:",
    'cancel': "🔙 انصراف",
    'invalid_winner_count': "تعداد برندگان باید بیشتر از صفر باشد.",
    'no_participants': "❌ هیچ کاربری برای قرعه‌کشی وجود ندارد.",
    'lottery_winners': "🏆 برندگان قرعه‌کشی:",
    'winner_info': "{rank}. کاربر با آیدی {user_id}\n",
    'you_won_lottery': """🎉🎉🎉 تبریک! شما در قرعه‌کشی برنده شدید! 🎉🎉🎉

لطفاً برای دریافت جایزه خود با ادمین @H0lwin_P تماس بگیرید.

برای شرکت در قرعه‌کشی‌های بعدی، به فعالیت خود در ربات ادامه دهید و دوستان خود را دعوت کنید تا شانس برنده شدن خود را افزایش دهید!""",
    'lottery_status': "گزارش ربات",
    'top_inviters': "📈 آمار برترین دعوت‌کنندگان:",
    'inviter_info': "{rank}. {name}: {invites} دعوت\n",
    'channel_management': """📢 مدیریت کانال‌ها

لطفاً یک گزینه را انتخاب کنید:""",
    'channel_list': "📋 لیست کانال‌های فعلی:",
    'channel_info': "{rank}. {channel_name} - {channel_link}\n",
    'no_channels': "هیچ کانالی ثبت نشده است.",
    'enter_channel_id': "لطفاً آیدی کانال را وارد کنید:",
    'enter_channel_name': "لطفاً نام کانال را وارد کنید:",
    'enter_channel_link': "لطفاً لینک کانال را وارد کنید:",
    'channel_added_success': "✅ کانال با موفقیت اضافه شد.",
    'channel_already_exists': "❌ این کانال قبلاً اضافه شده است.",
    'channel_add_error': "❌ خطا در اضافه کردن کانال. لطفاً دوباره تلاش کنید.",
    'enter_group_message': "📨 لطفاً پیام گروهی خود را وارد کنید:",
    'group_message_sent': "✅ پیام با موفقیت به {count} کاربر ارسال شد.",
    'enter_scheduled_message': """⏰ لطفاً پیام زمان‌بندی شده و زمان ارسال را به صورت زیر وارد کنید:

متن پیام
YYYY-MM-DD HH:MM""",
    'message_scheduled': "✅ پیام برای ارسال در تاریخ {date_time} زمان‌بندی شد.",
    'invalid_date_format': "❌ فرمت تاریخ و زمان نامعتبر است. لطفاً دوباره تلاش کنید.",
    'enter_user_id_to_block': "لطفاً آیدی کاربری را که می‌خواهید مسدود کنید وارد نمایید:",
    'user_blocked': "✅ کاربر با آیدی {user_id} مسدود شد.",
    'invalid_user_id': "❌ آیدی کاربر نامعتبر است. لطفاً یک عدد صحیح وارد کنید.",
    'enter_user_id_to_unblock': "لطفاً آیدی کاربری را که می‌خواهید از حالت مسدود خارج کنید وارد نمایید:",
    'user_unblocked': "✅ کاربر با آیدی {user_id} از حالت مسدود خارج شد.",
    'referral_success': """🎉 کاربر {first_name} با لینک دعوت شما وارد ربات شد!
✅ شما 2 امتیاز دریافت کردید!
🆔 چت آی‌دی کاربر: `{user_id}`""",
    'profile_button': "👤 پروفایل",
    'leaderboard_button': "🏆 لیدر بورد",
    'help_button': "📚 راهنما",
    'activity_history_button': "📋 تاریخچه فعالیت",
    'about_us_button': "ℹ️ درباره ما",
    'daily_bonus_button': "🎁 جایزه روزانه",
    'join_channel': "عضویت در کانال {channel_name} 📢",
    'check_membership': "تایید عضویت ✅",
    'back_button': "🔙 بازگشت",
    'chat_with_creator': "💬 چت با سازنده",
    'creator_channel': "📢 کانال سازنده",
    'start_lottery': "🎲 شروع قرعه‌کشی",
    'invite_stats': "📈 آمار دعوت‌ها",
    'manage_channels': "📢 مدیریت کانال‌ها",
    'send_group_message': "📨 ارسال پیام گروهی",
    'schedule_message': "⏰ پیام زمان‌بندی شده",
    'block_user': "🚫 مسدود کردن کاربر",
    'unblock_user': "✅ رفع مسدودیت کاربر",
    'list_channels': "📋 لیست کانال‌ها",
    'add_channel': "➕ افزودن کانال",
    'back_to_admin': "🔙 بازگشت به پنل ادمین",
    'back_to_channel_management': "🔙 بازگشت به مدیریت کانال‌ها",
    'reset_lottery': "🔄 بازنشانی قرعه‌کشی",
    'lottery_reset_success': "✅ قرعه‌کشی با موفقیت بازنشانی شد. همه کاربران باید دوباره ثبت‌نام کنند."
}

def get_text(key):
    return texts.get(key, key)

# Helper functions
def is_user_member(user_id, channel_id):
    try:
        member = bot.get_chat_member(channel_id, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

def generate_invite_link(user_id):
    unique_id = str(uuid.uuid4())[:8]
    return f"https://t.me/{bot.get_me().username}?start={user_id}_{unique_id}"

def save_user_info(user_id, username, first_name, referred_by=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        if cursor.fetchone():
            return False  # کاربر قبلاً ثبت‌نام کرده است
        now = JalaliDateTime.now(pytz.timezone('Asia/Tehran'))
        invite_link = generate_invite_link(user_id)
        cursor.execute('''
        INSERT INTO users (user_id, username, first_name, join_date, referred_by, invite_link)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, now.strftime('%Y-%m-%d %H:%M:%S'), referred_by, invite_link))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving user info: {e}")
        return False
    finally:
        conn.close()

def add_points(user_id, points=2):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET points = points + ? WHERE user_id = ?', (points, user_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error adding points: {e}")
    finally:
        conn.close()

def increase_invites(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET invites = invites + 1 WHERE user_id = ?', (user_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"Error increasing invites: {e}")
    finally:
        conn.close()

def calculate_chance(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT points, invites FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        if user:
            cursor.execute('SELECT SUM(points) FROM users')
            total_points = cursor.fetchone()[0] or 1
            return round(((user[0] + user[1]) / total_points) * 100, 2)
        return 0
    except Exception as e:
        logger.error(f"Error calculating chance: {e}")
        return 0
    finally:
        conn.close()

def get_channels():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT channel_id, channel_name, channel_link FROM channels')
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        return []
    finally:
        conn.close()

def check_user_membership(user_id):
    channels = get_channels()
    not_member_channels = []
    for channel in channels:
        if not is_user_member(user_id, channel[0]):
            not_member_channels.append(channel)
    return not_member_channels

def is_user_blocked(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT 1 FROM blocked_users WHERE user_id = ?', (user_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()

# Bot commands
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    if is_user_blocked(user_id):
        bot.reply_to(message, get_text('user_blocked'))
        return

    username = message.from_user.username
    first_name = message.from_user.first_name

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    existing_user = cursor.fetchone()
    conn.close()

    if existing_user:
        # در صورت ثبت‌نام قبلی، پیام اخطار ارسال و سپس منوی اصلی نمایش داده می‌شود
        bot.send_message(message.chat.id, get_text('already_registered'))
        invite_link = existing_user[7]
        show_main_menu(message, first_name, invite_link, user_id)
        return

    referred_by = None
    if len(message.text.split()) > 1:
        start_param = message.text.split()[1]
        if '_' in start_param:
            referred_by, lottery_id = start_param.split('_')
            if is_lottery_ended(lottery_id):
                bot.reply_to(message, get_text('lottery_ended'))
                return

    not_member_channels = check_user_membership(user_id)
    
    if not not_member_channels:
        if save_user_info(user_id, username, first_name, referred_by):
            if referred_by:
                add_points(int(referred_by))
                increase_invites(int(referred_by))
                bot.send_message(int(referred_by),
                                 get_text('referral_success').format(first_name=first_name, user_id=user_id))
            
            invite_link = generate_invite_link(user_id)
            show_main_menu(message, first_name, invite_link, user_id)
        else:
            bot.send_message(message.chat.id, get_text('already_registered'))
            show_main_menu(message, first_name, generate_invite_link(user_id), user_id)
    else:
        markup = types.InlineKeyboardMarkup()
        for channel in not_member_channels:
            markup.add(types.InlineKeyboardButton(get_text('join_channel').format(channel_name=channel[1]), url=channel[2]))
        markup.add(types.InlineKeyboardButton(get_text('check_membership'), callback_data="check_membership"))
        bot.send_message(message.chat.id, get_text('join_channels_message').format(first_name=first_name), reply_markup=markup)

# ارسال منوی اصلی (برای اولین نمایش پیام)
def show_main_menu(message, first_name, invite_link, user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(get_text('profile_button'), callback_data="user_profile"),
        types.InlineKeyboardButton(get_text('leaderboard_button'), callback_data="leaderboard"),
        types.InlineKeyboardButton(get_text('help_button'), callback_data="help"),
        types.InlineKeyboardButton(get_text('activity_history_button'), callback_data="activity_history"),
        types.InlineKeyboardButton(get_text('about_us_button'), callback_data="about_us"),
        types.InlineKeyboardButton(get_text('daily_bonus_button'), callback_data="daily_bonus")
    )
    bot.send_message(message.chat.id,
                     get_text('main_menu').format(first_name=first_name, invite_link=invite_link, user_id=user_id),
                     reply_markup=markup)

# ویرایش منوی اصلی (برای دکمه بازگشت در منوهای فرعی)
def edit_main_menu(call, first_name, invite_link, user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(get_text('profile_button'), callback_data="user_profile"),
        types.InlineKeyboardButton(get_text('leaderboard_button'), callback_data="leaderboard"),
        types.InlineKeyboardButton(get_text('help_button'), callback_data="help"),
        types.InlineKeyboardButton(get_text('activity_history_button'), callback_data="activity_history"),
        types.InlineKeyboardButton(get_text('about_us_button'), callback_data="about_us"),
        types.InlineKeyboardButton(get_text('daily_bonus_button'), callback_data="daily_bonus")
    )
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=get_text('main_menu').format(first_name=first_name, invite_link=invite_link, user_id=user_id),
                          reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    if is_user_blocked(user_id):
        bot.answer_callback_query(call.id, get_text('user_blocked'))
        return

    if call.data in ["start_lottery", "lottery_status", "invite_stats", "manage_channels", "send_group_message", "schedule_message", "back_to_admin", "reset_lottery"]:
        handle_admin_buttons(call)
    elif call.data == "list_channels":
        list_channels(call)
    elif call.data == "add_channel":
        ask_for_channel_info(call)
    elif call.data == "check_membership":
        check_membership(call)
    elif call.data == "user_profile":
        show_user_profile(call)
    elif call.data == "leaderboard":
        show_leaderboard(call)
    elif call.data == "help":
        show_help(call)
    elif call.data == "activity_history":
        show_activity_history(call)
    elif call.data == "back_to_main":
        back_to_main(call)
    elif call.data == "about_us":
        show_about_us(call)
    elif call.data == "daily_bonus":
        give_daily_bonus(call)

def back_to_main(call):
    user_id = call.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, invite_link FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        first_name, invite_link = user
        edit_main_menu(call, first_name, invite_link, user_id)
    else:
        bot.answer_callback_query(call.id, get_text('user_not_found'), show_alert=True)

def check_membership(call):
    user_id = call.from_user.id
    not_member_channels = check_user_membership(user_id)
    if not not_member_channels:
        send_welcome(call.message)
    else:
        markup = types.InlineKeyboardMarkup()
        for channel in not_member_channels:
            markup.add(types.InlineKeyboardButton(get_text('join_channel').format(channel_name=channel[1]), url=channel[2]))
        markup.add(types.InlineKeyboardButton(get_text('check_membership'), callback_data="check_membership"))
        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text=get_text('not_member_all_channels'),
                              reply_markup=markup)

def show_user_profile(call):
    user_id = call.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        chance = calculate_chance(user_id)
        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text=get_text('user_profile').format(user_id=user[0],
                                                                   name=user[2],
                                                                   username=user[1],
                                                                   points=user[5],
                                                                   invites=user[6],
                                                                   chance=chance),
                              reply_markup=types.InlineKeyboardMarkup().add(
                                  types.InlineKeyboardButton(get_text('back_button'), callback_data="back_to_main")
                              ))
    else:
        bot.answer_callback_query(call.id, get_text('user_not_found'), show_alert=True)

def show_leaderboard(call):
    user_id = call.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, first_name, points FROM users ORDER BY points DESC LIMIT 10')
    top_users = cursor.fetchall()
    conn.close()
    message_text = get_text('leaderboard_title') + "\n\n"
    for i, user in enumerate(top_users, 1):
        message_text += get_text('leaderboard_entry').format(rank=i, name=user[1], points=user[2])
    
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=message_text,
                          reply_markup=types.InlineKeyboardMarkup().add(
                              types.InlineKeyboardButton(get_text('back_button'), callback_data="back_to_main")
                          ))

def show_help(call):
    user_id = call.from_user.id
    help_text = get_text('help_text')
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=help_text,
                          reply_markup=types.InlineKeyboardMarkup().add(
                              types.InlineKeyboardButton(get_text('back_button'), callback_data="back_to_main")
                          ))

def show_activity_history(call):
    user_id = call.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT join_date, points, invites FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if user:
        cursor.execute('SELECT date, winners FROM lottery_history ORDER BY date DESC LIMIT 5')
        lottery_history = cursor.fetchall()
        
        history_text = get_text('activity_history').format(join_date=user[0], points=user[1], invites=user[2])
        
        if lottery_history:
            history_text += "\n\n" + get_text('recent_lotteries') + "\n"
            for date, winners in lottery_history:
                if str(user_id) in winners:
                    history_text += get_text('lottery_won').format(date=date)
                else:
                    history_text += get_text('lottery_participated').format(date=date)
        else:
            history_text += "\n\n" + get_text('no_lotteries')
        
        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text=history_text,
                              reply_markup=types.InlineKeyboardMarkup().add(
                                  types.InlineKeyboardButton(get_text('back_button'), callback_data="back_to_main")
                              ))
    else:
        bot.answer_callback_query(call.id, get_text('user_not_found'), show_alert=True)
    conn.close()

def show_about_us(call):
    user_id = call.from_user.id
    about_text = get_text('about_us')
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(get_text('chat_with_creator'), url="https://t.me/H0lwin_P"),
        types.InlineKeyboardButton(get_text('creator_channel'), url="https://t.me/your_channel"),
        types.InlineKeyboardButton(get_text('back_button'), callback_data="back_to_main")
    )
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=about_text,
                          reply_markup=markup)

# تغییر تابع جایزه روزانه: امتیاز ثابت 2 و تنها یکبار در هر 24 ساعت
def give_daily_bonus(call):
    user_id = call.from_user.id
    now = JalaliDateTime.now(pytz.timezone('Asia/Tehran'))
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT last_bonus_date FROM users WHERE user_id = ?', (user_id,))
    last_bonus = cursor.fetchone()
    if last_bonus and last_bonus[0]:
        try:
            last_bonus_dt = datetime.strptime(last_bonus[0], "%Y-%m-%d %H:%M:%S")
            if datetime.now() < last_bonus_dt + timedelta(hours=24):
                bot.answer_callback_query(call.id, get_text('bonus_already_claimed'), show_alert=True)
                conn.close()
                return
        except Exception as e:
            logger.error("Error parsing last_bonus_date: " + str(e))
    bonus_points = 2
    cursor.execute('UPDATE users SET points = points + ?, last_bonus_date = ? WHERE user_id = ?',
                   (bonus_points, now_str, user_id))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, get_text('bonus_claimed'), show_alert=True)
    show_user_profile(call)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_USER_ID:
        show_admin_panel(message)
    else:
        bot.send_message(message.chat.id, get_text('admin_access_denied'))

def show_admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(get_text('start_lottery'), callback_data="start_lottery"),
        types.InlineKeyboardButton(get_text('lottery_status'), callback_data="lottery_status"),
        types.InlineKeyboardButton(get_text('invite_stats'), callback_data="invite_stats"),
        types.InlineKeyboardButton(get_text('manage_channels'), callback_data="manage_channels"),
        types.InlineKeyboardButton(get_text('send_group_message'), callback_data="send_group_message"),
        types.InlineKeyboardButton(get_text('schedule_message'), callback_data="schedule_message"),
        types.InlineKeyboardButton(get_text('reset_lottery'), callback_data="reset_lottery")
    )
    bot.send_message(message.chat.id, get_text('admin_panel'), reply_markup=markup)

def handle_admin_buttons(call):
    if call.from_user.id != ADMIN_USER_ID:
        bot.answer_callback_query(call.id, get_text('admin_access_denied'))
        return

    if call.data == "start_lottery":
        ask_for_winner_count(call)
    elif call.data == "lottery_status":
        # گزارش: نمایش تعداد کاربران، مجموع امتیازات، ثبت نام‌های امروز و تعداد قرعه کشی‌های انجام شده
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        cursor.execute('SELECT SUM(points) FROM users')
        total_points = cursor.fetchone()[0] or 0
        today_str = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) FROM users WHERE join_date LIKE ?", (today_str + '%',))
        today_registrations = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM lottery_history')
        total_lotteries = cursor.fetchone()[0]
        conn.close()
        report_text = f"📊 گزارش ربات:\n\n👥 تعداد کاربران: {total_users}\n⭐️ مجموع امتیازات: {total_points}\n📝 ثبت نام‌های امروز: {today_registrations}\n🎰 تعداد قرعه کشی‌های انجام شده: {total_lotteries}"
        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text=report_text,
                              reply_markup=types.InlineKeyboardMarkup().add(
                                  types.InlineKeyboardButton(get_text('back_button'), callback_data="back_to_admin")
                              ))
    elif call.data == "invite_stats":
        show_invite_stats(call)
    elif call.data == "manage_channels":
        show_channel_management(call)
    elif call.data == "send_group_message":
        ask_for_group_message(call)
    elif call.data == "schedule_message":
        ask_for_scheduled_message(call)
    elif call.data == "back_to_admin":
        show_admin_panel(call.message)
    elif call.data == "reset_lottery":
        reset_lottery(call)

def ask_for_winner_count(call):
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=get_text('enter_winner_count'),
                          reply_markup=types.InlineKeyboardMarkup().add(
                              types.InlineKeyboardButton(get_text('cancel'), callback_data="back_to_admin")
                          ))
    bot.register_next_step_handler(call.message, start_lottery)

def start_lottery(message):
    global LOTTERY_ACTIVE
    if message.text == get_text('cancel'):
        show_admin_panel(message)
        return

    try:
        num_winners = int(message.text)
        if num_winners <= 0:
            raise ValueError(get_text('invalid_winner_count'))
        
        winners = select_winners(num_winners)
        announce_winners(winners, message.chat.id)
        LOTTERY_ACTIVE = False
    except ValueError as e:
        bot.reply_to(message, str(e))
        ask_for_winner_count(message)

def select_winners(num_winners):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, points FROM users')
    users = cursor.fetchall()
    conn.close()

    if not users:
        return []

    total_points = sum(user[1] for user in users)
    winners = random.choices(users, weights=[user[1]/total_points for user in users], k=min(num_winners, len(users)))
    return [winner[0] for winner in winners]

def announce_winners(winners, chat_id):
    if not winners:
        bot.send_message(chat_id, get_text('no_participants'))
        return

    winner_text = get_text('lottery_winners') + "\n\n"
    message_chunks = []
    current_chunk = ""

    for i, winner_id in enumerate(winners, 1):
        winner_info = get_text('winner_info').format(rank=i, user_id=winner_id)
        if len(current_chunk) + len(winner_info) > 4000:
            message_chunks.append(current_chunk)
            current_chunk = winner_info
        else:
            current_chunk += winner_info

    if current_chunk:
        message_chunks.append(current_chunk)

    for chunk in message_chunks:
        bot.send_message(chat_id, winner_text + chunk)

    # ثبت تاریخچه قرعه‌کشی
    conn = get_db_connection()
    cursor = conn.cursor()
    now = JalaliDateTime.now(pytz.timezone('Asia/Tehran'))
    cursor.execute('INSERT INTO lottery_history (date, winners) VALUES (?, ?)',
                   (now.strftime('%Y-%m-%d %H:%M:%S'), ','.join(map(str, winners))))
    conn.commit()
    conn.close()

    # اطلاع رسانی به برندگان
    for winner_id in winners:
        try:
            bot.send_message(winner_id, get_text('you_won_lottery'))
        except Exception as e:
            logger.error(f"Failed to notify winner {winner_id}: {e}")

def show_invite_stats(call):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, invites FROM users ORDER BY invites DESC LIMIT 10')
    top_inviters = cursor.fetchall()
    conn.close()

    stats_text = get_text('top_inviters') + "\n\n"
    for i, (name, invites) in enumerate(top_inviters, 1):
        stats_text += get_text('inviter_info').format(rank=i, name=name, invites=invites)

    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=stats_text,
                          reply_markup=types.InlineKeyboardMarkup().add(
                              types.InlineKeyboardButton(get_text('back_button'), callback_data="back_to_admin")
                          ))

def show_channel_management(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(get_text('list_channels'), callback_data="list_channels"),
        types.InlineKeyboardButton(get_text('add_channel'), callback_data="add_channel"),
        types.InlineKeyboardButton(get_text('back_to_admin'), callback_data="back_to_admin")
    )
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=get_text('channel_management'),
                          reply_markup=markup)

def list_channels(call):
    channels = get_channels()
    if channels:
        channel_list = get_text('channel_list') + "\n\n"
        for i, channel in enumerate(channels, 1):
            channel_list += get_text('channel_info').format(rank=i, channel_name=channel[1], channel_link=channel[2])
    else:
        channel_list = get_text('no_channels')

    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=channel_list,
                          reply_markup=types.InlineKeyboardMarkup().add(
                              types.InlineKeyboardButton(get_text('back_to_channel_management'), callback_data="manage_channels")
                          ))

def ask_for_channel_info(call):
    bot.send_message(call.message.chat.id, get_text('enter_channel_id'))
    bot.register_next_step_handler(call.message, process_add_channel_id)

def process_add_channel_id(message):
    channel_id = message.text
    bot.send_message(message.chat.id, get_text('enter_channel_name'))
    bot.register_next_step_handler(message, process_add_channel_name, channel_id)

def process_add_channel_name(message, channel_id):
    channel_name = message.text
    bot.send_message(message.chat.id, get_text('enter_channel_link'))
    bot.register_next_step_handler(message, process_add_channel_link, channel_id, channel_name)

def process_add_channel_link(message, channel_id, channel_name):
    channel_link = message.text
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO channels (channel_id, channel_name, channel_link) VALUES (?, ?, ?)',
                       (channel_id, channel_name, channel_link))
        conn.commit()
        bot.send_message(message.chat.id, get_text('channel_added_success'))
    except sqlite3.IntegrityError:
        bot.send_message(message.chat.id, get_text('channel_already_exists'))
    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        bot.send_message(message.chat.id, get_text('channel_add_error'))
    finally:
        conn.close()
    show_channel_management(message)

def ask_for_group_message(call):
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=get_text('enter_group_message'),
                          reply_markup=types.InlineKeyboardMarkup().add(
                              types.InlineKeyboardButton(get_text('cancel'), callback_data="back_to_admin")
                          ))
    bot.register_next_step_handler(call.message, send_group_message)

def send_group_message(message):
    if message.text == get_text('cancel'):
        show_admin_panel(message)
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()

    success_count = 0
    for user in users:
        try:
            bot.send_message(user[0], message.text)
            success_count += 1
        except Exception as e:
            logger.error(f"Error sending message to user {user[0]}: {e}")

    bot.reply_to(message, get_text('group_message_sent').format(count=success_count))
    show_admin_panel(message)

def ask_for_scheduled_message(call):
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=get_text('enter_scheduled_message'),
                          reply_markup=types.InlineKeyboardMarkup().add(
                              types.InlineKeyboardButton(get_text('cancel'), callback_data="back_to_admin")
                          ))
    bot.register_next_step_handler(call.message, schedule_message)

def schedule_message(message):
    if message.text == get_text('cancel'):
        show_admin_panel(message)
        return

    try:
        text, date_time = message.text.rsplit('\n', 1)
        schedule_time = JalaliDateTime.strptime(date_time.strip(), "%Y-%m-%d %H:%M").togregorian()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO scheduled_messages (message, schedule_time) VALUES (?, ?)',
                       (text, schedule_time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

        bot.reply_to(message, get_text('message_scheduled').format(date_time=date_time))
    except ValueError:
        bot.reply_to(message, get_text('invalid_date_format'))

    show_admin_panel(message)

def ask_for_user_to_block(call):
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=get_text('enter_user_id_to_block'),
                          reply_markup=types.InlineKeyboardMarkup().add(
                              types.InlineKeyboardButton(get_text('cancel'), callback_data="back_to_admin")
                          ))
    bot.register_next_step_handler(call.message, block_user)

def block_user(message):
    if message.text == get_text('cancel'):
        show_admin_panel(message)
        return

    try:
        user_id = int(message.text)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO blocked_users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        conn.close()
        bot.reply_to(message, get_text('user_blocked').format(user_id=user_id))
    except ValueError:
        bot.reply_to(message, get_text('invalid_user_id'))

    show_admin_panel(message)

def ask_for_user_to_unblock(call):
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=get_text('enter_user_id_to_unblock'),
                          reply_markup=types.InlineKeyboardMarkup().add(
                              types.InlineKeyboardButton(get_text('cancel'), callback_data="back_to_admin")
                          ))
    bot.register_next_step_handler(call.message, unblock_user)

def unblock_user(message):
    if message.text == get_text('cancel'):
        show_admin_panel(message)
        return

    try:
        user_id = int(message.text)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM blocked_users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        bot.reply_to(message, get_text('user_unblocked').format(user_id=user_id))
    except ValueError:
        bot.reply_to(message, get_text('invalid_user_id'))

    show_admin_panel(message)

def check_scheduled_messages():
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute('SELECT id, message FROM scheduled_messages WHERE schedule_time <= ?', (now.strftime("%Y-%m-%d %H:%M:%S"),))
    scheduled_messages = cursor.fetchall()

    for message_id, message_text in scheduled_messages:
        send_group_message_to_all(message_text)
        cursor.execute('DELETE FROM scheduled_messages WHERE id = ?', (message_id,))

    conn.commit()
    conn.close()

def send_group_message_to_all(message_text):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()

    for user in users:
        try:
            bot.send_message(user[0], message_text)
        except Exception as e:
            logger.error(f"Error sending scheduled message to user {user[0]}: {e}")

def reset_lottery(call):
    global LOTTERY_ACTIVE
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users')
    cursor.execute('DELETE FROM channels')
    cursor.execute('UPDATE sqlite_sequence SET seq = 0 WHERE name = "users"')
    cursor.execute('UPDATE sqlite_sequence SET seq = 0 WHERE name = "channels"')
    conn.commit()
    conn.close()
    
    LOTTERY_ACTIVE = True
    bot.answer_callback_query(call.id, get_text('lottery_reset_success'))
    show_admin_panel(call.message)

# Start the bot
if __name__ == "__main__":
    schedule.every(1).minutes.do(check_scheduled_messages)
    while True:
        try:
            logger.info("Starting bot...")
            threading.Thread(target=bot.polling, kwargs={"none_stop": True}).start()
            while True:
                schedule.run_pending()
                time.sleep(1)
        except Exception as e:
            logger.error(f"Bot stopped due to error: {e}")
            time.sleep(10)
