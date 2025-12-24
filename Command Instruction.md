# 🤖 Rocks 2.0 - Command Instruction Manual

This manual lists all available commands for the Rocks 2.0 Discord Bot.

**Legend:**
* `[argument]` = Required argument.
* `(argument)` = Optional argument.

---

## 💰 Economy & Leveling
*Manage your wealth, check your rank, and transfer coins.*

| Command | Description |
| :--- | :--- |
| **/balance** | Check your current coin balance. |
| **/daily** | Claim your daily reward. (Resets every 20-24 hours). |
| **/streak** | View your current daily streak and luck multiplier. |
| **/luck** | Check how your streak affects your drop rates. |
| **/pay [user] [amount]** | Send coins to another user (Tax may apply based on rank). |
| **/profile (user)** | View a user's full profile (Balance, Level, Rank, etc.). |
| **/lvl** | Check your current Level and XP progress. |
| **/leaderboard** | View the top 10 players in the server. |
| **/droprates** | View your current multipliers for Coins and XP. |

---

## 🎮 Games
*Play games to win coins. All games require a bet.*

| Command | Description |
| :--- | :--- |
| **/crash [bet] [cashout]** | **(NEW)** Bet on a rising multiplier. The rocket can crash at any time! |
| **/trivia** | **(NEW)** Answer a random question. First correct answer wins coins (No bet required). |
| **/slots [bet]** | Spin the slot machine. Match 3 symbols to win big. |
| **/blackjack [bet]** | Play a hand of Blackjack against the dealer. Get closest to 21. |
| **/roulette [bet] [space]** | Bet on `red`, `black`, `even`, `odd`, or a specific number (0-36). |
| **/coinflip [bet] [side]** | Flip a coin. Choose `heads` or `tails`. (2x payout). |
| **/rps [bet] [choice]** | Play Rock, Paper, Scissors against the bot. |

---

## 🛒 Shop & Creator Marketplace
*Buy, sell, and manage digital items.*

| Command | Description | Rank Required |
| :--- | :--- | :--- |
| **/shop** | Open the interactive visual shop interface. | None |
| **/search [query]** | Search for a specific item by name. | None |
| **/upd** | Upload a new item to the shop. | **Creator Role** |
| **/bumpitem** | **(NEW)** Move one of your items to the top of "New Arrivals". | **Supreme Rank** |

---

## 🎙️ Voice Features (New)
*Manage automated voice interactions.*

| Command | Description | Permission |
| :--- | :--- | :--- |
| **/setwelcomevoice [file]** | Upload an MP3/WAV file. New members will receive this audio in their DMs. | **Admin** |
| **/setvcgreet [channel] [file]** | Upload an MP3/WAV file. The bot will join and play this sound when users enter the selected voice channel. | **Admin** |

---

## 🛡️ Admin & Configuration
*Server setup and management tools. Requires Administrator permissions.*

### ⚙️ Server Setup
| Command | Description |
| :--- | :--- |
| **/config setup** | Link the bot to your special channels (Shop, Logs, Welcome, etc.). |
| **/config view** | View the current channel and role configuration for this server. |
| **/config setwelcomegif [gif]** | Set the custom GIF used in welcome messages. |

### 👥 Role Management
| Command | Description |
| :--- | :--- |
| **/config addcreatorrole [role]** | Allow users with this role to use `/upd` to upload items. |
| **/config removecreatorrole [role]** | Revoke upload permissions from a role. |
| **/config setjoinrole [role]** | Set a role to be automatically given to new members. |
| **/config setrankrole elite/master/supreme** | Set the roles given at Level 50, 75, and 100. |
| **/adminrole add [role]** | specific role to have admin command access. |
| **/adminrole remove [role]** | Revoke admin command access from a role. |

### 🛠️ Maintenance & Moderation
| Command | Description |
| :--- | :--- |
| **/givecoins [user] [amount]** | Add coins to a user's balance. |
| **/removecoins [user] [amount]** | Remove coins from a user's balance. |
| **/removeitem [item_id]** | Forcefully delete an item from the shop. |
| **/featureitem [item_id]** | Pin an item to the "Featured" section of the shop. |
| **/resetlevels (user)** | Reset a specific user (or all users > Level 11) back to starter levels. |
| **/synccreators** | Give the Creator role to all existing users Level 25+. |
| **/syncranks** | Retroactively give Rank roles (Elite/Master/Supreme) to qualified users. |

---

## ℹ️ Misc
| Command | Description |
| :--- | :--- |
| **/help** | Open the interactive help menu to browse commands by category. |