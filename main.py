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

# Loading .env and config.json
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

# Load bot configuration
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

# Static messages and time zone
HEADER_MSG = getenv("HEADER_MSG", "**@HybridUpdates Bot Status :**")
FOOTER_MSG = getenv("FOOTER_MSG", "⚠️ Bot down? Report to: @Hybrid_Vamp or @Hybrid_Vamp_Bot")
MSG_BUTTONS = getenv("MSG_BUTTONS", "💰 Donate#https://t.me/tribute/app?startapp=donation_466|🚀 Boost#https://t.me/Hybridupdates?boost")
TIME_ZONE = getenv("TIME_ZONE", "Asia/Kolkata")

log.info("Connecting to Pyrogram clients")

# Initialize the bot client and user client
try:
    client = Client("UserClient", api_id=API_ID, api_hash=API_HASH, session_string=PYRO_SESSION, no_updates=True)
    bot = Client("BotClient", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, no_updates=True)
except BaseException as e:
    log.warning(e)
    exit(1)

# Utility functions to get readable time and file size
def get_readable_time(seconds):
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    time_str = ""
    for period, period_seconds in periods:
        if seconds >= period_seconds:
            value, seconds = divmod(seconds, period_seconds)
            time_str += f"{int(value)}{period} "
    return time_str.strip() if time_str else "0s"

def get_readable_file_size(size_in_bytes):
    SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB']
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return f"{size_in_bytes:.2f}{SIZE_UNITS[index]}"

# Function to format bot status message
def make_btns():
    btns = []
    for row in MSG_BUTTONS.split('||'):
        row_btns = []
        for sbtn in row.split('|'):
            btext, link = sbtn.split('#', maxsplit=1)
            row_btns.append(InlineKeyboardButton(btext, url=link))
        btns.append(row_btns)
    return InlineKeyboardMarkup(btns)

# Function to edit bot message
async def editMsg(chat_id, message_id, text):
    try:
        post_msg = await bot.edit_message_text(int(chat_id), int(message_id), text, disable_web_page_preview=True)
        if MSG_BUTTONS:
            await bot.edit_message_reply_markup(post_msg.chat.id, post_msg.id, make_btns())
    except FloodWait as f:
        await sleep(f.value)
        await editMsg(chat_id, message_id, text)
    except MessageNotModified:
        pass

# Function to edit all channels with the bot status
async def editStatusMsg(status_msg):
    for channel in channels.values():
        log.info(f"Updating Channel ID: {channel['chat_id']} & Message ID: {channel['message_id']}")
        await sleep(1.5)
        await editMsg(channel['chat_id'], channel['message_id'], status_msg)

# Function to check bots' status
async def check_bots():
    start_time = time()
    totalBotsCount = len(bots)
    log.info("Starting Periodic Bot Status checks...")

    # Initial status update
    await editStatusMsg(f"{HEADER_MSG}\n\n• **Available Bots:** __Checking...__")

    bot_no, avl_bots = 0, 0
    for bot, bdata in bots.items():
        pre_time = time()
        bot_no += 1
        try:
            sent_msg = await client.send_message(bdata['bot_uname'], "/start")
            await sleep(10)
            history_msgs = await client.invoke(functions.messages.GetHistory(
                peer=await client.resolve_peer(bdata['bot_uname']),
                offset_id=0,
                offset_date=0,
                add_offset=0,
                limit=1,
                max_id=0,
                min_id=0,
                hash=0
            ))

            if sent_msg.id != history_msgs.messages[0].id:
                resp_time = history_msgs.messages[0].date - pre_time
                avl_bots += 1
                status = f"✅ `{get_readable_time(resp_time)}`"
            else:
                status = "❌"
            await editStatusMsg(f"{HEADER_MSG}\n\n• **Bot:** {bdata['bot_uname']}\n• **Status:** {status}")
        except Exception as e:
            log.error(f"Error checking {bdata['bot_uname']}: {str(e)}")
            await editStatusMsg(f"{HEADER_MSG}\n\n• **Bot:** {bdata['bot_uname']}\n• **Status:** ❌")

    total_time = time() - start_time
    current_time = datetime.now(utc).astimezone(timezone(TIME_ZONE))
    await editStatusMsg(
        f"{HEADER_MSG}\n\n• **Available Bots:** {avl_bots}/{totalBotsCount}\n"
        f"• **Last Checked:** {current_time.strftime('%H:%M:%S %d %B %Y')} ({TIME_ZONE})\n"
        f"• **Time Elapsed:** {get_readable_time(total_time)}\n\n{FOOTER_MSG}"
    )

# Main function to start the client and run checks
async def main():
    await client.start()
    await bot.start()
    await check_bots()

    # Ensure both clients stop gracefully
    await client.stop()
    await bot.stop()

client.run(main())
