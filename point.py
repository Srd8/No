# coding:utf-8
import os
import json
import requests
import telebot

# --- إعدادات البوت والسيرفر ---
BOT_TOKEN = "8739832337:AAGrfscEf9BjwCZLA8226cZJlcZ-j2UpqHQ"
SMM_API_URL = "https://kd1s.com/api/v2"
SMM_API_KEY = "427ee2c3a61c3377ab42629671e85e91"
INSTAGRAM_SERVICE_ID = "15670"

# --- إعدادات نظام النقاط المحدثة ---
MIN_QTY = 10
MAX_QTY = 500000
POINTS_PER_INVITE = 1000000000   # تم تعديل المكافأة إلى 1,000,000,000 نقطة لكل دعوة
COST_PER_FOLLOWER = 1          # تكلفة المتابع الواحد بالنقاط (1 متابع = 1 نقطة)

bot = telebot.TeleBot(BOT_TOKEN)

DB_FILE = "users_data.json"
user_sessions = {}

# --- وظائف قاعدة البيانات ---
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def init_user(user_id, username=""):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "points": 0,
            "username": username,
            "invited_by": None
        }
        save_data(data)
    return data

# --- إدارة الأوامر ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    username = message.from_user.username or ""
    text_args = message.text.split()
    
    # تهيئة بيانات المستخدم الجديد
    db_data = init_user(user_id, username)
    
    # التحقق من وجود دعوة
    if len(text_args) > 1 and text_args[1].isdigit():
        referrer_id = text_args[1]
        uid_str = str(user_id)
        
        # التأكد من أنه شخص جديد ولم يتم دعوته من قبل ولا يدعو نفسه
        if db_data[uid_str]["invited_by"] is None and referrer_id != uid_str:
            all_data = load_data()
            if referrer_id in all_data:
                # إضافة المليار نقطة للشخص الداعي
                all_data[referrer_id]["points"] += POINTS_PER_INVITE
                all_data[uid_str]["invited_by"] = referrer_id
                save_data(all_data)
                
                # إشعار الشخص الذي قام بالدعوة
                try:
                    bot.send_message(referrer_id, f"🎉 دخل شخص جديد للبوت عن طريق رابطك! تم إضافة **{POINTS_PER_INVITE:,}** نقطة إلى رصيدك.")
                except Exception:
                    pass

    # تحديث البيانات لعرض الرصيد الحالي
    db_data = load_data()
    current_points = db_data[str(user_id)]["points"]
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

    welcome_text = (
        f"👋 مرحبًا بك في بوت رشق المتابعين بنظام النقاط!\n\n"
        f"💰 **رصيد نقاطك الحالي:** `{current_points:,}` نقطة.\n"
        f"📌 **سعر الخدمة:** {COST_PER_FOLLOWER} نقطة لكل متابع واحد.\n\n"
        f"🔗 **رابط الدعوة الخاص بك:**\n`{ref_link}`\n\n"
        f"قم بمشاركة الرابط مع أصدقائك، وبمجرد دخول أي شخص ستحصل على **{POINTS_PER_INVITE:,}** نقطة مجاناً!\n\n"
        f"👇 لإرسال طلب، أرسل الآن **رابط حساب الانستقرام**:"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")
    user_sessions[user_id] = {'step': 'awaiting_link'}


# الخطوة الأولى: استقبال الرابط
@bot.message_handler(func=lambda message: user_sessions.get(message.chat.id, {}).get('step') == 'awaiting_link')
def process_link(message):
    chat_id = message.chat.id
    target_link = message.text.strip()
    
    if target_link.startswith('/'):
        return

    user_sessions[chat_id] = {
        'step': 'awaiting_quantity',
        'link': target_link
    }
    
    bot.reply_to(message, f"🔢 تمام، أرسل الآن **الكمية المطلوبة**\n(يجب أن تكون بين {MIN_QTY} و {MAX_QTY:,}):")


# الخطوة الثانية: فحص النقاط والكمية وإرسال الطلب
@bot.message_handler(func=lambda message: user_sessions.get(message.chat.id, {}).get('step') == 'awaiting_quantity')
def process_quantity(message):
    chat_id = message.chat.id
    quantity = message.text.strip()
    
    if quantity.startswith('/'):
        return

    if not quantity.isdigit():
        bot.reply_to(message, "❌ عذرًا، يجب إدخال الكمية كأرقام فقط. أعد إدخال الكمية:")
        return

    int_qty = int(quantity)

    # 1. التحقق من حدود السيرفر
    if int_qty < MIN_QTY or int_qty > MAX_QTY:
        bot.reply_to(message, f"⚠️ الكمية غير مسموح بها بالسيرفر!\nيجب أن تكون بين **{MIN_QTY}** و **{MAX_QTY:,}**.")
        return

    # 2. حساب تكلفة النقاط والتحقق من رصيد المستخدم
    needed_points = int_qty * COST_PER_FOLLOWER
    db_data = load_data()
    user_points = db_data[str(chat_id)]["points"]

    if user_points < needed_points:
        bot.reply_to(message, f"❌ رصيد نقاطك غير كافٍ!\n\n"
                              f"📊 الكمية المطلوبة: {int_qty:,} متابع.\n"
                              f"💎 النقاط المطلوبة: {needed_points:,} نقطة.\n"
                              f"💰 رصيدك الحالي: {user_points:,} نقطة.\n\n"
                              f"قم بنشر رابط الإحالة الخاص بك لتجميع النقاط أولاً!")
        user_sessions.pop(chat_id, None)
        return

    user_data = user_sessions[chat_id]
    target_link = user_data['link']
    
    bot.reply_to(message, f"🔄 رصيدك كافٍ! جاري إرسال الطلب إلى السيرفر الرئيسي...")
    
    # تجهيز بيانات السيرفر
    api_payload = {
        'key': SMM_API_KEY,
        'action': 'add',
        'service': INSTAGRAM_SERVICE_ID,
        'link': target_link,
        'quantity': int_qty
    }
    
    try:
        response = requests.post(SMM_API_URL, data=api_payload, timeout=15)
        response_data = response.json()
        
        if "order" in response_data:
            order_id = response_data["order"]
            
            # خصم النقاط من رصيد المستخدم في قاعدة البيانات وحفظها
            db_data[str(chat_id)]["points"] -= needed_points
            save_data(db_data)
            
            success_message = (
                f"✅ **تم إرسال الطلب بنجاح!**\n\n"
                f"🆔 رقم الطلب: `{order_id}`\n"
                f"📊 الكمية: {int_qty:,} متابع.\n"
                f"📉 تم خصم: {needed_points:,} نقطة.\n"
                f"💰 رصيدك المتبقي: {db_data[str(chat_id)]['points']:,} نقطة.\n\n"
                f"يتم الآن التنفيذ تلقائيًا."
            )
            bot.send_message(chat_id, success_message, parse_mode="Markdown")
        elif "error" in response_data:
            bot.send_message(chat_id, f"❌ رفض السيرفر الطلب بسبب:\n`{response_data['error']}`", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"⚠️ استجابة غير معروفة:\n`{response.text}`", parse_mode="Markdown")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ حدث خطأ غير متوقع: {str(e)}")
        
    user_sessions.pop(chat_id, None)

# تشغيل البوت
if __name__ == "__main__":
    print("🤖 البوت يعمل بنظام المليار نقطة لكل دعوة...")
    bot.infinity_polling()
