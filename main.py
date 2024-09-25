from asyncio import sleep
from logging import basicConfig, INFO, getLogger
from json import loads as json_loads
from time import time
from os import getenv, path as ospath 
from datetime import datetime
from pytz import timezone
from dotenv import load_dotenv
from requests import get as rget
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.raw import functions

basicConfig(level=INFO, format="[%(levelname)s] %(asctime)s - %(message)s")
log = getLogger(__name__)

# Loading environment variables
load_dotenv('.env', override=True)

API_ID = int(getenv("API_ID", 0))
API_HASH = getenv("API_HASH")
USER_SESSION = getenv('USER_SESSION')
BOT_TOKEN = getenv('BOT_TOKEN')
if USER_SESSION is None:
    log.error('USER_SESSION is not set')
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

log.info("Connecting to User Client for Bot Checks")
try:
    user_client = Client("UserClient", api_id=API_ID, api_hash=API_HASH, session_string=USER_SESSION, no_updates=True)
except BaseException as e:
    log.warning(e)
    exit(1)

log.info("Connecting to Bot Client for Status Updates")
if BOT_TOKEN:
    try:
        bot_client = Client("BotClient", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, no_updates=True)
    except BaseException as e:
        log.warning(e)
        exit(1)

async def get_bot_status(bot_username):
    """User client sends message to a bot and checks its response"""
    try:
        sent_msg = await user_client.send_message(bot_username, "/start")
        await sleep(10)
        history_msgs = await user_client.invoke(
            functions.messages.GetHistory(
                peer=await user_client.resolve_peer(bot_username),
                offset_id=0, offset_date=0, add_offset=0, limit=1, max_id=0, min_id=0, hash=0,
            )
        )
        if sent_msg.id == history_msgs.messages[0].id:
            return "❌"
        else:
            response_time = time() - sent_msg.date.timestamp()
            return f"✅ - Ping: {round(response_time, 2)}s"
    except Exception as e:
        log.error(str(e))
        return "❌"

async def edit_status_message(status_msg):
    """Bot client edits the status message in channels"""
    for channel in channels.values():
        try:
            log.info(f"Updating Channel ID: {channel['chat_id']} & Message ID: {channel['message_id']}")
            await sleep(1.5)
            await bot_client.edit_message_text(channel['chat_id'], channel['message_id'], status_msg, disable_web_page_preview=True)
        except FloodWait as f:
            await sleep(f.value * 1.2)
            await edit_status_message(status_msg)
        except MessageNotModified:
            pass

async def check_bots():
    """User client checks the status of all bots, bot client updates the messages"""
    bot_statuses = {}
    start_time = time()
    
    for bot, bdata in bots.items():
        log.info(f"Checking {bdata['bot_uname']}...")
        bot_statuses[bot] = await get_bot_status(bdata['bot_uname'])
        log.info(f"{bdata['bot_uname']} - {bot_statuses[bot]}")
    
    status_msg = f"__**{HEADER_MSG}**__\n\n"
    for bot, status in bot_statuses.items():
        status_msg += f"**{bots[bot]['bot_uname']}** - {status}\n"
    
    end_time = time()
    current_time = datetime.now(timezone(TIME_ZONE)).strftime('%d/%m/%Y %H:%M:%S')
    status_msg += f"\n__Last Checked: {current_time}__\n__Check Time: {round(end_time - start_time, 2)}s__\n\n{FOOTER_MSG}"
    
    await edit_status_message(status_msg)

async def main():
    await user_client.start()
    await bot_client.start()
    log.info("Clients started, beginning bot checks...")
    
    while True:
        await check_bots()
        await sleep(3600)  # Check every hour

if __name__ == "__main__":
    bot_client.run(main())
