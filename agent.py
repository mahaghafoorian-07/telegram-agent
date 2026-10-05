import os
import telebot
import jdatetime
from datetime import datetime
import threading
import time
import re

# تنظیمات ربات و کانال شما
TOKEN = "8718846217:AAHjbJICPIbRY2OfyvJ4BiEc0C7u5mnKvSw"
CHANNEL_ID = "@testpublish23423"

bot = telebot.TeleBot(TOKEN)

# ذخیره موقت پیش‌نویس کاربران و صف زمان‌بندی
user_drafts = {}
scheduled_queue = []

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 سلام!\n\nبرای ارسال پست، ابتدا **عکس همراه با متن** یا فقط **متن** خود را بفرستید.")

@bot.message_handler(content_types=['photo', 'text'])
def handle_user_input(message):
    chat_id = message.chat.id
    
    # ۱. اگر کاربر عکس همراه با متن فرستاد
    if message.content_type == 'photo':
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        os.makedirs("downloads", exist_ok=True)
        image_path = f"downloads/{chat_id}.jpg"
        with open(image_path, 'wb') as f:
            f.write(downloaded_file)
            
        caption = message.caption or ""
        user_drafts[chat_id] = {
            "image": image_path,
            "caption": caption
        }
        bot.reply_to(message, "✅ عکس و متن دریافت شد.\n\nاکنون **ساعت انتشار** (مثلاً `14:30`) یا **تاریخ و ساعت** (مثلاً `1405/07/13 14:30`) را بفرستید.")
        
    # ۲. اگر کاربر متن فرستاد
    elif message.content_type == 'text':
        text = message.text.strip()
        
        # اگر پیش‌نویس فعالی ندارد، این متن را به عنوان کپشن ثبت می‌کنیم
        if chat_id not in user_drafts:
            user_drafts[chat_id] = {
                "image": None,
                "caption": text
            }
            bot.reply_to(message, "✅ متن دریافت شد.\n\nاکنون **ساعت انتشار** (مثلاً `14:30`) را بفرستید.")
        
        # اگر پیش‌نویس دارد، یعنی متن دوم زمان انتشار است
        else:
            draft = user_drafts[chat_id]
            target_time = parse_target_time(text)
            
            if target_time:
                scheduled_queue.append({
                    "time": target_time,
                    "caption": draft["caption"],
                    "image": draft["image"]
                })
                bot.reply_to(message, f"🎉 پست با موفقیت در صف زمان‌‌سنج ثبت شد!\n\n⏰ زمان انتشار: `{target_time.strftime('%Y-%m-%d %H:%M')}`")
                del user_drafts[chat_id] # پاک کردن پیش‌نویس برای پست‌های بعدی
            else:
                bot.reply_to(message, "❌ فرمت زمان اشتباه است. لطفاً به صورت `14:30` یا `1405/07/13 14:30` وارد کنید.")

def parse_target_time(text):
    """تابع هوشمند برای خواندن ساعت و تاریخ شمسی یا میلادی"""
    try:
        now = datetime.now()
        target_date = now.date()
        target_hour, target_minute = now.hour, now.minute + 1 # پیش‌فرض: یک دقیقه بعد
        
        # استخراج ساعت (مثل 14:30)
        time_match = re.search(r'(\d{1,2}):(\d{2})', text)
        if time_match:
            target_hour = int(time_match.group(1))
            target_minute = int(time_match.group(2))
            
        # استخراج تاریخ شمسی (مثل 1405/07/13)
        jalali_match = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', text)
        if jalali_match:
            jy, jm, jd = map(int, jalali_match.groups())
            target_date = jdatetime.date(jy, jm, jd).togregorian()
            
        return datetime(target_date.year, target_date.month, target_date.day, target_hour, target_minute, 0)
    except Exception as e:
        print(f"خطا در تحلیل زمان: {e}")
        return None

def background_scheduler():
    """نخ پس‌زمینه برای بررسی ثانیه‌ای صف و انتشار سر ساعت"""
    print("⏰ سیستم زمان‌سنج دقیق (Scheduler Thread) روشن شد...")
    while True:
        now = datetime.now()
        for item in scheduled_queue[:]:
            if now >= item["time"]:
                print(f"🚀 زمان انتشار فرا رسید! در حال ارسال به کانال {CHANNEL_ID}...")
                try:
                    # بدون parse_mode تا هیچ خطای کاراکتر خاصی رخ ندهد
                    if item["image"] and os.path.exists(item["image"]):
                        with open(item["image"], 'rb') as photo:
                            bot.send_photo(CHANNEL_ID, photo, caption=item["caption"])
                    else:
                        bot.send_message(CHANNEL_ID, item["caption"])
                    print("✅ پست با موفقیت در کانال منتشر شد!")
                except Exception as e:
                    print(f"❌ خطا در ارسال به کانال: {e}")
                
                scheduled_queue.remove(item)
        time.sleep(1)

if __name__ == '__main__':
    # روشن کردن بخش زمان‌سنج در پشت صحنه
    t = threading.Thread(target=background_scheduler, daemon=True)
    t.start()
    
    print("🤖 ربات تلگرام با معماری استاندارد pyTelegramBotAPI روشن شد و آماده دریافت پیام است...")
    bot.infinity_polling()