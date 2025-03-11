import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import json

# Logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
COINGECKO_API = "https://api.coingecko.com/api/v3"
CURRENCIES = {
    'bitcoin': 'بیت‌کوین (BTC)', 
    'ethereum': 'اتریوم (ETH)', 
    'tether': 'تتر (USDT)', 
    'binancecoin': 'بایننس کوین (BNB)', 
    'solana': 'سولانا (SOL)', 
    'ripple': 'ریپل (XRP)', 
    'cardano': 'کاردانو (ADA)', 
    'dogecoin': 'دوج‌کوین (DOGE)', 
    'tron': 'ترون (TRX)', 
    'litecoin': 'لایت‌کوین (LTC)'
}
CHECK_INTERVAL = 60  # Check every 1 minute

# Language dictionaries
LANGUAGES = {
    'en': {
        'welcome': "Welcome to Crypto Bot!\nChoose an option:",
        'price': "Price",
        'set_alert': "Set Alert",
        'alerts_list': "View Alerts",
        'language': "Change Language",
        'current_price': "Current {coin} Price: ${price}",
        'change_24h': "24h Change: {change}%",
        'alert_set': "Alert set for {coin} at ${price}",
        'alert_triggered': "{coin} reached ${price}!\nCurrent price: ${current}",
        'select_coin': "Select a cryptocurrency:",
        'enter_price': "Enter target price for {coin}:",
        'alerts_empty': "You have no active alerts.",
        'alerts_title': "Your Active Alerts:"
    },
    'fa': {
        'welcome': "به ربات کریپتو خوش آمدید!\nیک گزینه را انتخاب کنید:",
        'price': "قیمت",
        'set_alert': "تنظیم هشدار",
        'alerts_list': "مشاهده هشدارها",
        'language': "تغییر زبان",
        'current_price': "قیمت فعلی {coin}: ${price}",
        'change_24h': "تغییر ۲۴ ساعته: {change}%",
        'alert_set': "هشدار برای {coin} در ${price} تنظیم شد",
        'alert_triggered': "{coin} به ${price} رسید!\nقیمت فعلی: ${current}",
        'select_coin': "یک ارز دیجیتال انتخاب کنید:",
        'enter_price': "قیمت هدف را برای {coin} وارد کنید:",
        'alerts_empty': "شما هیچ هشداری فعال ندارید.",
        'alerts_title': "هشدارهای فعال شما:"
    }
}

# Data storage
class Storage:
    def __init__(self):
        self.users = {}
        self.alerts = {}
        self.load_data()

    def load_data(self):
        if os.path.exists('data.json'):
            with open('data.json', 'r') as f:
                data = json.load(f)
                self.users = data.get('users', {})
                self.alerts = data.get('alerts', {})

    def save_data(self):
        with open('data.json', 'w') as f:
            json.dump({'users': self.users, 'alerts': self.alerts}, f)

storage = Storage()

# Get crypto price from CoinGecko
def get_crypto_price(coin_id):
    try:
        url = f"{COINGECKO_API}/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        price = data[coin_id]['usd']
        change_24h = round(data[coin_id]['usd_24h_change'], 2)
        logger.info(f"Fetched price for {coin_id}: ${price}")
        return price, change_24h
    except Exception as e:
        logger.error(f"Error fetching price for {coin_id}: {e}")
        return None, None

# Check alerts
async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    try:
        ids = ','.join(CURRENCIES.keys())
        url = f"{COINGECKO_API}/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        current_prices = {coin: data[coin]['usd'] for coin in CURRENCIES if coin in data}
    except Exception as e:
        logger.error(f"Error fetching prices in check_alerts: {e}")
        return

    for user_id, alerts in list(storage.alerts.items()):
        lang = storage.users.get(str(user_id), {}).get('lang', 'en')
        for alert in alerts[:]:
            coin, target_price = alert['coin'], alert['price']
            current_price = current_prices.get(coin)
            if current_price and (
                (target_price > alert['original_price'] and current_price >= target_price) or
                (target_price < alert['original_price'] and current_price <= target_price)
            ):
                await context.bot.send_message(
                    chat_id=user_id,
                    text=LANGUAGES[lang]['alert_triggered'].format(
                        coin=CURRENCIES[coin] if lang == 'fa' else coin.capitalize(),
                        price=target_price,
                        current=current_price
                    )
                )
                alerts.remove(alert)
    storage.save_data()

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in storage.users:
        storage.users[user_id] = {'lang': 'en'}
    lang = storage.users[user_id]['lang']
    
    keyboard = [
        [InlineKeyboardButton(LANGUAGES[lang]['price'], callback_data='price'),
         InlineKeyboardButton(LANGUAGES[lang]['set_alert'], callback_data='alert')],
        [InlineKeyboardButton(LANGUAGES[lang]['alerts_list'], callback_data='alerts_list'),
         InlineKeyboardButton(LANGUAGES[lang]['language'], callback_data='language')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(LANGUAGES[lang]['welcome'], reply_markup=reply_markup)

# Button handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    lang = storage.users[user_id]['lang']

    if query.data == 'price' or query.data == 'alert':
        keyboard = []
        coins = list(CURRENCIES.keys())
        for i in range(0, len(coins), 2):
            row = []
            row.append(InlineKeyboardButton(
                CURRENCIES[coins[i]] if lang == 'fa' else coins[i].capitalize(),
                callback_data=f"{query.data}_{coins[i]}"
            ))
            if i + 1 < len(coins):
                row.append(InlineKeyboardButton(
                    CURRENCIES[coins[i+1]] if lang == 'fa' else coins[i+1].capitalize(),
                    callback_data=f"{query.data}_{coins[i+1]}"
                ))
            keyboard.append(row)
        await query.edit_message_text(
            LANGUAGES[lang]['select_coin'],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == 'alerts_list':
        alerts = storage.alerts.get(user_id, [])
        if not alerts:
            await query.edit_message_text(LANGUAGES[lang]['alerts_empty'])
        else:
            alert_list = [LANGUAGES[lang]['alerts_title']]
            for alert in alerts:
                coin_name = CURRENCIES[alert['coin']] if lang == 'fa' else alert['coin'].capitalize()
                alert_list.append(f"{coin_name}: ${alert['price']}")
            await query.edit_message_text("\n".join(alert_list))

    elif query.data == 'language':
        keyboard = [
            [InlineKeyboardButton("English", callback_data='lang_en'),
             InlineKeyboardButton("فارسی", callback_data='lang_fa')]
        ]
        await query.edit_message_text(
            "Select language / زبان را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith('price_'):
        coin = query.data.split('_')[1]
        price, change = get_crypto_price(coin)
        if price:
            coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
            await query.edit_message_text(
                f"{LANGUAGES[lang]['current_price'].format(coin=coin_name, price=price)}\n"
                f"{LANGUAGES[lang]['change_24h'].format(change=change)}"
            )

    elif query.data.startswith('alert_'):
        coin = query.data.split('_')[1]
        context.user_data['alert_coin'] = coin
        coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
        await query.edit_message_text(LANGUAGES[lang]['enter_price'].format(coin=coin_name))

    elif query.data.startswith('lang_'):
        new_lang = query.data.split('_')[1]
        storage.users[user_id]['lang'] = new_lang
        storage.save_data()
        keyboard = [
            [InlineKeyboardButton(LANGUAGES[new_lang]['price'], callback_data='price'),
             InlineKeyboardButton(LANGUAGES[new_lang]['set_alert'], callback_data='alert')],
            [InlineKeyboardButton(LANGUAGES[new_lang]['alerts_list'], callback_data='alerts_list'),
             InlineKeyboardButton(LANGUAGES[new_lang]['language'], callback_data='language')]
        ]
        await query.edit_message_text(
            LANGUAGES[new_lang]['welcome'],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Handle price input for alerts
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'alert_coin' in context.user_data:
        user_id = str(update.effective_user.id)
        lang = storage.users[user_id]['lang']
        coin = context.user_data['alert_coin']
        
        try:
            target_price = float(update.message.text)
            current_price, _ = get_crypto_price(coin)
            if current_price is None:
                raise ValueError("Could not fetch current price")
            
            if user_id not in storage.alerts:
                storage.alerts[user_id] = []
            storage.alerts[user_id].append({
                'coin': coin,
                'price': target_price,
                'original_price': current_price
            })
            storage.save_data()
            
            coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
            await update.message.reply_text(
                LANGUAGES[lang]['alert_set'].format(coin=coin_name, price=target_price)
            )
            del context.user_data['alert_coin']
        except ValueError as e:
            await update.message.reply_text("Please enter a valid number" if lang == 'en' else "لطفاً یک عدد معتبر وارد کنید")

def main():
    application = Application.builder().token('8003905325:AAGaLlv41FUe9RgHjFmeNDLrxSQAcWO7KXE').build()
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_alerts, 'interval', seconds=CHECK_INTERVAL, args=[application])
    scheduler.start()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
