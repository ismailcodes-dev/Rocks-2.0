import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import database
import logging
from logging.handlers import RotatingFileHandler

# --- SETUP LOGGING ---
# This creates a log file that rotates (overwrites old logs) so it doesn't eat your hard drive.
logger = logging.getLogger('bot')
logger.setLevel(logging.INFO)

# File Handler (Saves to bot.log)
handler = RotatingFileHandler('bot.log', maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Console Handler (Prints to terminal)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s: %(message)s'))
logger.addHandler(console)

# --- CONFIGURATION ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- BOT INITIALIZATION ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.voice_states = True 
        
        super().__init__(command_prefix="/", intents=intents, help_command=None) # We disable default help
        self.db = database.DatabaseManager(self)

    async def on_ready(self):
        """Event that runs when the bot is online."""
        await self.db.init_db()
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Discord.py Version: {discord.__version__}')
        
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

bot = MyBot()

# --- MAIN FUNCTION ---
async def main():
    """The main function to run the bot."""
    cog_folder = "cogs"
    
    async with bot:
        for filename in os.listdir(cog_folder):
            if filename.endswith(".py") and filename != "__init__.py":
                try:
                    await bot.load_extension(f"{cog_folder}.{filename[:-3]}")
                    logger.info(f"Loaded cog: {filename}")
                except Exception as e:
                    logger.error(f"Failed to load cog {filename}: {e}", exc_info=True)
        
        await bot.start(BOT_TOKEN)

# --- RUN THE BOT ---
if __name__ == "__main__":
    if BOT_TOKEN is None:
        logger.critical("Error: BOT_TOKEN environment variable not found.")
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            pass