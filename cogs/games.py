# cogs/games.py

import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio

# --- Blackjack Game View (Fair Rules) ---
class BlackjackView(discord.ui.View):
    def __init__(self, bot, author, player_data, bet):
        super().__init__(timeout=120)
        self.bot = bot
        self.author = author
        self.player_data = player_data
        self.bet = bet
        self.deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        random.shuffle(self.deck)
        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ This is not your game!", ephemeral=True)
            return False
        return True

    def calculate_hand_value(self, hand):
        value = sum(hand)
        aces = hand.count(11)
        while value > 21 and aces:
            value -= 10
            aces -= 1
        return value

    async def update_message(self, interaction: discord.Interaction):
        player_score = self.calculate_hand_value(self.player_hand)
        embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.dark_green())
        embed.set_author(name=f"{self.author.display_name}'s game")
        embed.add_field(name="Your Hand", value=f"{' '.join(map(str, self.player_hand))}  (**{player_score}**)", inline=False)
        embed.add_field(name="Dealer's Hand", value=f"{self.dealer_hand[0]} ?", inline=False)
        embed.set_footer(text="Tip: Try to get closer to 21 than the dealer without going over!")
        await interaction.edit_original_response(embed=embed, view=self)

    async def handle_game_end(self, interaction, result):
        dealer_score = self.calculate_hand_value(self.dealer_hand)
        
        file = None
        if result == "win" or result == "blackjack":
            file = discord.File("cogs/win.gif", filename="win.gif")
            if result == "win":
                new_balance = self.player_data['balance'] + self.bet
                title = "🎉 You Won! 🎉"
                desc = f"You won **{self.bet*2:,}** coins!"
            else: # Blackjack
                new_balance = self.player_data['balance'] + int(self.bet * 1.5)
                title = "✨ BLACKJACK! ✨"
                desc = f"You won **{int(self.bet * 2.5):,}** coins!"
        elif result == "push":
            file = discord.File("cogs/tie.gif", filename="tie.gif")
            new_balance = self.player_data['balance']
            title = "🤝 Push 🤝"
            desc = "It's a tie! Your bet has been returned."
        else: # loss
            file = discord.File("cogs/loss.gif", filename="loss.gif")
            new_balance = self.player_data['balance'] - self.bet
            title = "💔 You Lost 💔"
            desc = f"The dealer won. You lost **{self.bet:,}** coins."
            
        await self.bot.db.update_user_data(self.author.id, self.author.guild.id, {"balance": new_balance})
        
        embed = discord.Embed(title=title, description=desc, color=discord.Color.blue())
        embed.add_field(name="Your Hand", value=f"{' '.join(map(str, self.player_hand))} (**{self.calculate_hand_value(self.player_hand)}**)", inline=True)
        embed.add_field(name="Dealer's Hand", value=f"{' '.join(map(str, self.dealer_hand))} (**{dealer_score}**)", inline=True)
        embed.set_footer(text=f"New Balance: {new_balance:,}")

        attachments = [file] if file else []
        if file:
            embed.set_thumbnail(url=f"attachment://{file.filename}")
        
        await interaction.edit_original_response(embed=embed, view=None, attachments=attachments)
        self.stop()

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.player_hand.append(self.deck.pop())
        player_score = self.calculate_hand_value(self.player_hand)
        if player_score > 21:
            await self.handle_game_end(interaction, "loss")
        else:
            await self.update_message(interaction)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player_score = self.calculate_hand_value(self.player_hand)
        dealer_score = self.calculate_hand_value(self.dealer_hand)
        while dealer_score < 17:
            self.dealer_hand.append(self.deck.pop())
            dealer_score = self.calculate_hand_value(self.dealer_hand)
            
        if dealer_score > 21 or player_score > dealer_score:
            await self.handle_game_end(interaction, "win")
        elif player_score == dealer_score:
            await self.handle_game_end(interaction, "push")
        else:
            await self.handle_game_end(interaction, "loss")


class GamesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def check_player_can_bet(self, interaction: discord.Interaction, player_data: dict, bet: int) -> bool:
        """A helper function to check if a player can afford their bet."""
        if bet <= 0:
            await interaction.followup.send("❌ You must bet a positive amount of coins.", ephemeral=True)
            return False
        if player_data['balance'] < bet:
            await interaction.followup.send(f"❌ You don't have enough coins! Your balance is **{player_data['balance']:,}**.", ephemeral=True)
            return False
        return True

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} cog has been loaded.')

    @app_commands.command(name="slots", description="Play the slot machine for a chance to win big!")
    @app_commands.describe(bet="The amount of coins you want to bet.")
    async def slots(self, interaction: discord.Interaction, bet: int):
        await interaction.response.defer()
        player = await self.bot.db.get_user_data(interaction.user.id, interaction.guild.id)
        if not await self.check_player_can_bet(interaction, player, bet):
            return

        emojis = ["🍒", "🍊", "🔔", "💎", "💰"] 
        reels = [random.choice(emojis) for _ in range(3)]
        result_str = " | ".join(reels)
        
        payout = 0
        if reels[0] == reels[1] == reels[2]:
            if reels[0] == "💰": payout = bet * 8
            elif reels[0] == "💎": payout = bet * 7
            elif reels[0] == "🔔": payout = bet * 6
            else: payout = bet * 4
        elif reels[0] == reels[1] or reels[1] == reels[2]:
            payout = int(bet * 1.5)
        elif reels[0] == reels[2]:
            payout = bet

        new_balance = player['balance'] - bet + payout
        await self.bot.db.update_user_data(interaction.user.id, interaction.guild.id, {"balance": new_balance})
        
        embed = discord.Embed(title="🎰 Slot Machine 🎰")
        embed.set_author(name=f"{interaction.user.display_name}'s game")
        embed.add_field(name="Result", value=f"**[ {result_str} ]**", inline=False)
        
        file = None
        if payout > bet:
            file = discord.File("cogs/win.gif", filename="win.gif")
            embed.description = f"🎉 **YOU WON!** 🎉\nYou won **{payout:,}** coins!"
            embed.color = discord.Color.green()
        elif payout == bet:
            file = discord.File("cogs/tie.gif", filename="tie.gif")
            embed.description = f"🙌 **PUSH!** 🙌\nYou got your bet of **{bet:,}** back!"
            embed.color = discord.Color.light_grey()
        else:
            file = discord.File("cogs/loss.gif", filename="loss.gif")
            embed.description = f"💔 **You lost.** Better luck next time!"
            embed.color = discord.Color.red()
        
        footer_text = f"New Balance: {new_balance:,} | Tip: Match three 💰 for the jackpot!"
        embed.set_footer(text=footer_text)
        
        if file:
            embed.set_thumbnail(url=f"attachment://{file.filename}")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)
    

    @app_commands.command(name="coinflip", description="Bet on a 50/50 coin flip.")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip(self, interaction: discord.Interaction, bet: int, choice: str):
        await interaction.response.defer()
        player = await self.bot.db.get_user_data(interaction.user.id, interaction.guild.id)
        if not await self.check_player_can_bet(interaction, player, bet):
            return

        outcome = random.choice(["heads", "tails"])
        won = (choice.lower() == outcome)
        
        if won:
            file = discord.File("cogs/win.gif", filename="win.gif")
            new_balance = player['balance'] + bet
            title = "🎉 You Won! 🎉"
            color = discord.Color.green()
            description = f"The coin landed on **{outcome.title()}**. You won **{bet*2:,}** coins!"
        else:
            file = discord.File("cogs/loss.gif", filename="loss.gif")
            new_balance = player['balance'] - bet
            title = "💔 You Lost 💔"
            color = discord.Color.red()
            description = f"The coin landed on **{outcome.title()}**. You lost **{bet:,}** coins."
            
        await self.bot.db.update_user_data(interaction.user.id, interaction.guild.id, {"balance": new_balance})
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_thumbnail(url=f"attachment://{file.filename}")
        embed.set_author(name=f"{interaction.user.display_name}'s coin flip")
        embed.set_footer(text=f"New Balance: {new_balance:,} | Tip: This is a true 50/50 chance!")
        await interaction.followup.send(embed=embed, file=file)


    @app_commands.command(name="blackjack", description="Play a game of Blackjack against the bot.")
    @app_commands.describe(bet="The amount of coins to bet.")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        await interaction.response.defer()
        player = await self.bot.db.get_user_data(interaction.user.id, interaction.guild.id)
        if not await self.check_player_can_bet(interaction, player, bet):
            return

        view = BlackjackView(self.bot, interaction.user, player, bet)
        player_score = view.calculate_hand_value(view.player_hand)
        
        embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.dark_green())
        embed.set_author(name=f"{interaction.user.display_name}'s game")
        embed.add_field(name="Your Hand", value=f"{' '.join(map(str, view.player_hand))}  (**{player_score}**)", inline=False)
        embed.add_field(name="Dealer's Hand", value=f"{view.dealer_hand[0]} ?", inline=False)
        embed.set_footer(text="Tip: Try to get closer to 21 than the dealer without going over!")
        await interaction.followup.send(embed=embed, view=view)

        if player_score == 21:
            await asyncio.sleep(1) # Give player a moment to see their blackjack
            await view.handle_game_end(interaction, "blackjack")


    @app_commands.command(name="roulette", description="Play a game of Roulette.")
    @app_commands.describe(bet="The amount to bet.", space="The space to bet on (e.g., 'red', 'black', or a number 0-36).")
    async def roulette(self, interaction: discord.Interaction, bet: int, space: str):
        await interaction.response.defer()
        player = await self.bot.db.get_user_data(interaction.user.id, interaction.guild.id)
        if not await self.check_player_can_bet(interaction, player, bet):
            return
        
        space = space.lower()
        red_numbers = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        winning_number = random.randint(0, 36)
        
        payout = 0; won = False
        if space.isdigit() and 0 <= int(space) <= 36:
            if int(space) == winning_number:
                payout = bet * 35; won = True
        elif space == "red":
            if winning_number in red_numbers:
                payout = bet; won = True
        elif space == "black":
            if winning_number != 0 and winning_number not in red_numbers:
                payout = bet; won = True
        elif space == "even":
            if winning_number != 0 and winning_number % 2 == 0:
                payout = bet; won = True
        elif space == "odd":
            if winning_number % 2 != 0:
                payout = bet; won = True
        else:
            await interaction.followup.send("❌ Invalid space. Please bet on 'red', 'black', 'even', 'odd', or a number between 0 and 36.", ephemeral=True); return
        
        result_color = "Red" if winning_number in red_numbers else ("Green" if winning_number == 0 else "Black")
        embed = discord.Embed(title="🎡 Roulette 🎡", description=f"The ball landed on **{winning_number} ({result_color})**", color=discord.Color.dark_magenta())
        
        if won:
            file = discord.File("cogs/win.gif", filename="win.gif")
            new_balance = player['balance'] + payout
            embed.add_field(name="🎉 You Won! 🎉", value=f"Your bet on **{space.title()}** won! You get **{payout:,}** coins!")
        else:
            file = discord.File("cogs/loss.gif", filename="loss.gif")
            new_balance = player['balance'] - bet
            embed.add_field(name="💔 You Lost 💔", value=f"Your bet on **{space.title()}** lost. You lose **{bet:,}** coins.")
            
        await self.bot.db.update_user_data(interaction.user.id, interaction.guild.id, {"balance": new_balance})
        embed.set_thumbnail(url=f"attachment://{file.filename}")
        embed.set_footer(text=f"New Balance: {new_balance:,} | Tip: Betting on a number pays 35x!")
        await interaction.followup.send(embed=embed, file=file)


    @app_commands.command(name="rps", description="Play Rock, Paper, Scissors.")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Rock ✊", value="rock"),
        app_commands.Choice(name="Paper ✋", value="paper"),
        app_commands.Choice(name="Scissors ✌️", value="scissors")
    ])
    async def rps(self, interaction: discord.Interaction, bet: int, choice: str):
        await interaction.response.defer()
        player = await self.bot.db.get_user_data(interaction.user.id, interaction.guild.id)
        if not await self.check_player_can_bet(interaction, player, bet):
            return
        
        bot_choice = random.choice(["rock", "paper", "scissors"])

        winner = None 
        if choice == bot_choice: winner = None
        elif (choice == "rock" and bot_choice == "scissors") or \
             (choice == "paper" and bot_choice == "rock") or \
             (choice == "scissors" and bot_choice == "paper"):
            winner = True
        else: winner = False

        file = None
        if winner is True:
            file = discord.File("cogs/win.gif", filename="win.gif")
            new_balance = player['balance'] + bet
            result_text = f"You won! You chose **{choice.title()}** and I chose **{bot_choice.title()}**."
        elif winner is False:
            file = discord.File("cogs/loss.gif", filename="loss.gif")
            new_balance = player['balance'] - bet
            result_text = f"You lost! You chose **{choice.title()}** and I chose **{bot_choice.title()}**."
        else: # Tie
            file = discord.File("cogs/tie.gif", filename="tie.gif")
            new_balance = player['balance']
            result_text = f"It's a tie! We both chose **{choice.title()}**."
            
        await self.bot.db.update_user_data(interaction.user.id, interaction.guild.id, {"balance": new_balance})
        embed = discord.Embed(title="✊ Rock, Paper, Scissors ✌️", description=result_text, color=discord.Color.orange())
        embed.set_footer(text=f"New Balance: {new_balance:,} | Tip: Paper beats Rock, Rock beats Scissors, Scissors beats Paper.")

        if file:
            embed.set_thumbnail(url=f"attachment://{file.filename}")
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(GamesCog(bot))
