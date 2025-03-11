from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import logging
import json
import os

# Logging configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
COINGECKO_API = "https://api.coingecko.com/api/v3"
CURRENCIES = [
    'bitcoin',        # بیت‌کوین (BTC)
    'ethereum',       # اتریوم (ETH)
    'tether',         # تتر (USDT) - استیبل‌کوین
    'binancecoin',    # بایننس کوین (BNB)
    'solana',         # سولانا (SOL)
    'ripple',         # ریپل (XRP)
    'cardano',        # کاردانو (ADA)
    'dogecoin',       # دوج‌کوین (DOGE)
    'tron',           # ترون (TRX)
    'avalanche-2',    # آوالانچ (AVAX)
    'shiba-inu',      # شیبا اینو (SHIB)
    'polkadot',       # پولکادات (DOT)
    'chainlink',      # چین‌لینک (LINK)
    'matic-network',  # پالیگان (MATIC)
    'uniswap',        # یونی‌سواپ (UNI)
    'litecoin',       # لایت‌کوین (LTC)
    'near',           # نیر پروتکل (NEAR)
    'aptos',          # آپتوس (APT)
    'cosmos',         # کازموس (ATOM)
    'stellar',        # استلار (XLM)
    'arbitrum',       # آربیتروم (ARB)
    'optimism',       # آپتیمیزم (OP)
    'filecoin',       # فایل‌کوین (FIL)
    'hedera-hashgraph', # هدرا (HBAR)
    'vechain',        # وی‌چین (VET)
    'injective-protocol', # اینجکتیو (INJ)
    'algorand',       # الگوراند (ALGO)
    'quant-network',  # کوانت (QNT)
    'maker',          # میکر (MKR)
    'aave',           # آوه (AAVE)
]
CHECK_INTERVAL = 300  # Check every 5 minutes (in seconds)

# Language dictionaries
LANGUAGES = {
    'en': {
        'welcome': "Welcome to Crypto Bot!\nChoose an option:",
        'price': "Price",
        'set_alert': "Set Alert",
        'language': "Change Language",
        'current_price': "Current {coin} Price: ${price}\n24h Change: {change}%",
        'alert_set': "Alert set for {coin} at ${price}",
        'alert_triggered': "{coin} reached ${price}!\nCurrent price: ${current}",
        'select_coin': "Select a cryptocurrency:",
        'enter_price': "Enter target price for {coin}:"
    },
    'fa': {
        'welcome': "به ربات کریپتو خوش آمدید!\nیک گزینه را انتخاب کنید:",
        'price': "قیمت",
        'set_alert': "تنظیم هشدار",
        'language': "تغییر زبان",
        'current_price': "قیمت فعلی {coin}: ${price}\nتغییر ۲۴ ساعته: {change}%",
        'alert_set': "هشدار برای {coin} در قیمت ${price} تنظیم شد",
        'alert_triggered': "{coin} به ${price} رسید!\nقیمت فعلی: ${current}",
        'select_coin': "یک ارز دیجیتال انتخاب کنید:",
        'enter_price': "قیمت هدف را برای {coin} وارد کنید:"
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
        data = response.json()
        price = data[coin_id]['usd']
        change_24h = round(data[coin_id]['usd_24h_change'], 2)
        return price, change_24h
    except Exception as e:
        logger.error(f"Error fetching price: {e}")
        return None, None

# Check alerts
async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    current_prices = {}
    for coin in CURRENCIES:
        price, _ = get_crypto_price(coin)
        if price:
            current_prices[coin] = price

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
                        coin=coin.capitalize(), 
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
        [InlineKeyboardButton(LANGUAGES[lang]['language'], callback_data='language')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(LANGUAGES[lang]['welcome'], reply_markup=reply_markup)

# Button handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    lang = storage.users[user_id]['lang']

    if query.data == 'price':
        keyboard = [[InlineKeyboardButton(coin.capitalize(), callback_data=f'price_{coin}')] for coin in CURRENCIES]
        await query.edit_message_text(
            LANGUAGES[lang]['select_coin'],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data == 'alert':
        keyboard = [[InlineKeyboardButton(coin.capitalize(), callback_data=f'alert_{coin}')] for coin in CURRENCIES]
        await query.edit_message_text(
            LANGUAGES[lang]['select_coin'],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
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
            await query.edit_message_text(
                LANGUAGES[lang]['current_price'].format(
                    coin=coin.capitalize(),
                    price=price,
                    change=change
                )
            )
    
    elif query.data.startswith('alert_'):
        coin = query.data.split('_')[1]
        context.user_data['alert_coin'] = coin
        await query.edit_message_text(LANGUAGES[lang]['enter_price'].format(coin=coin.capitalize()))
    
    elif query.data.startswith('lang_'):
        new_lang = query.data.split('_')[1]
        storage.users[user_id]['lang'] = new_lang
        storage.save_data()
        await start(update, context)

# Handle price input for alerts
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'alert_coin' in context.user_data:
        user_id = str(update.effective_user.id)
        lang = storage.users[user_id]['lang']
        coin = context.user_data['alert_coin']
        
        try:
            target_price = float(update.message.text)
            current_price, _ = get_crypto_price(coin)
            
            if user_id not in storage.alerts:
                storage.alerts[user_id] = []
            storage.alerts[user_id].append({
                'coin': coin,
                'price': target_price,
                'original_price': current_price
            })
            storage.save_data()
            
            await update.message.reply_text(
                LANGUAGES[lang]['alert_set'].format(coin=coin.capitalize(), price=target_price)
            )
            del context.user_data['alert_coin']
        except ValueError:
            await update.message.reply_text("Please enter a valid number")

def main():
    application = Application.builder().token('8003905325:AAGaLlv41FUe9RgHjFmeNDLrxSQAcWO7KXE').build()
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_alerts, 'interval', seconds=CHECK_INTERVAL, args=[application])
    scheduler.start()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
