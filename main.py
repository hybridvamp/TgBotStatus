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

basicConfig(level=INFO, format="[%(levelname)s] %(asctime)s - %(message)s")
log = getLogger(__name__)

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
FOOTER_MSG = getenv("FOOTER_MSG", "⚠️ Bot down ? Report to: @Hybrid_Vamp or @Hybrid_Vamp_Bot")
MSG_BUTTONS = getenv("MSG_BUTTONS", "💰 Donate#https://t.me/tribute/app?startapp=donation_466|🚀 Boost#https://t.me/Hybridupdates?boost")
TIME_ZONE = getenv("TIME_ZONE", "Asia/Kolkata")

log.info("Connecting User and Bot Clients")
user_client = Client("UserClient", api_id=API_ID, api_hash=API_HASH, session_string=PYRO_SESSION, no_updates=True)
bot_client = Client("BotClient", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, no_updates=True)

async def bot_info(user_id):
    try:
        return (await user_client.get_users(user_id)).mention
    except Exception:
        return ''
        
async def editMsg(chat_id, message_id, text):
    try:
        post_msg = await bot_client.edit_message_text(int(chat_id), int(message_id), text, 
            disable_web_page_preview=True)
        if MSG_BUTTONS:
            await bot_client.edit_message_reply_markup(post_msg.chat.id, post_msg.id, make_btns())
    except FloodWait as f:
        await sleep(f.value * 1.2)
        await editMsg(chat_id, message_id, text)
    except MessageNotModified:
        pass

async def check_bots():
    start_time = time()
    bot_stats = {}
    totalBotsCount = len(bots.keys())
    log.info("Starting Periodic Bot Status checks...")
    
    header_msg = f"__**{HEADER_MSG}**__\n\n"
    status_message = header_msg + """• **Available Bots :** __Checking...__

• `Currently Ongoing Periodic Check`

"""
    await editStatusMsg(status_message)

    bot_no, avl_bots = 0, 0
    for bot, bdata in bots.items():
        if not bot or not bdata:
            break
        bot_stats.setdefault(bot, {})
        bot_stats[bot]['bot_uname'] = bdata['bot_uname']
        bot_stats[bot]['host'] = bdata['host']
        pre_time = time()
        
        # Send a message to the bot
        try:
            sent_msg = await user_client.send_message(bdata['bot_uname'], "/start")
            await sleep(10)  # Wait for a response
            # Get the last message sent by the bot
            history_msgs = await user_client.get_chat_history(bdata['bot_uname'], limit=1)
            if sent_msg.id == history_msgs[0].id:
                bot_stats[bot]["status"] = "❌"
                await user_client.send_message(chat_id="@Hybrid_Vamp", text=f"⚠️ {bdata['bot_uname']} is down")
            else:
                resp_time = history_msgs[0].date - int(pre_time)
                avl_bots += 1
                bot_stats[bot]["response_time"] = f"`{get_readable_time(resp_time)}`"
                bot_stats[bot]["status"] = "✅"
        except Exception as e:
            log.info(str(e))
            bot_stats[bot]["status"] = "❌"
            await user_client.send_message(chat_id="@Hybrid_Vamp", text=f"⚠️ {bdata['bot_uname']} is down")
        
        log.info(f"Checked {bdata['bot_uname']} & Status : {bot_stats[bot]['status']}.")
        bot_no += 1
        
        # Update the status message after each check
        status_message = f"**Bot :** {await bot_info(bot_stats[bot]['bot_uname'])}\n"
        if (stdata := bot_stats[bot].get('status_data')):
            try:
                status_message += f'├ **Commit Date :** {stdata["commit_date"]}\n'
            except:
                pass
            try:
                status_message += f'├ **Bot Uptime :** {get_readable_time(stdata["on_time"])}\n'
            except:
                pass
            try:
                status_message += f'├ **Alive :** {get_readable_time(stdata["uptime"])}\n'
            except:
                pass
        
        if bot_stats[bot].get("response_time"):
            status_message += f"├ **Ping :** {bot_stats[bot]['response_time']}\n"
        status_message += f"├ **Status :** {bot_stats[bot]['status']}\n└ **Host :** {bot_stats[bot]['host']}\n\n"
        await editStatusMsg(status_message)

    end_time = time()
    log.info("Completed periodic checks.")

    status_message += f"__Last Checked on {datetime.now(timezone(TIME_ZONE)).strftime('%d/%m/%Y %H:%M:%S')}__"
    status_message += f"\n__Check Time: {get_readable_time(end_time - start_time)}__\n\n{FOOTER_MSG}"

    await editStatusMsg(status_message)
    log.info("Message Update Complete.")

async def main():
    async with user_client, bot_client:
        log.info("Connected to User and Bot API.")
        while True:
            await check_bots()
            await sleep(3600)  # periodic bot status checks every hour

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
