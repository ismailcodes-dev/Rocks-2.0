import discord
from discord.ext import commands
from discord import app_commands, ui

class HelpSelect(ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            discord.SelectOption(label="💰 Economy", description="Money, Levels, and Daily Rewards", emoji="💰", value="economy"),
            discord.SelectOption(label="🎮 Games", description="Casino, Trivia, and Crash", emoji="🎲", value="games"),
            discord.SelectOption(label="🛒 Shop", description="Buying and Selling items", emoji="🛒", value="shop"),
            discord.SelectOption(label="🎙️ Voice", description="Voice Greetings and Welcome Notes", emoji="🎙️", value="voice"),
            discord.SelectOption(label="⚙️ Admin", description="Configuration and Moderation", emoji="🛡️", value="admin"),
        ]
        super().__init__(placeholder="Select a category to view commands...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        embed = discord.Embed(color=discord.Color.blue())
        
        if category == "economy":
            embed.title = "💰 Economy Commands"
            embed.description = (
                "`/balance` - Check your wallet\n"
                "`/daily` - Claim daily rewards\n"
                "`/streak` - Check your daily streak luck\n"
                "`/pay [user] [amount]` - Send coins to a friend\n"
                "`/leaderboard` - See the top players\n"
                "`/lvl` - Check your level and XP\n"
                "`/profile [user]` - View full profile stats"
            )
        elif category == "games":
            embed.title = "🎮 Game Commands"
            embed.description = (
                "`/crash [bet] [cashout]` - High risk, high reward multiplier game\n"
                "`/trivia` - Answer questions to win cash\n"
                "`/blackjack [bet]` - Classic card game\n"
                "`/slots [bet]` - Spin to win\n"
                "`/roulette [bet] [space]` - Bet on Red, Black, or Numbers\n"
                "`/coinflip [bet] [side]` - Heads or Tails"
            )
        elif category == "shop":
            embed.title = "🛒 Shop & Creator Commands"
            embed.description = (
                "`/shop` - Open the visual marketplace\n"
                "`/search [query]` - Find specific items\n"
                "`/upd` - [Creators] Upload a new item\n"
                "`/bumpitem` - [Supreme] Promote your item to the top"
            )
        elif category == "voice":
            embed.title = "🎙️ Voice Features"
            embed.description = (
                "**Passive Features:**\n"
                "• Join a VC to hear a custom greeting (if set)\n"
                "• New members get a voice note in DMs (if set)\n\n"
                "**Commands:**\n"
                "`/setwelcomevoice` - [Admin] Set the DM join audio\n"
                "`/setvcgreet` - [Admin] Set the VC join audio"
            )
        elif category == "admin":
            embed.title = "🛡️ Admin Configuration"
            embed.description = (
                "`/config setup` - Set up bot channels (Shop, Logs, etc.)\n"
                "`/config view` - See current settings\n"
                "`/config addcreatorrole` - Allow roles to upload items\n"
                "`/adminrole add` - Give admin powers to a role\n"
                "`/synccreators` - Fix roles for level 25+ users\n"
                "`/syncranks` - Fix roles for Elite/Master/Supreme"
            )

        embed.set_footer(text="Select another category to switch views.")
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.add_item(HelpSelect(bot))

class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="View the list of available commands.")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 Bot Help Menu",
            description="Welcome! Please select a category below to see available commands.",
            color=discord.Color.brand_green()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        view = HelpView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))