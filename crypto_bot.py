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
CHECK_INTERVAL = 180  # Check every 3 minutes
USD_TO_IRR = 930000  # 930,000 IRR per USD

# 100 popular cryptocurrencies
CURRENCIES = {
    'bitcoin': 'بیت‌کوین (BTC)', 'ethereum': 'اتریوم (ETH)', 'tether': 'تتر (USDT)', 'binancecoin': 'بایننس کوین (BNB)',
    'solana': 'سولانا (SOL)', 'ripple': 'ریپل (XRP)', 'cardano': 'کاردانو (ADA)', 'dogecoin': 'دوج‌کوین (DOGE)',
    'tron': 'ترون (TRX)', 'litecoin': 'لایت‌کوین (LTC)', 'shiba-inu': 'شیبا اینو (SHIB)', 'polkadot': 'پولکادات (DOT)',
    'chainlink': 'چین‌لینک (LINK)', 'matic-network': 'پالیگان (MATIC)', 'uniswap': 'یونی‌سواپ (UNI)', 'avalanche-2': 'آوالانچ (AVAX)',
    'stellar': 'استلار (XLM)', 'cosmos': 'کازموس (ATOM)', 'near': 'نیر پروتکل (NEAR)', 'aptos': 'آپتوس (APT)',
    'filecoin': 'فایل‌کوین (FIL)', 'arbitrum': 'آربیتروم (ARB)', 'optimism': 'آپتیمیزم (OP)', 'hedera-hashgraph': 'هدرا (HBAR)',
    'vechain': 'وی‌چین (VET)', 'injective-protocol': 'اینجکتیو (INJ)', 'algorand': 'الگوراند (ALGO)', 'quant-network': 'کوانت (QNT)',
    'maker': 'میکر (MKR)', 'aave': 'آوه (AAVE)', 'the-graph': 'گراف (GRT)', 'fantom': 'فانتوم (FTM)',
    'thorchain': 'تورچین (RUNE)', 'lido-dao': 'لیدو دائو (LDO)', 'render-token': 'رندر (RNDR)', 'immutable-x': 'ایمیوتبل ایکس (IMX)',
    'celestia': 'سلستیا (TIA)', 'sui': 'سوی (SUI)', 'bittensor': 'بیت‌تنسور (TAO)', 'kaspa': 'کاسپا (KAS)',
    'pepe': 'پپه (PEPE)', 'dydx': 'دی‌وای‌دی‌ایکس (DYDX)', 'worldcoin-wld': 'ورلدکوین (WLD)', 'cronos': 'کرونوس (CRO)',
    'kava': 'کاوا (KAVA)', 'flow': 'فلو (FLOW)', 'gala': 'گالا (GALA)', 'eos': 'ایاس (EOS)',
    'tezos': 'تزوس (XTZ)', 'neo': 'نئو (NEO)', 'iota': 'آیوتا (IOTA)', 'elrond-erd-2': 'الروند (EGLD)',
    'chiliz': 'چلیز (CHZ)', 'oasis-network': 'اوئیسیس (ROSE)', 'mina-protocol': 'مینا (MINA)', 'klaytn': 'کلایتن (KLAY)',
    'terra-luna': 'ترا لونا (LUNA)', 'axie-infinity': 'اکسی اینفینیتی (AXS)', 'decentraland': 'دیسنترالند (MANA)', 'sand': 'سندباکس (SAND)',
    'curve-dao-token': 'کرو دائو (CRV)', 'compound-governance-token': 'کامپاوند (COMP)', 'synthetix-network-token': 'سینتتیکس (SNX)', '1inch': 'وان‌اینچ (1INCH)',
    'pancakeswap-token': 'پنکیک‌سواپ (CAKE)', 'trust-wallet-token': 'تراست ولت (TWT)', 'rocket-pool': 'راکت پول (RPL)', 'gnosis': 'گنوزیس (GNO)',
    'basic-attention-token': 'بت (BAT)', 'zcash': 'زی‌کش (ZEC)', 'dash': 'دش (DASH)', 'nem': 'نِم (XEM)',
    'waves': 'ویوز (WAVES)', 'siacoin': 'سیاکوین (SC)', 'ontology': 'آنتوژی (ONT)', 'qtum': 'کوانتوم (QTUM)',
    'icon': 'آیکون (ICX)', 'ravencoin': 'ریون‌کوین (RVN)', 'zilliqa': 'زیلیکا (ZIL)', '0x': 'زیروایکس (ZRX)',
    'audius': 'آدیوس (AUDIO)', 'ankr': 'انکر (ANKR)', 'balancer': 'بالانسر (BAL)', 'yearn-finance': 'یرن فایننس (YFI)',
    'uma': 'اوما (UMA)', 'harmony': 'هارمونی (ONE)', 'wax': 'وکس (WAXP)', 'hive': 'هایو (HIVE)',
    'steem': 'استیم (STEEM)', 'digibyte': 'دیجی‌بایت (DGB)', 'nano': 'نانو (XNO)', 'storj': 'استورج (STORJ)',
    'livepeer': 'لایوپیر (LPT)', 'skale': 'اسکیل (SKL)', 'numeraire': 'نومریر (NMR)', 'api3': 'ای‌پی‌آی‌تری (API3)',
    'band-protocol': 'بند پروتکل (BAND)', 'cartesi': 'کارتزی (CTSI)', 'orchid-protocol': 'ارکید (OXT)', 'nkn': 'ان‌کی‌ان (NKN)'
}

# Language dictionaries
LANGUAGES = {
    'en': {
        'welcome': "Welcome to Crypto Bot!\nChoose an option:",
        'price': "Price",
        'set_alert': "Set Alert",
        'alerts_list': "View Alerts",
        'language': "Change Language",
        'chart': "Chart",
        'daily_report': "Daily Report: {status}",
        'convert_to_irr': "Convert to IRR",
        'developer': "About Developer",
        'search': "Search Coin",
        'my_data': "My Data",
        'current_price': "📊 Current {coin} Price: ${price}",
        'change_24h': "📈 24h Change: {change}%",
        'price_in_irr': "💵 {coin} Price in IRR: {price_irr:,} IRR",
        'alert_set': "✅ Alert set for {coin} at ${price}",
        'alert_triggered': "⚠️ {coin} reached ${price}!\nCurrent price: ${current}",
        'select_coin': "Select a cryptocurrency (Page {page}/{total_pages}):",
        'enter_price': "Enter target price for {coin}:",
        'alerts_empty': "You have no active alerts.",
        'alerts_title': "Your Active Alerts:",
        'delete_alert': "Delete",
        'chart_link': "View {coin} chart: {url}",
        'daily_on': "ON",
        'daily_off': "OFF",
        'daily_report_text': "📅 Daily Crypto Report:",
        'search_prompt': "Enter coin name (English or Persian):",
        'search_result': "Found: {coin}",
        'search_no_result': "No coin found!",
        'prev_page': "Previous",
        'next_page': "Next",
        'my_data_title': "Your Data ({last_name}):",
        'my_data_lang': "Language: {lang}",
        'my_data_report': "Daily Report: {status}",
        'my_data_alerts': "Alerts:\n{alerts}",
        'developer_info': (
            "👩‍💻 Developer Information:\n"
            "Name: Sara Rad\n"
            "Telegram ID: @SaraRad\n"
            "Project Goal: Build a crypto tracking bot for educational purposes\n"
            "University: Al-Zahra University, Kerman\n"
            "Supervisor: Dr. Ali Mohammadi\n"
            "Student ID: 140123456\n"
            "Date: Spring 2024"
        )
    },
    'fa': {
        'welcome': "به ربات کریپتو خوش آمدید!\nیک گزینه را انتخاب کنید:",
        'price': "قیمت",
        'set_alert': "تنظیم هشدار",
        'alerts_list': "مشاهده هشدارها",
        'language': "تغییر زبان",
        'chart': "نمودار",
        'daily_report': "گزارش روزانه: {status}",
        'convert_to_irr': "تبدیل به ریال",
        'developer': "معرفی توسعه‌دهنده",
        'search': "جستجوی ارز",
        'my_data': "داده‌های من",
        'current_price': "📊 قیمت فعلی {coin}: ${price}",
        'change_24h': "📈 تغییر ۲۴ ساعته: {change}%",
        'price_in_irr': "💵 قیمت {coin} به ریال: {price_irr:,} IRR",
        'alert_set': "✅ هشدار برای {coin} در ${price} تنظیم شد",
        'alert_triggered': "⚠️ {coin} به ${price} رسید!\nقیمت فعلی: ${current}",
        'select_coin': "یک ارز دیجیتال انتخاب کنید (صفحه {page}/{total_pages}):",
        'enter_price': "قیمت هدف را برای {coin} وارد کنید:",
        'alerts_empty': "شما هیچ هشداری فعال ندارید.",
        'alerts_title': "هشدارهای فعال شما:",
        'delete_alert': "حذف",
        'chart_link': "مشاهده نمودار {coin}: {url}",
        'daily_on': "روشن",
        'daily_off': "خاموش",
        'daily_report_text': "📅 گزارش روزانه کریپتو:",
        'search_prompt': "نام ارز را وارد کنید (فارسی یا انگلیسی):",
        'search_result': "پیدا شد: {coin}",
        'search_no_result': "ارزی پیدا نشد!",
        'prev_page': "قبلی",
        'next_page': "بعدی",
        'my_data_title': "داده‌های شما ({last_name}):",
        'my_data_lang': "زبان: {lang}",
        'my_data_report': "گزارش روزانه: {status}",
        'my_data_alerts': "هشدارها:\n{alerts}",
        'developer_info': (
            "👩‍💻 اطلاعات توسعه‌دهنده:\n"
            "نام: سارا راد\n"
            "آیدی تلگرام: @SaraRad\n"
            "هدف پروژه: ساخت ربات ردیابی کریپتو برای اهداف آموزشی\n"
            "دانشگاه: دانشگاه الزهرا، کرمان\n"
            "استاد راهنما: دکتر علی محمدی\n"
            "شماره دانشجویی: ۱۴۰۱۲۳۴۵۶\n"
            "تاریخ: بهار ۱۴۰۳"
        )
    }
}

# Data storage with JSON
class Storage:
    def __init__(self):
        self.users = {}
        self.alerts = {}
        self.load_data()

    def load_data(self):
        if os.path.exists('/app/data.json'):  # For Railway Volume
            with open('/app/data.json', 'r') as f:
                data = json.load(f)
                self.users = data.get('users', {})
                self.alerts = data.get('alerts', {})

    def save_data(self):
        with open('/app/data.json', 'w') as f:
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

# Daily report
async def daily_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        ids = ','.join(CURRENCIES.keys())
        url = f"{COINGECKO_API}/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url)
        data = response.json()
        prices = {coin: data[coin]['usd'] for coin in CURRENCIES if coin in data}
    except Exception as e:
        logger.error(f"Error fetching prices for daily report: {e}")
        return

    for user_id, user_data in storage.users.items():
        if user_data.get('daily_report', False):
            lang = user_data.get('lang', 'en')
            report = [LANGUAGES[lang]['daily_report_text']]
            for coin, price in list(prices.items())[:10]:
                coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
                report.append(f"{coin_name}: ${price}")
            await context.bot.send_message(chat_id=user_id, text="\n".join(report))

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    last_name = update.effective_user.last_name or "Unknown"  # Get last name from profile
    if user_id not in storage.users:
        storage.users[user_id] = {'lang': 'en', 'daily_report': False, 'last_name': last_name}
    elif 'last_name' not in storage.users[user_id]:  # Update last_name if not present
        storage.users[user_id]['last_name'] = last_name
    lang = storage.users[user_id]['lang']
    daily_status = LANGUAGES[lang]['daily_on'] if storage.users[user_id]['daily_report'] else LANGUAGES[lang]['daily_off']
    
    # Log current data
    logger.info(f"Current data: {json.dumps(storage.users, indent=2, ensure_ascii=False)}")
    logger.info(f"Current alerts: {json.dumps(storage.alerts, indent=2, ensure_ascii=False)}")
    
    keyboard = [
        [InlineKeyboardButton(LANGUAGES[lang]['price'], callback_data='price_0'),
         InlineKeyboardButton(LANGUAGES[lang]['set_alert'], callback_data='alert_0')],
        [InlineKeyboardButton(LANGUAGES[lang]['alerts_list'], callback_data='alerts_list'),
         InlineKeyboardButton(LANGUAGES[lang]['chart'], callback_data='chart_0')],
        [InlineKeyboardButton(LANGUAGES[lang]['daily_report'].format(status=daily_status), callback_data='toggle_daily'),
         InlineKeyboardButton(LANGUAGES[lang]['convert_to_irr'], callback_data='convert_to_irr_0')],
        [InlineKeyboardButton(LANGUAGES[lang]['search'], callback_data='search'),
         InlineKeyboardButton(LANGUAGES[lang]['developer'], callback_data='developer')],
        [InlineKeyboardButton(LANGUAGES[lang]['my_data'], callback_data='my_data'),
         InlineKeyboardButton(LANGUAGES[lang]['language'], callback_data='language')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(LANGUAGES[lang]['welcome'], reply_markup=reply_markup)
    storage.save_data()

# Button handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    lang = storage.users[user_id]['lang']
    coins = list(CURRENCIES.keys())
    items_per_page = 10
    total_pages = (len(coins) + items_per_page - 1) // items_per_page

    if query.data.startswith(('price_', 'alert_', 'chart_', 'convert_to_irr_')):
        action, page = query.data.split('_')[0], int(query.data.split('_')[1])
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(coins))
        keyboard = []
        for i in range(start_idx, end_idx, 2):
            row = []
            row.append(InlineKeyboardButton(
                CURRENCIES[coins[i]] if lang == 'fa' else coins[i].capitalize(),
                callback_data=f"{action}_{coins[i]}"
            ))
            if i + 1 < end_idx:
                row.append(InlineKeyboardButton(
                    CURRENCIES[coins[i+1]] if lang == 'fa' else coins[i+1].capitalize(),
                    callback_data=f"{action}_{coins[i+1]}"
                ))
            keyboard.append(row)
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(LANGUAGES[lang]['prev_page'], callback_data=f"{action}_{page-1}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(LANGUAGES[lang]['next_page'], callback_data=f"{action}_{page+1}"))
        if nav_row:
            keyboard.append(nav_row)
        await query.edit_message_text(
            LANGUAGES[lang]['select_coin'].format(page=page+1, total_pages=total_pages),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == 'alerts_list':
        alerts = storage.alerts.get(user_id, [])
        if not alerts:
            await query.edit_message_text(LANGUAGES[lang]['alerts_empty'])
        else:
            alert_list = [LANGUAGES[lang]['alerts_title']]
            for i, alert in enumerate(alerts):
                coin_name = CURRENCIES[alert['coin']] if lang == 'fa' else alert['coin'].capitalize()
                alert_list.append(f"{coin_name}: ${alert['price']}  [{LANGUAGES[lang]['delete_alert']}](callback_data='delete_alert_{i}')")
            await query.edit_message_text("\n".join(alert_list), parse_mode='Markdown')

    elif query.data.startswith('delete_alert_'):
        alert_index = int(query.data.split('_')[2])
        alerts = storage.alerts.get(user_id, [])
        if 0 <= alert_index < len(alerts):
            alerts.pop(alert_index)
            storage.save_data()
        await button(update, context)

    elif query.data == 'language':
        keyboard = [
            [InlineKeyboardButton("English", callback_data='lang_en'),
             InlineKeyboardButton("فارسی", callback_data='lang_fa')]
        ]
        await query.edit_message_text(
            "Select language / زبان را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith('price_') and len(query.data.split('_')) == 2:
        coin = query.data.split('_')[1]
        price, change = get_crypto_price(coin)
        if price:
            coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
            await query.edit_message_text(
                f"{LANGUAGES[lang]['current_price'].format(coin=coin_name, price=price)}\n"
                f"{LANGUAGES[lang]['change_24h'].format(change=change)}"
            )

    elif query.data.startswith('alert_') and len(query.data.split('_')) == 2:
        coin = query.data.split('_')[1]
        context.user_data['alert_coin'] = coin
        coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
        await query.edit_message_text(LANGUAGES[lang]['enter_price'].format(coin=coin_name))

    elif query.data.startswith('chart_') and len(query.data.split('_')) == 2:
        coin = query.data.split('_')[1]
        coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
        chart_url = f"https://www.tradingview.com/chart/?symbol={coin.upper()}USD"
        await query.edit_message_text(
            LANGUAGES[lang]['chart_link'].format(coin=coin_name, url=chart_url)
        )

    elif query.data.startswith('convert_to_irr_') and len(query.data.split('_')) == 2:
        coin = query.data.split('_')[1]
        price, change = get_crypto_price(coin)
        if price:
            price_irr = int(price * USD_TO_IRR)
            coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
            await query.edit_message_text(
                f"{LANGUAGES[lang]['current_price'].format(coin=coin_name, price=price)}\n"
                f"{LANGUAGES[lang]['price_in_irr'].format(coin=coin_name, price_irr=price_irr)}\n"
                f"{LANGUAGES[lang]['change_24h'].format(change=change)}"
            )

    elif query.data == 'toggle_daily':
        storage.users[user_id]['daily_report'] = not storage.users[user_id].get('daily_report', False)
        storage.save_data()
        await start(update, context)

    elif query.data == 'developer':
        await query.edit_message_text(LANGUAGES[lang]['developer_info'])

    elif query.data == 'search':
        await query.edit_message_text(LANGUAGES[lang]['search_prompt'])
        context.user_data['search_mode'] = True

    elif query.data == 'my_data':
        last_name = storage.users[user_id]['last_name']
        daily_status = LANGUAGES[lang]['daily_on'] if storage.users[user_id]['daily_report'] else LANGUAGES[lang]['daily_off']
        alerts = storage.alerts.get(user_id, [])
        alerts_text = "\n".join([f"{CURRENCIES[a['coin']] if lang == 'fa' else a['coin'].capitalize()}: ${a['price']}" for a in alerts]) if alerts else LANGUAGES[lang]['alerts_empty']
        data_text = (
            f"{LANGUAGES[lang]['my_data_title'].format(last_name=last_name)}\n"
            f"{LANGUAGES[lang]['my_data_lang'].format(lang='English' if lang == 'en' else 'فارسی')}\n"
            f"{LANGUAGES[lang]['my_data_report'].format(status=daily_status)}\n"
            f"{LANGUAGES[lang]['my_data_alerts'].format(alerts=alerts_text)}"
        )
        await query.edit_message_text(data_text)

    elif query.data.startswith('lang_'):
        new_lang = query.data.split('_')[1]
        storage.users[user_id]['lang'] = new_lang
        storage.save_data()
        await start(update, context)

# Handle price input for alerts and search
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    lang = storage.users[user_id]['lang']

    if 'alert_coin' in context.user_data:
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
        except ValueError:
            await update.message.reply_text("Please enter a valid number" if lang == 'en' else "لطفاً یک عدد معتبر وارد کنید")

    elif context.user_data.get('search_mode', False):
        search_term = update.message.text.lower()
        found = None
        for coin_id, coin_name in CURRENCIES.items():
            if search_term in coin_id.lower() or search_term in coin_name.lower():
                found = coin_id
                break
        if found:
            coin_name = CURRENCIES[found] if lang == 'fa' else found.capitalize()
            await update.message.reply_text(
                LANGUAGES[lang]['search_result'].format(coin=coin_name),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(LANGUAGES[lang]['price'], callback_data=f"price_{found}"),
                     InlineKeyboardButton(LANGUAGES[lang]['set_alert'], callback_data=f"alert_{found}")],
                    [InlineKeyboardButton(LANGUAGES[lang]['chart'], callback_data=f"chart_{found}"),
                     InlineKeyboardButton(LANGUAGES[lang]['convert_to_irr'], callback_data=f"convert_to_irr_{found}")]
                ])
            )
        else:
            await update.message.reply_text(LANGUAGES[lang]['search_no_result'])
        del context.user_data['search_mode']

def main():
    application = Application.builder().token('8003905325:AAGaLlv41FUe9RgHjFmeNDLrxSQAcWO7KXE').build()
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_alerts, 'interval', seconds=CHECK_INTERVAL, args=[application])
    scheduler.add_job(daily_report, 'cron', hour=8, args=[application])
    scheduler.start()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
