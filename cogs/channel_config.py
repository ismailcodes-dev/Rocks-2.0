import discord
from discord.ext import commands
from discord import app_commands
import os
import ast # Used to safely convert strings "[1, 2]" back to lists [1, 2]
import typing

WELCOME_GIF_DIR = "cogs/welcome_gifs"

PERKS = {
    "default": {"multiplier": 1.0, "daily_bonus": 0, "shop_discount": 0.0, "pay_limit": 10000, "flair": ""},
    "elite": {"multiplier": 1.2, "daily_bonus": 250, "shop_discount": 0.0, "pay_limit": 25000, "flair": "💠"},
    "master": {"multiplier": 1.5, "daily_bonus": 750, "shop_discount": 0.05, "pay_limit": 25000, "flair": "🏆"},
    "supreme": {"multiplier": 2.0, "daily_bonus": 2000, "shop_discount": 0.10, "pay_limit": 25000, "flair": "👑"}
}

# --- HELPER FUNCTIONS (Now Async!) ---
async def get_guild_setting(bot, guild_id, key, default=None):
    return await bot.db.get_guild_setting(guild_id, key, default)

async def get_member_perks(bot, member: discord.Member) -> dict:
    if not member or not isinstance(member, discord.Member): return PERKS["default"]
    
    # We fetch the role IDs from DB
    supreme_id = await bot.db.get_guild_setting(member.guild.id, "SUPREME_ROLE_ID")
    master_id = await bot.db.get_guild_setting(member.guild.id, "MASTER_ROLE_ID")
    elite_id = await bot.db.get_guild_setting(member.guild.id, "ELITE_ROLE_ID")

    role_ids = {role.id for role in member.roles}
    
    if supreme_id and int(supreme_id) in role_ids: return PERKS["supreme"]
    if master_id and int(master_id) in role_ids: return PERKS["master"]
    if elite_id and int(elite_id) in role_ids: return PERKS["elite"]
    return PERKS["default"]

# Helper to check permissions asynchronously
async def is_owner_or_has_admin_role(interaction: discord.Interaction) -> bool:
    if interaction.user.id == interaction.guild.owner_id: return True
    
    # We need to access the bot via the interaction
    raw_admin = await interaction.client.db.get_guild_setting(interaction.guild.id, "ADMIN_ROLES")
    if not raw_admin: return False
    
    try:
        admin_role_ids = set(ast.literal_eval(raw_admin))
    except:
        return False
        
    user_role_ids = {role.id for role in interaction.user.roles}
    return not user_role_ids.isdisjoint(admin_role_ids)


class ChannelConfigCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not os.path.exists(WELCOME_GIF_DIR):
            os.makedirs(WELCOME_GIF_DIR)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot: return
        
        join_role_id = await self.bot.db.get_guild_setting(member.guild.id, "JOIN_ROLE_ID")
        if join_role_id:
            role = member.guild.get_role(int(join_role_id))
            if role:
                try: await member.add_roles(role, reason="Automatic role assignment")
                except: pass

        welcome_channel_id = await self.bot.db.get_guild_setting(member.guild.id, "WELCOME_CHANNEL_ID")
        if welcome_channel_id:
            welcome_channel = member.guild.get_channel(int(welcome_channel_id))
            if welcome_channel:
                rules_id = await self.bot.db.get_guild_setting(member.guild.id, "RULES_CHANNEL_ID")
                shop_id = await self.bot.db.get_guild_setting(member.guild.id, "SHOP_CHANNEL_ID")
                
                rules_mention = f"<#{rules_id}>" if rules_id else "the rules"
                shop_mention = f"<#{shop_id}>" if shop_id else "the shop"
                
                desc = f"Welcome {member.mention}!\n• Read {rules_mention}\n• Check {shop_mention}"
                embed = discord.Embed(title=f"Welcome to {member.guild.name}", description=desc, color=discord.Color.dark_grey())
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"Member #{member.guild.member_count}")
                
                # Check for GIF
                gif_path = f"{WELCOME_GIF_DIR}/{member.guild.id}.gif"
                if os.path.exists(gif_path):
                    await welcome_channel.send(file=discord.File(gif_path), embed=embed)
                else:
                    await welcome_channel.send(embed=embed)

    config_group = app_commands.Group(name="config", description="Configuration commands", default_permissions=discord.Permissions(administrator=True))

    @config_group.command(name="setup", description="Link channels.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction, shop: typing.Optional[discord.TextChannel] = None, welcome: typing.Optional[discord.TextChannel] = None):
        await interaction.response.defer(ephemeral=True)
        # Only implementing a few for brevity, works same as before
        if shop: await self.bot.db.set_guild_setting(interaction.guild.id, "SHOP_CHANNEL_ID", shop.id)
        if welcome: await self.bot.db.set_guild_setting(interaction.guild.id, "WELCOME_CHANNEL_ID", welcome.id)
        await interaction.followup.send("✅ Channels updated!", ephemeral=True)

    @config_group.command(name="addcreatorrole", description="Add a role that can upload items.")
    async def add_creator(self, interaction: discord.Interaction, role: discord.Role):
        current_raw = await self.bot.db.get_guild_setting(interaction.guild.id, "CREATOR_ROLE_IDS")
        current_list = ast.literal_eval(current_raw) if current_raw else []
        
        if role.id not in current_list:
            current_list.append(role.id)
            await self.bot.db.set_guild_setting(interaction.guild.id, "CREATOR_ROLE_IDS", str(current_list))
            await interaction.response.send_message(f"✅ Added {role.mention} as creator.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Role already added.", ephemeral=True)

    @config_group.command(name="setrankrole", description="Set rank roles.")
    @app_commands.choices(rank=[
        app_commands.Choice(name="Elite (Lvl 50)", value="ELITE_ROLE_ID"),
        app_commands.Choice(name="Master (Lvl 75)", value="MASTER_ROLE_ID"),
        app_commands.Choice(name="Supreme (Lvl 100)", value="SUPREME_ROLE_ID")
    ])
    async def set_rank(self, interaction: discord.Interaction, rank: str, role: discord.Role):
        await self.bot.db.set_guild_setting(interaction.guild.id, rank, role.id)
        await interaction.response.send_message(f"✅ Set {rank} to {role.mention}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelConfigCog(bot))