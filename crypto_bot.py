import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# تنظیمات لاگینگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# تنظیمات ثابت
COINGECKO_API = "https://api.coingecko.com/api/v3"
CHECK_INTERVAL = 60  # چک کردن هر 1 دقیقه
USD_TO_IRR = 930000  # نرخ تبدیل دلار به ریال

# لیست 100 ارز دیجیتال محبوب
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

# دیکشنری زبان‌ها
LANGUAGES = {
    'en': {
        'welcome': "Welcome to Crypto Bot!\nChoose an option:",
        'price': "Prices",
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
        'delete_menu': "Which alert do you want to delete?",
        'alert_deleted': "Alert deleted!",
        'chart_link': "View {coin} chart: {url}",
        'daily_on': "ON",
        'daily_off': "OFF",
        'daily_report_text': "📅 Daily Crypto Report:",
        'daily_report_enabled': "Daily report enabled for you. Every day at 6:00 AM Tehran time, a report will be sent with the top 10 crypto prices.",
        'daily_report_disabled': "Daily report disabled.",
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
            "Developer: Fatemeh Ziaei\n\n"
            "Student ID: 02121112705031\n\n"
            "Supervisor: Dr. Faezeh Mokhtar Abadi\n\n"
            "University: Al-Zahra National Skills University, Kerman, Iran\n\n"
            "Project Goal: Build a crypto tracking bot\n\n\n"
            "** Bachelor's Thesis **"
        ),
        'help': (
            "Crypto Bot Help:\n"
            "- /start: Start the bot and see the main menu\n"
            "- Prices: View current prices of cryptocurrencies\n"
            "- Set Alert: Set a price alert for a coin\n"
            "- View Alerts: See and manage your alerts\n"
            "- Chart: Get a chart link for a coin\n"
            "- Daily Report: Toggle daily price reports\n"
            "- Search Coin: Search for a specific coin\n"
            "- My Data: View your saved data\n"
            "- Change Language: Switch between English and Persian\n"
            "- About Developer: Learn about the developer"
        ),
        'convert_message': "The price of {coin} is equivalent to {price_irr:,} IRR",
        'back_to_menu': "Back to Menu"
    },
    'fa': {
        'welcome': "به ربات کریپتو خوش آمدید، ابزاری پیشرفته برای رصد بازار ارزهای دیجیتال:\n",
        'price': "قیمت ارز",
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
        'delete_menu': "کدام هشدار را می‌خواهید حذف کنید؟",
        'alert_deleted': "هشدار حذف شد!",
        'chart_link': "مشاهده نمودار {coin}: {url}",
        'daily_on': "روشن",
        'daily_off': "خاموش",
        'daily_report_text': "📅 گزارش روزانه کریپتو:",
        'daily_report_enabled': "گزارش روزانه برای شما فعال شد. هر روز ساعت ۶:۰۰ صبح به وقت تهران، گزارشی از قیمت ۱۰ ارز برتر ارسال می‌شود。",
        'daily_report_disabled': "گزارش روزانه خاموش شد。",
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
            "توسعه‌دهنده: فاطمه ضیایی\n\n"
            "شماره دانشجویی: 02121112705031\n\n"
            "استاد راهنما: خانم دکتر فائزه مختارآبادی\n\n"
            "دانشگاه: دانشگاه ملی مهارت الزهرا، کرمان\n\n"
            "هدف پروژه: ساخت ربات ردیابی کریپتو\n\n\n"
            "** پروژه کارشناسی **"
        ),
        'help': (
            "راهنمایی ربات کریپتو:\n"
            "- /start: شروع ربات و نمایش منوی اصلی\n"
            "- قیمت ارز: مشاهده قیمت فعلی ارزهای دیجیتال\n"
            "- تنظیم هشدار: تنظیم هشدار قیمت برای یک ارز\n"
            "- مشاهده هشدارها: دیدن و مدیریت هشدارهای شما\n"
            "- نمودار: دریافت لینک نمودار یک ارز\n"
            "- گزارش روزانه: روشن/خاموش کردن گزارش روزانه قیمت‌ها\n"
            "- جستجوی ارز: جستجو برای یک ارز خاص\n"
            "- داده‌های من: مشاهده داده‌های ذخیره‌شده شما\n"
            "- تغییر زبان: تغییر بین فارسی و انگلیسی\n"
            "- معرفی توسعه‌دهنده: اطلاعات درباره توسعه‌دهنده"
        ),
        'convert_message': "قیمت {coin} معادل {price_irr:,} ریال است",
        'back_to_menu': "بازگشت به منو"
    }
}

# کلاس ذخیره‌سازی با دیتابیس PostgreSQL
class Storage:
    def __init__(self):
        self.conn = psycopg2.connect(os.getenv('DATABASE_URL'), cursor_factory=RealDictCursor)
        self.create_tables()
        self.load_data()

    def create_tables(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    lang TEXT DEFAULT 'en',
                    daily_report BOOLEAN DEFAULT FALSE,
                    first_name TEXT,
                    last_name TEXT
                );
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT,
                    coin TEXT,
                    price REAL,
                    original_price REAL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
            """)
            self.conn.commit()

    def load_data(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM users")
            self.users = {row['user_id']: dict(row) for row in cur.fetchall()}
            cur.execute("SELECT * FROM alerts")
            self.alerts = {}
            for row in cur.fetchall():
                user_id = row['user_id']
                if user_id not in self.alerts:
                    self.alerts[user_id] = []
                self.alerts[user_id].append({
                    'coin': row['coin'],
                    'price': row['price'],
                    'original_price': row['original_price']
                })

    def save_data(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

storage = Storage()

# تابع دریافت قیمت ارز از CoinGecko
def get_crypto_price(coin_id):
    try:
        url = f"{COINGECKO_API}/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        price = data[coin_id]['usd']
        change_24h = data[coin_id]['usd_24h_change']
        logger.info(f"دریافت قیمت برای {coin_id}: ${price}")
        return price, change_24h
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت برای {coin_id}: {e}")
        return None, None

# تابع چک کردن هشدارها
async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    try:
        ids = ','.join(CURRENCIES.keys())
        url = f"{COINGECKO_API}/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        current_prices = {coin: data[coin]['usd'] for coin in CURRENCIES if coin in data}
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت‌ها در چک کردن هشدارها: {e}")
        return

    with storage.conn.cursor() as cur:
        cur.execute("SELECT * FROM alerts")
        alerts = cur.fetchall()
        for alert in alerts:
            user_id = alert['user_id']
            coin = alert['coin']
            target_price = alert['price']
            original_price = alert['original_price']
            current_price = current_prices.get(coin)
            lang = storage.users.get(user_id, {}).get('lang', 'en')
            if current_price and (
                (target_price > original_price and current_price >= target_price) or
                (target_price < original_price and current_price <= target_price)
            ):
                await context.bot.send_message(
                    chat_id=user_id,
                    text=LANGUAGES[lang]['alert_triggered'].format(
                        coin=CURRENCIES[coin] if lang == 'fa' else coin.capitalize(),
                        price=target_price,
                        current=current_price
                    )
                )
                cur.execute("DELETE FROM alerts WHERE id = %s", (alert['id'],))
        storage.save_data()
    storage.load_data()

# تابع ارسال گزارش روزانه
async def daily_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        ids = ','.join(CURRENCIES.keys())
        url = f"{COINGECKO_API}/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url)
        data = response.json()
        prices = {coin: data[coin]['usd'] for coin in CURRENCIES if coin in data}
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت‌ها برای گزارش روزانه: {e}")
        return

    for user_id, user_data in storage.users.items():
        if user_data.get('daily_report', False):
            lang = user_data.get('lang', 'en')
            report = [LANGUAGES[lang]['daily_report_text']]
            for coin, price in list(prices.items())[:10]:
                coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
                report.append(f"{coin_name}: ${price}")
            await context.bot.send_message(chat_id=user_id, text="\n".join(report))

# تابع شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    first_name = update.effective_user.first_name or "Unknown"
    last_name = update.effective_user.last_name or "Unknown"
    
    with storage.conn.cursor() as cur:
        cur.execute("""
            INSERT INTO users (user_id, lang, daily_report, first_name, last_name)
            VALUES (%s, % надійністьs, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET first_name = %s, last_name = %s
        """, (user_id, 'en', False, first_name, last_name, first_name, last_name))
        storage.save_data()
    
    storage.load_data()
    lang = storage.users[user_id]['lang']
    daily_status = LANGUAGES[lang]['daily_on'] if storage.users[user_id]['daily_report'] else LANGUAGES[lang]['daily_off']
    
    logger.info(f"داده‌های فعلی: {storage.users}")
    logger.info(f"هشدارهای فعلی: {storage.alerts}")
    
    keyboard = [
        [InlineKeyboardButton(LANGUAGES[lang]['price'], callback_data='price_0'),
         InlineKeyboardButton(LANGUAGES[lang]['set_alert'], callback_data='alert_0')],
        [InlineKeyboardButton(LANGUAGES[lang]['alerts_list'], callback_data='alerts_list'),
         InlineKeyboardButton(LANGUAGES[lang]['chart'], callback_data='chart_0')],
        [InlineKeyboardButton(LANGUAGES[lang]['daily_report'].format(status=daily_status), callback_data='toggle_daily'),
         InlineKeyboardButton(LANGUAGES[lang]['search'], callback_data='search')],
        [InlineKeyboardButton(LANGUAGES[lang]['my_data'], callback_data='my_data'),
         InlineKeyboardButton(LANGUAGES[lang]['language'], callback_data='language')],
        [InlineKeyboardButton(LANGUAGES[lang]['developer'], callback_data='developer')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(LANGUAGES[lang]['welcome'], reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(LANGUAGES[lang]['welcome'], reply_markup=reply_markup)

# تابع راهنما
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    lang = storage.users.get(user_id, {}).get('lang', 'en')
    await update.message.reply_text(LANGUAGES[lang]['help'])

# تابع مدیریت دکمه‌ها
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    lang = storage.users[user_id]['lang']
    coins = list(CURRENCIES.keys())
    items_per_page = 10
    total_pages = (len(coins) + items_per_page - 1) // items_per_page

    data_parts = query.data.split('_')
    action = data_parts[0]

    if action in ('price', 'alert', 'chart') and len(data_parts) == 2:
        try:
            page = int(data_parts[1])  # حالت صفحه‌بندی
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
            keyboard.append([InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')])
            await query.edit_message_text(
                LANGUAGES[lang]['select_coin'].format(page=page+1, total_pages=total_pages),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except ValueError:  # حالت انتخاب ارز
            coin = data_parts[1]
            if action == 'price':
                price, change = get_crypto_price(coin)
                if price is not None:
                    coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
                    change_str = f"{change:+.2f}"
                    await query.edit_message_text(
                        f"{LANGUAGES[lang]['current_price'].format(coin=coin_name, price=price)}\n"
                        f"{LANGUAGES[lang]['change_24h'].format(change=change_str)}",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton(LANGUAGES[lang]['convert_to_irr'], callback_data=f"convert_to_irr_{coin}_{price}")],
                            [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
                        ])
                    )
                else:
                    await query.edit_message_text("Could not fetch price." if lang == 'en' else "نمی‌توان قیمت را دریافت کرد.")
            elif action == 'alert':
                context.user_data['alert_coin'] = coin
                coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
                await query.edit_message_text(
                    LANGUAGES[lang]['enter_price'].format(coin=coin_name),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
                    ])
                )
            elif action == 'chart':
                coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
                # اصلاح لینک نمودار برای سازگاری با TradingView
                symbol = coin.upper() if coin == 'bitcoin' else f"BINANCE:{coin.upper()}USDT"  # استفاده از جفت USDT برای اکثر ارزها
                chart_url = f"https://www.tradingview.com/chart/?symbol={symbol}"
                await query.edit_message_text(
                    LANGUAGES[lang]['chart_link'].format(coin=coin_name, url=chart_url),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
                    ])
                )

    elif action == 'convert_to_irr':
        coin = data_parts[1]
        price = float(data_parts[2])
        price_irr = price * USD_TO_IRR
        coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
        price_irr_str = "{:,.0f}".format(price_irr)
        await query.message.reply_text(
            LANGUAGES[lang]['convert_message'].format(coin=coin_name, price_irr=price_irr_str),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
            ])
        )

    elif query.data == 'alerts_list':
        alerts = storage.alerts.get(user_id, [])
        if not alerts:
            await query.edit_message_text(
                LANGUAGES[lang]['alerts_empty'],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
                ])
            )
        else:
            alert_list = [LANGUAGES[lang]['alerts_title']]
            for alert in alerts:
                coin_name = CURRENCIES[alert['coin']] if lang == 'fa' else alert['coin'].capitalize()
                alert_list.append(f"{coin_name}: ${alert['price']}")
            alert_list.append("")  # خط خالی قبل از دکمه
            keyboard = [
                [InlineKeyboardButton(LANGUAGES[lang]['delete_alert'], callback_data='delete_menu')],
                [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
            ]
            await query.edit_message_text("\n".join(alert_list), reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'delete_menu':
        alerts = storage.alerts.get(user_id, [])
        if not alerts:
            await query.edit_message_text(
                LANGUAGES[lang]['alerts_empty'],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
                ])
            )
        else:
            keyboard = []
            for i, alert in enumerate(alerts):
                coin_name = CURRENCIES[alert['coin']] if lang == 'fa' else alert['coin'].capitalize()
                keyboard.append([InlineKeyboardButton(
                    f"{coin_name}: ${alert['price']}",
                    callback_data=f"delete_alert_{i}"
                )])
            keyboard.append([InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')])
            await query.edit_message_text(
                LANGUAGES[lang]['delete_menu'],
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data.startswith('delete_alert_'):
        alert_index = int(query.data.split('_')[2])
        alerts = storage.alerts.get(user_id, [])
        if 0 <= alert_index < len(alerts):
            with storage.conn.cursor() as cur:
                cur.execute("SELECT id FROM alerts WHERE user_id = %s ORDER BY id", (user_id,))
                alert_ids = [row['id'] for row in cur.fetchall()]
                if alert_index < len(alert_ids):
                    cur.execute("DELETE FROM alerts WHERE id = %s", (alert_ids[alert_index],))
                    storage.save_data()
                    storage.load_data()
            await query.edit_message_text(
                LANGUAGES[lang]['alert_deleted'],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
                ])
            )
        else:
            await button(update, context)  # برگشت به لیست هشدارها

    elif query.data == 'language':
        keyboard = [
            [InlineKeyboardButton("English", callback_data='lang_en'),
             InlineKeyboardButton("فارسی", callback_data='lang_fa')],
            [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
        ]
        await query.edit_message_text(
            "Select language / زبان را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == 'toggle_daily':
        with storage.conn.cursor() as cur:
            cur.execute("UPDATE users SET daily_report = NOT daily_report WHERE user_id = %s RETURNING daily_report", (user_id,))
            new_status = cur.fetchone()['daily_report']
            storage.save_data()
        storage.load_data()
        message = LANGUAGES[lang]['daily_report_enabled'] if new_status else LANGUAGES[lang]['daily_report_disabled']
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
            ])
        )

    elif query.data == 'developer':
        await query.edit_message_text(
            LANGUAGES[lang]['developer_info'],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
            ])
        )

    elif query.data == 'search':
        await query.edit_message_text(
            LANGUAGES[lang]['search_prompt'],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
            ])
        )
        context.user_data['search_mode'] = True

    elif query.data == 'my_data':
        first_name = storage.users[user_id]['first_name']
        last_name = storage.users[user_id]['last_name']
        daily_status = LANGUAGES[lang]['daily_on'] if storage.users[user_id]['daily_report'] else LANGUAGES[lang]['daily_off']
        alerts = storage.alerts.get(user_id, [])
        alerts_text = "\n".join([f"{CURRENCIES[a['coin']] if lang == 'fa' else a['coin'].capitalize()}: ${a['price']}" for a in alerts]) if alerts else LANGUAGES[lang]['alerts_empty']
        data_text = (
            f"{LANGUAGES[lang]['my_data_title'].format(last_name=f'{first_name} {last_name}')}\n"
            f"{LANGUAGES[lang]['my_data_lang'].format(lang='English' if lang == 'en' else 'فارسی')}\n"
            f"{LANGUAGES[lang]['my_data_report'].format(status=daily_status)}\n"
            f"{LANGUAGES[lang]['my_data_alerts'].format(alerts=alerts_text)}"
        )
        await query.edit_message_text(
            data_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
            ])
        )

    elif query.data.startswith('lang_'):
        new_lang = query.data.split('_')[1]
        with storage.conn.cursor() as cur:
            cur.execute("UPDATE users SET lang = %s WHERE user_id = %s", (new_lang, user_id))
            storage.save_data()
        storage.load_data()
        await start(update, context)  # نمایش منو با زبان جدید

    elif query.data == 'back_to_menu':
        await start(update, context)

# تابع مدیریت پیام‌های ورودی
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
            
            with storage.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO alerts (user_id, coin, price, original_price)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, coin, target_price, current_price))
                storage.save_data()
            
            coin_name = CURRENCIES[coin] if lang == 'fa' else coin.capitalize()
            await update.message.reply_text(
                LANGUAGES[lang]['alert_set'].format(coin=coin_name, price=target_price),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
                ])
            )
            del context.user_data['alert_coin']
            storage.load_data()
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid number" if lang == 'en' else "لطفاً یک عدد معتبر وارد کنید",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
                ])
            )

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
                    [InlineKeyboardButton(LANGUAGES[lang]['chart'], callback_data=f"chart_{found}")],
                    [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
                ])
            )
        else:
            await update.message.reply_text(
                LANGUAGES[lang]['search_no_result'],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(LANGUAGES[lang]['back_to_menu'], callback_data='back_to_menu')]
                ])
            )
        del context.user_data['search_mode']

# تابع اصلی برنامه
def main():
    application = Application.builder().token('8003905325:AAGaLlv41FUe9RgHjFmeNDLrxSQAcWO7KXE').build()
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_alerts, 'interval', seconds=CHECK_INTERVAL, args=[application])
    scheduler.add_job(daily_report, 'cron', hour=2, minute=30, args=[application])  # 6:00 AM Tehran = 2:30 AM UTC
    scheduler.start()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    try:
        application.run_polling()
    finally:
        storage.close()

if __name__ == '__main__':
    main()
