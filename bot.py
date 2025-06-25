import os
import datetime
import logging
import discord
from discord.ext import commands
import requests
from chat_memory import ChatMemory

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("nova-discord.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Enable necessary intents
intents = discord.Intents.default()
intents.message_content = True

TOKEN = os.getenv("DISCORD_TOKEN")
bot = commands.Bot(command_prefix="/", intents=intents)
chat_memory = ChatMemory(max_messages=10)

logger.debug(f"TOKEN repr is {repr(TOKEN)}")

@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user}")

@bot.command()
async def ping(ctx):
    logger.debug("/ping command received")
    await ctx.send("Pong!")

@bot.command()
async def forget(ctx):
    """Tell Nova to forget the current conversation."""
    logger.debug("/forget command received")
    try:
        response = requests.post(
            "http://devshell:5001/clear_memory",
            json={"user_id": "default"},
            timeout=10
        )
        if response.status_code == 200:
            await ctx.send("🧠 Nova's memory has been cleared.")
            logger.info("Cleared Nova's memory successfully.")
        else:
            await ctx.send("❌ Could not clear Nova’s memory.")
            logger.warning(f"Failed to clear memory, status: {response.status_code}")
    except Exception as e:
        logger.error(f"Exception during /forget: {e}", exc_info=True)
        await ctx.send(f"⚠️ Error: {str(e)}")

@bot.event
async def on_message(message):
    logger.debug(f"Received message from {message.author}: {message.content}")

    if message.author == bot.user:
        return

    if message.content.startswith('/'):
        await bot.process_commands(message)
        return

    if isinstance(message.channel, discord.DMChannel):
        user_id = str(message.author.id)
        user_msg = message.content.strip()

        if not user_msg:
            return

        chat_memory.add_message(user_id, "user", user_msg)
        context = chat_memory.get_context(user_id)
        prompt = "\n".join([
            f"{msg}" if role == "user" else f"Nova: {msg}"
            for role, msg in context
        ])

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"nova-memory/conversations/{timestamp}_{message.author.name}.txt"
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, "w") as f:
            f.write(prompt)

        logger.debug(f"Saved conversation to {filename}")

        try:
            response = requests.post(
                "http://devshell:5001/chat-mistral",
                json={"message": user_msg, "source": "discord"},
                timeout=30
            )
            if response.status_code == 200:
                reply = response.json().get("reply", "Nova had no response.")
                logger.info("Received reply from devshell")
            else:
                reply = f"Nova encountered an error: {response.status_code}"
                logger.warning(f"Non-200 response from devshell: {response.status_code}")
        except Exception as e:
            reply = f"Nova is having a moment: {e}"
            logger.error(f"Exception in devshell call: {e}", exc_info=True)

        chat_memory.add_message(user_id, "assistant", reply)
        await message.channel.send(reply)

bot.run(TOKEN)
