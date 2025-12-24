import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio

# Directory to save uploaded voice files
VOICE_FILES_DIR = "cogs/voice_files"

class VoiceManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not os.path.exists(VOICE_FILES_DIR):
            os.makedirs(VOICE_FILES_DIR)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} cog has been loaded.')

    # --- FEATURE 1: Welcome Voice Note (DM) ---
    @app_commands.command(name="setwelcomevoice", description="[Admin] Set an audio file to DM to new members.")
    @app_commands.describe(file="Upload an MP3/WAV file.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_welcome_voice(self, interaction: discord.Interaction, file: discord.Attachment):
        if not file.filename.endswith(('.mp3', '.wav', '.ogg')):
            return await interaction.response.send_message("❌ Please upload an audio file (mp3, wav, ogg).", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        
        # Save file as welcome_{guild_id}.extension
        extension = file.filename.split('.')[-1]
        save_path = f"{VOICE_FILES_DIR}/welcome_{interaction.guild.id}.{extension}"
        await file.save(save_path)

        # Save the path to the database (using our new guild_settings table)
        await self.bot.db.set_guild_setting(interaction.guild.id, "WELCOME_VOICE_PATH", save_path)
        
        await interaction.followup.send(f"✅ **Voice Welcome Set!** New members will receive this audio file in their DMs.")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot: return
        
        # Check if this guild has a welcome voice file set
        file_path = await self.bot.db.get_guild_setting(member.guild.id, "WELCOME_VOICE_PATH")
        
        if file_path and os.path.exists(file_path):
            try:
                audio_file = discord.File(file_path)
                await member.send("👋 **Welcome to the server!** Here is a message for you:", file=audio_file)
            except discord.Forbidden:
                print(f"Could not DM welcome voice to {member.name}")

    # --- FEATURE 2: Voice Channel Greeter ---
    @app_commands.command(name="setvcgreet", description="[Admin] Set a sound to play when someone joins a specific voice channel.")
    @app_commands.describe(channel="The voice channel to attach the sound to.", file="Upload an MP3/WAV file.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_vc_greet(self, interaction: discord.Interaction, channel: discord.VoiceChannel, file: discord.Attachment):
        if not file.filename.endswith(('.mp3', '.wav', '.ogg')):
            return await interaction.response.send_message("❌ Please upload an audio file (mp3, wav, ogg).", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        
        # Save file as greet_{channel_id}.extension
        extension = file.filename.split('.')[-1]
        save_path = f"{VOICE_FILES_DIR}/greet_{channel.id}.{extension}"
        await file.save(save_path)
        
        # Save the mapping (channel_id -> file_path) in settings
        # We use a specific key format: "VC_GREET_{channel_id}"
        await self.bot.db.set_guild_setting(interaction.guild.id, f"VC_GREET_{channel.id}", save_path)
        
        await interaction.followup.send(f"✅ **Channel Greeting Set!** The bot will play this sound when users join {channel.mention}.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot: return
        
        # Check if user actually joined a channel (and didn't just mute/deafen)
        if after.channel and (not before.channel or before.channel.id != after.channel.id):
            
            # Check if this channel has a greet sound
            file_path = await self.bot.db.get_guild_setting(member.guild.id, f"VC_GREET_{after.channel.id}")
            
            if file_path and os.path.exists(file_path):
                # Check if bot is already in a voice channel in this guild
                if member.guild.voice_client is not None:
                    return # Bot is busy playing something else

                try:
                    # Connect, Play, Disconnect
                    vc = await after.channel.connect()
                    
                    # Define a callback to disconnect after playing
                    def after_playing(error):
                        coro = vc.disconnect()
                        fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                        try: fut.result()
                        except: pass

                    vc.play(discord.FFmpegPCMAudio(file_path), after=after_playing)
                    
                except Exception as e:
                    print(f"Failed to play VC greet: {e}")
                    # Ensure cleanup if stuck
                    if member.guild.voice_client:
                        await member.guild.voice_client.disconnect()

async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceManager(bot))