import discord
from discord.ext import commands
from discord import app_commands
from .channel_config import get_guild_setting, is_owner_or_has_admin_role, PERKS
import ast

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        else:
            print(f"An unhandled error occurred in AdminCog: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)

    @app_commands.command(name="synccreators", description="[Admin] Give the Creator role to all members at or above level 25.")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_creators(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Updated: Async DB fetch + Parse list
        raw_ids = await get_guild_setting(self.bot, interaction.guild.id, "CREATOR_ROLE_IDS")
        try:
            creator_role_ids = ast.literal_eval(raw_ids) if raw_ids else []
        except:
            creator_role_ids = []

        if not creator_role_ids:
            await interaction.followup.send("❌ No Creator roles configured. Use `/config addcreatorrole` first.", ephemeral=True)
            return
        
        all_users_data = await self.bot.db.get_all_users_in_guild(interaction.guild.id)
        eligible_users = [user for user in all_users_data if user['level'] >= 25]
        updated_count = 0
        
        for user_data in eligible_users:
            member = interaction.guild.get_member(user_data['user_id'])
            if member:
                current_role_ids = {role.id for role in member.roles}
                roles_to_add = []
                for role_id in creator_role_ids:
                    if role_id not in current_role_ids:
                        role = interaction.guild.get_role(int(role_id))
                        if role:
                            roles_to_add.append(role)
                if roles_to_add:
                    try:
                        await member.add_roles(*roles_to_add, reason="Syncing Creator roles")
                        updated_count += 1
                    except discord.Forbidden:
                        print(f"Failed to add creator role to {member.display_name}")
        
        await interaction.followup.send(f"✅ Sync complete! Updated **{updated_count}** eligible members.", ephemeral=True)

    @app_commands.command(name="syncranks", description="[Admin] Give rank roles to all members who meet level requirements.")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_ranks(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Updated: Fetch individual settings asynchronously
        supreme_id = await get_guild_setting(self.bot, interaction.guild.id, "SUPREME_ROLE_ID")
        master_id = await get_guild_setting(self.bot, interaction.guild.id, "MASTER_ROLE_ID")
        elite_id = await get_guild_setting(self.bot, interaction.guild.id, "ELITE_ROLE_ID")
        
        # Normalize IDs to int if they exist
        rank_roles_map = {
            100: (int(supreme_id) if supreme_id else None, "supreme"),
            75: (int(master_id) if master_id else None, "master"),
            50: (int(elite_id) if elite_id else None, "elite")
        }

        if not any(role_id for role_id, _ in rank_roles_map.values()):
            await interaction.followup.send("❌ No rank roles configured. Use `/config setrankrole` to set them up.", ephemeral=True)
            return

        all_users_data = await self.bot.db.get_all_users_in_guild(interaction.guild.id)
        counts = {"elite": 0, "master": 0, "supreme": 0}
        
        await interaction.followup.send(f"Scanning **{len(all_users_data)}** members...", ephemeral=True)

        for user_data in all_users_data:
            member = interaction.guild.get_member(user_data['user_id'])
            if not member or member.bot: continue

            user_level = user_data['level']
            
            for level_req, (role_id, perk_key) in sorted(rank_roles_map.items(), reverse=True):
                if user_level >= level_req and role_id:
                    role = interaction.guild.get_role(role_id)
                    if role and role not in member.roles:
                        try:
                            await member.add_roles(role, reason=f"Retroactive promotion")
                            counts[perk_key] += 1
                            
                            # DM Logic
                            perk_info = PERKS[perk_key]
                            embed = discord.Embed(title="🎉 You've Been Promoted!", description=f"You earned the **{role.name}** rank!", color=discord.Color.brand_green())
                            embed.add_field(name="💰 Boost", value=f"**{perk_info['multiplier']:.1f}x** Coins & XP!", inline=False)
                            await member.send(embed=embed)
                        except: pass
                        break 
        
        summary = f"**Supreme:** {counts['supreme']} | **Master:** {counts['master']} | **Elite:** {counts['elite']}"
        await interaction.followup.send(f"✅ **Rank Sync Complete**\n{summary}", ephemeral=True)

    @app_commands.command(name="removecoins", description="[Admin] Remove coins from a user.")
    @app_commands.check(is_owner_or_has_admin_role)
    async def removecoins(self, interaction: discord.Interaction, user: discord.User, amount: int):
        await interaction.response.defer()
        if amount <= 0: return await interaction.followup.send("Please provide a positive number.", ephemeral=True)
        
        player = await self.bot.db.get_user_data(user.id, interaction.guild.id)
        new_balance = max(0, player['balance'] - amount)
        await self.bot.db.update_user_data(user.id, interaction.guild.id, {"balance": new_balance})
        await interaction.followup.send(f"✅ Removed **{amount:,}** coins from {user.mention}.")

    adminrole_group = app_commands.Group(name="adminrole", description="Manage which roles have admin access.")

    @adminrole_group.command(name="add", description="[Admin] Grant a role admin command access.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_admin_role(self, interaction: discord.Interaction, role: discord.Role):
        # Updated: Read -> Parse -> Append -> Save
        raw_roles = await get_guild_setting(self.bot, interaction.guild.id, "ADMIN_ROLES")
        try:
            admin_roles = ast.literal_eval(raw_roles) if raw_roles else []
        except: admin_roles = []

        if role.id in admin_roles:
            return await interaction.response.send_message(f"❌ {role.mention} is already an admin role.", ephemeral=True)
            
        admin_roles.append(role.id)
        await self.bot.db.set_guild_setting(interaction.guild.id, "ADMIN_ROLES", str(admin_roles))
        await interaction.response.send_message(f"✅ Granted admin access to {role.mention}.", ephemeral=True)

    @adminrole_group.command(name="remove", description="[Admin] Revoke a role's admin command access.")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_admin_role(self, interaction: discord.Interaction, role: discord.Role):
        raw_roles = await get_guild_setting(self.bot, interaction.guild.id, "ADMIN_ROLES")
        try:
            admin_roles = ast.literal_eval(raw_roles) if raw_roles else []
        except: admin_roles = []

        if role.id not in admin_roles:
            return await interaction.response.send_message(f"❌ {role.mention} is not an admin role.", ephemeral=True)
            
        admin_roles.remove(role.id)
        await self.bot.db.set_guild_setting(interaction.guild.id, "ADMIN_ROLES", str(admin_roles))
        await interaction.response.send_message(f"✅ Revoked admin access from {role.mention}.", ephemeral=True)

    @adminrole_group.command(name="list", description="[Admin] List all roles with admin command access.")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_admin_roles(self, interaction: discord.Interaction):
        raw_roles = await get_guild_setting(self.bot, interaction.guild.id, "ADMIN_ROLES")
        try:
            admin_role_ids = ast.literal_eval(raw_roles) if raw_roles else []
        except: admin_role_ids = []
        
        if not admin_role_ids:
            return await interaction.response.send_message("No admin roles configured.", ephemeral=True)
            
        roles = [interaction.guild.get_role(r_id) for r_id in admin_role_ids]
        desc = "\n".join(r.mention for r in roles if r)
        embed = discord.Embed(title="⚙️ Admin Roles", description=desc, color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="givecoins", description="[Admin] Give coins to a user.")
    @app_commands.check(is_owner_or_has_admin_role)
    async def givecoins(self, interaction: discord.Interaction, user: discord.User, amount: int):
        await interaction.response.defer()
        player = await self.bot.db.get_user_data(user.id, interaction.guild.id)
        new_balance = player['balance'] + amount
        await self.bot.db.update_user_data(user.id, interaction.guild.id, {"balance": new_balance})
        await interaction.followup.send(f"✅ Gave **{amount:,}** coins to {user.mention}.")

    @app_commands.command(name="removeitem", description="[Admin] Remove an item from the shop.")
    @app_commands.check(is_owner_or_has_admin_role)
    async def removeitem(self, interaction: discord.Interaction, item_id: int):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.delete_item(item_id, interaction.guild.id)
        await interaction.followup.send(f"Successfully removed item ID `{item_id}`.")

    @app_commands.command(name="resetlevels", description="[Admin] Reset levels for players above level 11.")
    @app_commands.check(is_owner_or_has_admin_role)
    async def resetlevels(self, interaction: discord.Interaction, user: discord.User = None):
        await interaction.response.defer(ephemeral=True)
        if user:
            await self.bot.db.update_user_data(user.id, interaction.guild.id, {"level": 1, "xp": 0})
            await interaction.followup.send(f"✅ Reset level for {user.mention}.")
        else:
            all_users = await self.bot.db.get_all_users_in_guild(interaction.guild.id)
            updated = 0
            for user_data in all_users:
                if user_data['level'] > 11:
                    await self.bot.db.update_user_data(user_data['user_id'], interaction.guild.id, {"level": 9, "xp": 0})
                    updated += 1
            await interaction.followup.send(f"✅ Reset complete! Affected **{updated}** players.")

    @app_commands.command(name="featureitem", description="[Admin] Feature an item in the new shop view.")
    @app_commands.check(is_owner_or_has_admin_role)
    async def feature_item(self, interaction: discord.Interaction, item_id: int):
        await interaction.response.defer(ephemeral=True)
        item = await self.bot.db.get_item_details(item_id, interaction.guild.id)
        if not item: return await interaction.followup.send(f"❌ Item `{item_id}` not found.", ephemeral=True)
        await self.bot.db.set_featured_item(item_id, interaction.guild.id)
        await interaction.followup.send(f"✅ **{item['item_name']}** is now featured!")

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))