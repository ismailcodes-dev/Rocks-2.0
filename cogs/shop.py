import discord
from discord.ext import commands
from discord import app_commands, ui
from .channel_config import get_member_perks, get_guild_setting
import math
import time
import datetime

COMMISSION_RATE = 0.80

class PurchaseView(ui.View):
    def __init__(self, bot: commands.Bot, item: dict, final_price: int, discount: float):
        super().__init__(timeout=180)
        self.bot = bot
        self.item = item
        self.final_price = final_price
        self.discount = discount

    @ui.button(label="Buy Now", style=discord.ButtonStyle.green, emoji="🛒")
    async def buy_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            # 1. Validate Purchase
            item_id = self.item['item_id']
            # Re-fetch item to ensure it still exists
            db_item = await self.bot.db.get_item_details(item_id, interaction.guild.id)
            player = await self.bot.db.get_user_data(interaction.user.id, interaction.guild.id)

            if not db_item:
                return await interaction.followup.send("❌ This item seems to have been removed from the shop.", ephemeral=True)
            if player['balance'] < self.final_price:
                return await interaction.followup.send(f"❌ You don't have enough coins! You need **{self.final_price:,}** coins.", ephemeral=True)

            # 2. Process Transaction
            original_price = db_item['price']
            commission_amount = int(original_price * COMMISSION_RATE)
            
            # Buyer pays
            new_balance_buyer = player['balance'] - self.final_price
            await self.bot.db.update_user_data(interaction.user.id, interaction.guild.id, {"balance": new_balance_buyer})
            
            # Creator gets paid
            creator_data = await self.bot.db.get_user_data(db_item['creator_id'], interaction.guild.id)
            new_balance_creator = creator_data['balance'] + commission_amount
            await self.bot.db.update_user_data(db_item['creator_id'], interaction.guild.id, {"balance": new_balance_creator})
            
            # Update stats
            await self.bot.db.increment_purchase_count(item_id, interaction.guild.id)
            
            # 3. Generate Premium Receipt
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            saved_amount = int(original_price - self.final_price)
            
            receipt_text = (
                "```yaml\n"
                "🧾 ROCKS 2.0 RECEIPT\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Item:     {db_item['item_name'][:20]}\n"
                f"Category: {db_item['category']}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Price:    {original_price:,} Coins\n"
                f"Discount: -{saved_amount:,} Coins\n"
                "------------------------------\n"
                f"Total:    {self.final_price:,} Coins\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Date:     {date_str}\n"
                "```"
            )
            
            # 4. Send DM
            dm_embed = discord.Embed(title="✅ Purchase Successful!", description=receipt_text, color=discord.Color.brand_green())
            dm_embed.add_field(name="📥 Download Link", value=f"**[Click Here to Download]({db_item['product_link']})**")
            dm_embed.set_footer(text="Thank you for your purchase!")
            
            try:
                await interaction.user.send(embed=dm_embed)
                await interaction.followup.send("✅ **Purchase complete!** I've sent the receipt and download link to your DMs.", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("⚠️ **Purchase Failed.** I couldn't send you a DM. Please enable DMs and try again.", ephemeral=True)

            # Log to channel if configured (Fetching from DB now)
            log_channel_id = await get_guild_setting(self.bot, interaction.guild.id, "PURCHASE_LOG_CHANNEL_ID")
            if log_channel_id:
                log_channel = self.bot.get_channel(int(log_channel_id))
                if log_channel:
                    await log_channel.send(f"🛒 **{interaction.user.name}** bought **{db_item['item_name']}** for {self.final_price} coins.")

        except Exception as e:
            print(f"Error during purchase: {e}")
            await interaction.followup.send("An unexpected error occurred. Please try again.", ephemeral=True)

class CategorySelect(ui.Select):
    def __init__(self, categories):
        # Limit to 25 categories due to Discord limits
        options = [discord.SelectOption(label="All Categories", value="all", emoji="🌐")]
        for cat in sorted(list(categories))[:24]:
            options.append(discord.SelectOption(label=cat, value=cat))
            
        super().__init__(placeholder="📂 Filter by Category...", min_values=1, max_values=1, options=options, row=3)

    async def callback(self, interaction: discord.Interaction):
        view: ShopView = self.view
        selected = self.values[0]
        await interaction.response.defer()
        
        if selected == "all":
            view.current_items = await view.bot.db.get_all_items(view.guild_id)
            view.current_tab = "all_items"
        else:
            all_items = await view.bot.db.get_all_items(view.guild_id)
            view.current_items = [item for item in all_items if item['category'] == selected]
            view.current_tab = "filtered"
            
        view.selected_index = 0
        await view.update_view(interaction)


class ShopView(ui.View):
    def __init__(self, bot: commands.Bot, author_id: int, guild_id: int, categories: set):
        super().__init__(timeout=300)
        self.bot = bot
        self.author_id = author_id
        self.guild_id = guild_id
        self.current_tab = "featured"
        self.current_items = []
        self.selected_index = 0
        self.items_in_view = 10
        
        if categories:
            self.add_item(CategorySelect(categories))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_id and interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This is not your shop session.", ephemeral=True)
            return False
        return True

    async def build_embed_and_components(self):
        guild = self.bot.get_guild(self.guild_id)
        embed = discord.Embed(title=f"🛍️ {guild.name} Marketplace", color=discord.Color.from_str("#5865F2"))
        
        self.clear_items()
        self.add_item(self.featured_button)
        self.add_item(self.new_button)
        self.add_item(self.all_items_button)
        
        content_description = ""
        thumbnail_url = "https://placehold.co/900x300/2b2d31/ffffff?text=Creator+Marketplace&font=raleway"
        
        if self.current_tab == "featured":
            featured_item = await self.bot.db.get_featured_item(self.guild_id)
            if featured_item:
                creator = await self.bot.fetch_user(featured_item['creator_id'])
                content_description = f"## ⭐ {featured_item['item_name']}\n*By {creator.display_name}*\n\n> A special item highlighted by our staff.\n\n**Price:** {featured_item['price']:,} coins"
                thumbnail_url = featured_item.get('screenshot_link')
                self.add_item(ui.Button(style=discord.ButtonStyle.green, label="🔍 View Item", custom_id=f"quick_view_{featured_item['item_id']}", row=1))
            else:
                content_description = "## ⭐ Featured Item\n\n> There is no featured item at the moment."
                
        elif self.current_tab in ["new", "all_items", "filtered"]:
            titles = {"new": "🚀 New Arrivals", "all_items": "📚 All Items", "filtered": "📂 Category Result"}
            content_description = f"## {titles.get(self.current_tab, 'Items')}\n\n"
            
            if self.current_items:
                start = max(0, self.selected_index - math.floor(self.items_in_view / 2))
                end = min(len(self.current_items), start + self.items_in_view)
                start = max(0, end - self.items_in_view)
                
                list_str = ""
                for i in range(start, end):
                    item = self.current_items[i]
                    prefix = "➤" if i == self.selected_index else "•"
                    
                    badges = ""
                    if time.time() - item.get('upload_timestamp', 0) < 259200: badges += "🆕 "
                    if item.get('purchase_count', 0) > 10: badges += "🔥 "
                    
                    list_str += f"{prefix} **{item['item_name']}** {badges}• `{item.get('price', 0):,} 🪙`\n"
                    
                content_description += list_str
                embed.set_footer(text=f"Showing item {self.selected_index + 1} of {len(self.current_items)} | Use arrows to scroll")
                
                if len(self.current_items) > 1:
                    self.scroll_up_button.disabled = self.selected_index == 0
                    self.scroll_down_button.disabled = self.selected_index == len(self.current_items) - 1
                    self.add_item(self.scroll_up_button)
                    self.add_item(self.scroll_down_button)
                self.add_item(self.select_item_button)
            else:
                content_description += "> Nothing to show here yet!"

        embed.set_image(url=thumbnail_url)
        embed.description = content_description
        return embed

    async def update_view(self, interaction: discord.Interaction):
        # Preserve category select
        cat_select = None
        for child in self.children:
            if isinstance(child, CategorySelect):
                cat_select = child
                break
        
        embed = await self.build_embed_and_components()
        
        if cat_select:
            self.add_item(cat_select)
            
        await interaction.edit_original_response(embed=embed, view=self)

    async def handle_tab_switch(self, interaction: discord.Interaction, tab_name: str):
        self.current_tab = tab_name
        self.selected_index = 0
        
        if self.current_tab == "new": 
            self.current_items = await self.bot.db.get_new_arrivals(self.guild_id, limit=None)
        elif self.current_tab == "all_items": 
            self.current_items = await self.bot.db.get_all_items(self.guild_id)
        else: 
            self.current_items = []
            
        self.featured_button.style = discord.ButtonStyle.primary if tab_name == "featured" else discord.ButtonStyle.secondary
        self.new_button.style = discord.ButtonStyle.primary if tab_name == "new" else discord.ButtonStyle.secondary
        self.all_items_button.style = discord.ButtonStyle.primary if tab_name == "all_items" else discord.ButtonStyle.secondary
        await self.update_view(interaction)

    @ui.button(label="⭐ Featured", style=discord.ButtonStyle.primary, custom_id="featured_tab", row=0)
    async def featured_button(self, i: discord.Interaction, b: ui.Button):
        await i.response.defer()
        await self.handle_tab_switch(i, "featured")

    @ui.button(label="🚀 New Arrivals", style=discord.ButtonStyle.secondary, custom_id="new_tab", row=0)
    async def new_button(self, i: discord.Interaction, b: ui.Button):
        await i.response.defer()
        await self.handle_tab_switch(i, "new")

    @ui.button(label="📚 All Items", style=discord.ButtonStyle.secondary, custom_id="all_items_tab", row=0)
    async def all_items_button(self, i: discord.Interaction, b: ui.Button):
        await i.response.defer()
        await self.handle_tab_switch(i, "all_items")

    @ui.button(emoji="🔼", style=discord.ButtonStyle.grey, custom_id="scroll_up", row=2)
    async def scroll_up_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.selected_index > 0:
            self.selected_index -= 1
            await interaction.response.defer()
            await self.update_view(interaction)

    @ui.button(emoji="🔽", style=discord.ButtonStyle.grey, custom_id="scroll_down", row=2)
    async def scroll_down_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.selected_index < len(self.current_items) - 1:
            self.selected_index += 1
            await interaction.response.defer()
            await self.update_view(interaction)

    @ui.button(label="View Item", style=discord.ButtonStyle.green, custom_id="select_item", row=1)
    async def select_item_button(self, interaction: discord.Interaction, button: ui.Button):
        if not self.current_items: return
        item_data = self.current_items[self.selected_index]
        await self.show_item_details(interaction, item_data['item_id'])

    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data.get("custom_id", "").startswith("quick_view_"):
            item_id = int(interaction.data["custom_id"].split("_")[2])
            await self.show_item_details(interaction, item_id)

    async def show_item_details(self, interaction: discord.Interaction, item_id: int):
        await interaction.response.defer(ephemeral=True)
        item = await self.bot.db.get_item_details(item_id, interaction.guild.id)
        if not item: return await interaction.followup.send("❌ This item could not be found.", ephemeral=True)
        
        creator = await self.bot.fetch_user(item['creator_id'])
        # Updated: Async call to get perks
        perks = await get_member_perks(self.bot, interaction.user)
        final_price = int(item['price'] * (1 - perks['shop_discount']))

        embed = discord.Embed(title=item['item_name'], color=discord.Color.from_str("#5865F2"))
        embed.set_author(name=f"Created by {creator.display_name}", icon_url=creator.display_avatar.url)
        
        price_str = f"**{final_price:,}** coins"
        if perks['shop_discount'] > 0:
            price_str += f" (~~{item['price']:,}~~) with your **{perks['shop_discount']:.0%}** discount!"
            
        embed.add_field(name="Price", value=price_str)
        embed.add_field(name="Category", value=item['category'])
        embed.add_field(name="Stats", value=f"🛒 {item.get('purchase_count',0)} sold")
        
        if item.get('screenshot_link'): embed.set_image(url=item['screenshot_link'])
        
        await interaction.followup.send(embed=embed, view=PurchaseView(self.bot, item, final_price, perks['shop_discount']), ephemeral=True)


class ShopCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} cog has been loaded.')

    @app_commands.command(name="shop", description="Open the interactive marketplace.")
    async def shop(self, interaction: discord.Interaction):
        # Updated: Async call to get setting
        shop_channel_id = await get_guild_setting(self.bot, interaction.guild.id, "SHOP_CHANNEL_ID")
        
        if shop_channel_id and interaction.channel.id != int(shop_channel_id):
            shop_channel = self.bot.get_channel(int(shop_channel_id))
            await interaction.response.send_message(f"❌ The shop can only be used in {shop_channel.mention if shop_channel else 'a missing channel'}.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        all_items = await self.bot.db.get_all_items(interaction.guild.id)
        categories = set(item['category'] for item in all_items)
        
        view = ShopView(self.bot, interaction.user.id, interaction.guild.id, categories)
        await view.handle_tab_switch(interaction, "featured")

    @app_commands.command(name="search", description="Search for an item in the shop.")
    async def search(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)
        if len(query) < 3: return await interaction.followup.send("Please enter at least 3 characters.", ephemeral=True)
        
        results = await self.bot.db.search_items(interaction.guild.id, query)
        if not results: return await interaction.followup.send(f"No items found matching `{query}`.", ephemeral=True)
        
        embed = discord.Embed(title=f"🔎 Search Results for `{query}`", description=f"Found **{len(results)}** item(s). Use `/shop` to browse properly.", color=discord.Color.blue())
        for item in results[:5]:
            embed.add_field(name=item['item_name'], value=f"{item['price']:,} coins", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ShopCog(bot))