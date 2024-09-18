#!/usr/bin/env python3
from asyncio import sleep
from logging import basicConfig, INFO, getLogger
from json import loads as json_loads
from time import time
from os import getenv, path as ospath
from datetime import datetime

from pytz import utc, timezone
from dotenv import load_dotenv
from requests import get as rget
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.raw import functions

basicConfig(level=INFO, format="[%(levelname)s] %(asctime)s - %(message)s")
log = getLogger(__name__)

# Load environment variables
if CONFIG_ENV_URL := getenv('CONFIG_ENV_URL'):
    try:
        res = rget(CONFIG_ENV_URL)
        if res.status_code == 200:
            log.info("Downloading .env from CONFIG_ENV_URL")
            with open('.env', 'wb+') as f:
                f.write(res.content)
        else:
            log.error(f"Failed to Download .env due to Error Code {res.status_code}")
    except Exception as e:
        log.error(f"CONFIG_ENV_URL: {e}")

if CONFIG_JSON_URL := getenv('CONFIG_JSON_URL'):
    try:
        res = rget(CONFIG_JSON_URL)
        if res.status_code == 200:
            log.info("Downloading config.json from CONFIG_JSON_URL")
            with open('config.json', 'wb+') as f:
                f.write(res.content)
        else:
            log.error(f"Failed to download config.json due to Error Code {res.status_code}")
    except Exception as e:
        log.error(f"CONFIG_JSON_URL: {e}")

load_dotenv('.env', override=True)

API_ID = int(getenv("API_ID", 0))
API_HASH = getenv("API_HASH")
PYRO_SESSION = getenv('PYRO_SESSION')
BOT_TOKEN = getenv('BOT_TOKEN')
if PYRO_SESSION is None:
    log.error('PYRO_SESSION is not set')
    exit(1)
if not ospath.exists('config.json'):
    log.error("config.json not Found!")
    exit(1)
try:
    config = json_loads(open('config.json', 'r').read())
    bots = config['bots']
    channels = config['channels']
except Exception as e:
    log.error(str(e))
    log.error("Error: config.json is not valid")
    exit(1)

HEADER_MSG = getenv("HEADER_MSG", "**@HybridUpdates Bot Status :**")
FOOTER_MSG = getenv("FOOTER_MSG", "⚠️ Bot down? Report to: @Hybrid_Vamp or @Hybrid_Vamp_Bot")
MSG_BUTTONS = getenv("MSG_BUTTONS", "💰 Donate#https://t.me/tribute/app?startapp=donation_466|🚀 Boost#https://t.me/Hybridupdates?boost")
TIME_ZONE = getenv("TIME_ZONE", "Asia/Kolkata")

log.info("Connecting pyroBotClient")
try:
    client = Client("TgBotStatus", api_id=API_ID, api_hash=API_HASH, session_string=PYRO_SESSION, no_updates=True)
except BaseException as e:
    log.warning(e)
    exit(1)

if BOT_TOKEN:
    try:
        bot = Client("TgBotStatus_Bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, no_updates=True)
        await bot.start()  # Ensure the bot client is started properly
    except BaseException as e:
        log.warning(e)
        exit(1)

# Helper functions
def progress_bar(current, total):
    pct = (current / total) * 100
    p = min(max(pct, 0), 100)
    cFull = int(p // 8)
    p_str = '●' * cFull
    p_str += '○' * (12 - cFull)
    return f"[{p_str}] {round(p, 2)}%"

def get_readable_time(seconds):
    mseconds = seconds * 1000
    periods = [('d', 86400000), ('h', 3600000), ('m', 60000), ('s', 1000), ('ms', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if mseconds >= period_seconds:
            period_value, mseconds = divmod(mseconds, period_seconds)
            result += f'{int(period_value)}{period_name}'
    if result == '':
        return '0ms'
    return result

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']

def get_readable_file_size(size_in_bytes):
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return f'{size_in_bytes:.2f}{SIZE_UNITS[index]}' if index > 0 else f'{size_in_bytes}B'

async def bot_info(user_id):
    try:
        return (await client.get_users(user_id)).mention
    except Exception:
        return ''

def make_btns():
    btns = []
    for row in MSG_BUTTONS.split('||'):
        row_btns = []
        for sbtn in row.split('|'):
            btext, link = sbtn.split('#', maxsplit=1)
            row_btns.append(InlineKeyboardButton(btext, url=link))
        btns.append(row_btns)
    return InlineKeyboardMarkup(btns)

async def editMsg(chat_id, message_id, text):
    try:
        post_msg = await client.edit_message_text(int(chat_id), int(message_id), text, 
            disable_web_page_preview=True)
        if BOT_TOKEN and MSG_BUTTONS:
            await bot.edit_message_reply_markup(post_msg.chat.id, post_msg.id, make_btns())
    except FloodWait as f:
        await sleep(f.value * 1.2)
        await editMsg(chat_id, message_id, text)
    except MessageNotModified:
        pass

async def editStatusMsg(status_msg):
    _channels = channels.values()
    if len(_channels) == 0:
        log.warning("No channels found")
        exit(1)
    for channel in _channels:
        log.info(f"Updating Channel ID : {channel['chat_id']} & Message ID : {channel['message_id']}")
        await sleep(1.5)
        try:
            await editMsg(channel['chat_id'], channel['message_id'], status_msg)
        except Exception as e:
            log.error(str(e))
            continue

async def check_bots():
    start_time = time()
    bot_stats = {}
    totalBotsCount = len(bots.keys())
    log.info("Starting Periodic Bot Status checks...")

    header_msg = f"__**{HEADER_MSG}**__\n\n"
    status_message = header_msg + """• **Available Bots :** __Checking...__

• `Currently Ongoing Periodic Check`

"""
    await editStatusMsg(status_message + f"""**• Status Update Stats:**
┌ **Bots Verified :** 0 out of {totalBotsCount}
├ **Progress :** [○○○○○○○○○○] 0%
└ **Time Elapsed :** 0s""")

    bot_no, avl_bots = 0, 0
    for bot, bdata in bots.items():
        if not bot or not bdata:
            break
        bot_stats.setdefault(bot, {})
        bot_stats[bot]['bot_uname'] = bdata['bot_uname']
        bot_stats[bot]['host'] = bdata['host']
        pre_time = time()
        if bdata.get('base_url_of_bot'):
            resp = rget(f"{bdata['base_url_of_bot']}/status")
            if resp.status_code == 200:
                bot_stats[bot]["status_data"] = resp.json()
        try:
            sent_msg = await client.send_message(bdata['bot_uname'], "/start")
            await sleep(10)
            history_msgs = await client.invoke(
                functions.messages.GetHistory(
                    peer=await client.resolve_peer(bdata['bot_uname']), offset_id=0, offset_date=0, add_offset=0, limit=1, max_id=0, min_id=0, hash=0,
                )
            )
            if sent_msg.id == history_msgs.messages[0].id:
                bot_stats[bot]["status"] = "❌"
                await bot.send_message(chat_id="@Hybrid_Vamp", text=f"⚠️ {bdata['bot_uname']} is down")
            else:
                resp_time = history_msgs.messages[0].date - int(pre_time)
                avl_bots += 1
                bot_stats[bot]["response_time"] = f"`{get_readable_time(resp_time)}`"
                bot_stats[bot]["status"] = "✅"
            await client.read_chat_history(bdata['bot_uname'])
        except Exception as e:
            log.info(str(e))
            bot_stats[bot]["status"] = "❌"
            await bot.send_message(chat_id="@Hybrid_Vamp", text=f"⚠️ {bdata['bot_uname']} is down")

        log.info(f"Checked {bdata['bot_uname']} & Status : {bot_stats[bot]['status']}.")
        bot_no += 1

        await editStatusMsg(status_message + f"""**Status Update Stats:**
┌ **Bots Checked :** {bot_no} out of {totalBotsCount}
├ **Progress :** {progress_bar(bot_no, totalBotsCount)}
└ **Time Elapsed :** {get_readable_time(time() - start_time)}""")

    # Stop the bot after all checks
    await bot.stop()

    end_time = time()
    log.info("Completed periodic checks.")

if __name__ == "__main__":
    client.start()
    client.loop.run_until_complete(check_bots())
    client.stop()
