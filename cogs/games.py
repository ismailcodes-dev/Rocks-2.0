# cogs/games.py

import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import aiohttp
import html
import time

# --- Blackjack Game View ---
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
            # file = discord.File("cogs/win.gif", filename="win.gif") # Uncomment if you have the file
            if result == "win":
                new_balance = self.player_data['balance'] + self.bet
                title = "🎉 You Won! 🎉"
                desc = f"You won **{self.bet*2:,}** coins!"
            else: # Blackjack
                new_balance = self.player_data['balance'] + int(self.bet * 1.5)
                title = "✨ BLACKJACK! ✨"
                desc = f"You won **{int(self.bet * 2.5):,}** coins!"
        elif result == "push":
            new_balance = self.player_data['balance']
            title = "🤝 Push 🤝"
            desc = "It's a tie! Your bet has been returned."
        else: # loss
            new_balance = self.player_data['balance'] - self.bet
            title = "💔 You Lost 💔"
            desc = f"The dealer won. You lost **{self.bet:,}** coins."
            
        await self.bot.db.update_user_data(self.author.id, self.author.guild.id, {"balance": new_balance})
        
        embed = discord.Embed(title=title, description=desc, color=discord.Color.blue())
        embed.add_field(name="Your Hand", value=f"{' '.join(map(str, self.player_hand))} (**{self.calculate_hand_value(self.player_hand)}**)", inline=True)
        embed.add_field(name="Dealer's Hand", value=f"{' '.join(map(str, self.dealer_hand))} (**{dealer_score}**)", inline=True)
        embed.set_footer(text=f"New Balance: {new_balance:,}")

        # if file: embed.set_thumbnail(url=f"attachment://{file.filename}")
        
        await interaction.edit_original_response(embed=embed, view=None) # attachments=[file] if file else []
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

    # --- EXISTING GAMES (Slots, Coinflip, Roulette, RPS, Blackjack) ---
    
    @app_commands.command(name="slots", description="Play the slot machine!")
    async def slots(self, interaction: discord.Interaction, bet: int):
        await interaction.response.defer()
        player = await self.bot.db.get_user_data(interaction.user.id, interaction.guild.id)
        if not await self.check_player_can_bet(interaction, player, bet): return

        emojis = ["🍒", "🍊", "🔔", "💎", "💰"] 
        reels = [random.choice(emojis) for _ in range(3)]
        
        payout = 0
        if reels[0] == reels[1] == reels[2]:
            payout = bet * (8 if reels[0] == "💰" else 4)
        elif reels[0] == reels[1] or reels[1] == reels[2]:
            payout = int(bet * 1.5)
            
        new_balance = player['balance'] - bet + payout
        await self.bot.db.update_user_data(interaction.user.id, interaction.guild.id, {"balance": new_balance})
        
        embed = discord.Embed(title="🎰 Slot Machine", description=f"**[ {' | '.join(reels)} ]**", color=discord.Color.gold())
        if payout > 0: embed.add_field(name="WINNER!", value=f"You won **{payout:,}** coins!")
        else: embed.add_field(name="Lost", value="Better luck next time.")
        embed.set_footer(text=f"New Balance: {new_balance:,}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="coinflip", description="Bet on Heads or Tails.")
    @app_commands.choices(choice=[app_commands.Choice(name="Heads", value="heads"), app_commands.Choice(name="Tails", value="tails")])
    async def coinflip(self, interaction: discord.Interaction, bet: int, choice: str):
        await interaction.response.defer()
        player = await self.bot.db.get_user_data(interaction.user.id, interaction.guild.id)
        if not await self.check_player_can_bet(interaction, player, bet): return

        outcome = random.choice(["heads", "tails"])
        won = (choice.lower() == outcome)
        new_balance = player['balance'] + bet if won else player['balance'] - bet
        
        await self.bot.db.update_user_data(interaction.user.id, interaction.guild.id, {"balance": new_balance})
        embed = discord.Embed(title="🪙 Coin Flip", description=f"The coin landed on **{outcome.title()}**!", color=discord.Color.green() if won else discord.Color.red())
        embed.add_field(name="Result", value=f"You {'won' if won else 'lost'} **{bet if won else bet:,}** coins.")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="blackjack", description="Play Blackjack.")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        await interaction.response.defer()
        player = await self.bot.db.get_user_data(interaction.user.id, interaction.guild.id)
        if not await self.check_player_can_bet(interaction, player, bet): return
        view = BlackjackView(self.bot, interaction.user, player, bet)
        player_score = view.calculate_hand_value(view.player_hand)
        embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.dark_green())
        embed.set_author(name=f"{interaction.user.display_name}'s game")
        embed.add_field(name="Your Hand", value=f"{' '.join(map(str, view.player_hand))}  (**{player_score}**)", inline=False)
        embed.add_field(name="Dealer's Hand", value=f"{view.dealer_hand[0]} ?", inline=False)
        await interaction.followup.send(embed=embed, view=view)
        if player_score == 21:
            await asyncio.sleep(1)
            await view.handle_game_end(interaction, "blackjack")

    # --- NEW GAME 1: CRASH (Stock Market Style) ---
    @app_commands.command(name="crash", description="Bet on a rising multiplier. Auto-cashout before it crashes!")
    @app_commands.describe(bet="Coins to bet", auto_cashout="Target multiplier (e.g. 2.0)")
    async def crash(self, interaction: discord.Interaction, bet: int, auto_cashout: float):
        await interaction.response.defer()
        player = await self.bot.db.get_user_data(interaction.user.id, interaction.guild.id)
        
        if not await self.check_player_can_bet(interaction, player, bet): return
        if auto_cashout < 1.1:
            return await interaction.followup.send("❌ Auto-cashout must be at least 1.1x", ephemeral=True)

        # Crash Algorithm: Weighted random
        # 3% chance of instant crash (1.0x)
        if random.random() < 0.03:
            crash_point = 1.00
        else:
            # Generate crash point (favors lower numbers)
            crash_point = 0.99 * (1 / (1 - random.random()))
            crash_point = max(1.0, crash_point)

        won = auto_cashout <= crash_point
        
        # Visuals
        embed = discord.Embed(title="🚀 Crash", description="The rocket is taking off...", color=discord.Color.blue())
        embed.add_field(name="Your Target", value=f"**{auto_cashout}x**", inline=True)
        embed.add_field(name="Bet", value=f"{bet:,}", inline=True)
        msg = await interaction.followup.send(embed=embed)

        # Animation Loop (Fake the rise)
        current_display = 1.0
        while current_display < crash_point and current_display < auto_cashout + 0.5:
            await asyncio.sleep(0.7)
            # Increase display multiplier
            increment = 0.1 + (current_display * 0.1) # Speeds up as it goes higher
            current_display += increment
            
            if current_display >= crash_point: 
                current_display = crash_point
                break
                
            embed.description = f"🚀 **{current_display:.2f}x**"
            try: await msg.edit(embed=embed)
            except: break
        
        # Final Result
        if won:
            profit = int(bet * auto_cashout) - bet
            new_balance = player['balance'] + profit
            embed.title = "✅ SUCESSFUL CASHOUT"
            embed.description = f"Crashed at **{crash_point:.2f}x**\nYou cashed out at **{auto_cashout:.2f}x**"
            embed.color = discord.Color.green()
            embed.add_field(name="Profit", value=f"+{profit:,} coins", inline=False)
        else:
            new_balance = player['balance'] - bet
            embed.title = "💥 CRASHED!"
            embed.description = f"Crashed at **{crash_point:.2f}x**\nYou needed **{auto_cashout:.2f}x**"
            embed.color = discord.Color.red()
            embed.add_field(name="Loss", value=f"-{bet:,} coins", inline=False)

        embed.set_footer(text=f"New Balance: {new_balance:,}")
        await self.bot.db.update_user_data(interaction.user.id, interaction.guild.id, {"balance": new_balance})
        await msg.edit(embed=embed)

    # --- NEW GAME 2: TRIVIA ---
    @app_commands.command(name="trivia", description="Answer a trivia question to win coins!")
    async def trivia(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # 1. Fetch Question from OpenTDB
        url = "https://opentdb.com/api.php?amount=1&type=multiple"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await interaction.followup.send("❌ Could not fetch a question. Try again later.")
                data = await resp.json()
        
        if data['response_code'] != 0:
            return await interaction.followup.send("❌ Trivia API error.")

        question_data = data['results'][0]
        question = html.unescape(question_data['question'])
        correct_answer = html.unescape(question_data['correct_answer'])
        wrong_answers = [html.unescape(a) for a in question_data['incorrect_answers']]
        
        # 2. Shuffle answers
        all_answers = wrong_answers + [correct_answer]
        random.shuffle(all_answers)
        
        # Map letters to answers
        options_map = {0: 'A', 1: 'B', 2: 'C', 3: 'D'}
        answer_text = ""
        correct_letter = ""
        
        for i, ans in enumerate(all_answers):
            letter = options_map[i]
            answer_text += f"**{letter})** {ans}\n"
            if ans == correct_answer:
                correct_letter = letter

        embed = discord.Embed(title="🧠 Trivia Time!", description=f"**Category:** {question_data['category']}\n**Difficulty:** {question_data['difficulty'].title()}\n\n**{question}**\n\n{answer_text}", color=discord.Color.purple())
        embed.set_footer(text="Type A, B, C, or D in the chat! First correct answer wins 250 coins.")
        await interaction.followup.send(embed=embed)

        # 3. Wait for Answer
        def check(m):
            return m.channel == interaction.channel and not m.author.bot and m.content.upper() in ['A', 'B', 'C', 'D']

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            
            if msg.content.upper() == correct_letter:
                reward = 250
                winner_data = await self.bot.db.get_user_data(msg.author.id, interaction.guild.id)
                await self.bot.db.update_user_data(msg.author.id, interaction.guild.id, {"balance": winner_data['balance'] + reward})
                
                await msg.reply(f"🎉 **Correct!** {msg.author.mention} won **{reward}** coins! The answer was **{correct_answer}**.")
            else:
                await msg.reply(f"❌ **Wrong!** The correct answer was **{correct_letter}) {correct_answer}**.")
                
        except asyncio.TimeoutError:
            await interaction.followup.send(f"⏰ Time's up! The correct answer was **{correct_letter}) {correct_answer}**.")

async def setup(bot: commands.Bot):
    await bot.add_cog(GamesCog(bot))