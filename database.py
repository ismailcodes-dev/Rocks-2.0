# database.py
import aiosqlite
import time
import os
from discord.ext import commands

class DatabaseManager:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.economy_db_path = "economy.db"
        self.shop_db_path = "shop.db"
        # We will initialize tables in an async setup method

    async def init_db(self):
        """Initializes the database tables asynchronously."""
        async with aiosqlite.connect(self.economy_db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            
            # --- USERS TABLE ---
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER NOT NULL, guild_id INTEGER NOT NULL,
                    balance INTEGER DEFAULT 0, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
                    last_daily TEXT, daily_streak INTEGER DEFAULT 0,
                    last_coin_claim REAL DEFAULT 0, last_xp_claim REAL DEFAULT 0,
                    daily_spam_count INTEGER DEFAULT 0,
                    daily_stream_coins INTEGER DEFAULT 0,
                    last_bump_timestamp REAL DEFAULT 0,
                    stream_start_timestamp REAL DEFAULT 0, 
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            
            # --- GUILD SETTINGS TABLE (Replaces channel_config.json) ---
            # We store settings as key-value pairs per guild for flexibility
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER NOT NULL,
                    setting_key TEXT NOT NULL,
                    setting_value TEXT,
                    PRIMARY KEY (guild_id, setting_key)
                )
            """)
            await db.commit()
            print(f"✅ Economy DB initialized at {self.economy_db_path}")

        async with aiosqlite.connect(self.shop_db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT, creator_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL, item_name TEXT NOT NULL, application TEXT NOT NULL,
                    category TEXT NOT NULL, price INTEGER NOT NULL, product_link TEXT NOT NULL,
                    screenshot_link TEXT, screenshot_link_2 TEXT, screenshot_link_3 TEXT,
                    purchase_count INTEGER DEFAULT 0,
                    upload_timestamp REAL DEFAULT 0,
                    is_featured INTEGER DEFAULT 0
                )
            """)
            await db.commit()
            print(f"✅ Shop DB initialized at {self.shop_db_path}")

    # --- SETTINGS MANAGEMENT (Replacing JSON) ---
    async def get_guild_setting(self, guild_id: int, key: str, default=None):
        async with aiosqlite.connect(self.economy_db_path) as db:
            cursor = await db.execute("SELECT setting_value FROM guild_settings WHERE guild_id = ? AND setting_key = ?", (guild_id, key))
            row = await cursor.fetchone()
            if row:
                # Attempt to cast to int if it looks like an ID
                val = row[0]
                if val.isdigit(): return int(val)
                return val
            return default

    async def set_guild_setting(self, guild_id: int, key: str, value):
        async with aiosqlite.connect(self.economy_db_path) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, setting_key, setting_value) 
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, setting_key) DO UPDATE SET setting_value = excluded.setting_value
            """, (guild_id, key, str(value)))
            await db.commit()

    # --- USER DATA ---
    async def get_user_data(self, user_id: int, guild_id: int):
        async with aiosqlite.connect(self.economy_db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
            row = await cursor.fetchone()
            if not row:
                await db.execute("INSERT INTO users (user_id, guild_id) VALUES (?, ?)", (user_id, guild_id))
                await db.commit()
                cursor = await db.execute("SELECT * FROM users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
                row = await cursor.fetchone()
            return dict(row)

    async def update_user_data(self, user_id: int, guild_id: int, data: dict):
        if not data: return
        set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
        values = list(data.values()) + [user_id, guild_id]
        async with aiosqlite.connect(self.economy_db_path) as db:
            await db.execute(f"UPDATE users SET {set_clause} WHERE user_id = ? AND guild_id = ?", values)
            await db.commit()

    async def delete_user_data(self, user_id: int, guild_id: int):
        async with aiosqlite.connect(self.economy_db_path) as db:
            await db.execute("DELETE FROM users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
            await db.commit()

    async def get_leaderboard(self, guild_id: int, limit: int = 10):
        async with aiosqlite.connect(self.economy_db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT user_id, level, xp, balance FROM users WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT ?", (guild_id, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
            
    async def get_all_users_in_guild(self, guild_id: int):
        async with aiosqlite.connect(self.economy_db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE guild_id = ?", (guild_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # --- SHOP ITEMS ---
    async def add_item_to_shop(self, creator_id, guild_id, item_name, application, category, price, product_link, screenshot_link, screenshot_link_2, screenshot_link_3):
        async with aiosqlite.connect(self.shop_db_path) as db:
            await db.execute(
                "INSERT INTO items (creator_id, guild_id, item_name, application, category, price, product_link, screenshot_link, screenshot_link_2, screenshot_link_3, upload_timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (creator_id, guild_id, item_name, application, category, price, product_link, screenshot_link, screenshot_link_2, screenshot_link_3, time.time())
            )
            await db.commit()

    async def get_item_details(self, item_id, guild_id):
        async with aiosqlite.connect(self.shop_db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM items WHERE item_id = ? AND guild_id = ?", (item_id, guild_id))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def delete_item(self, item_id, guild_id):
        async with aiosqlite.connect(self.shop_db_path) as db:
            await db.execute("DELETE FROM items WHERE item_id = ? AND guild_id = ?", (item_id, guild_id))
            await db.commit()

    async def get_new_arrivals(self, guild_id, limit=5):
        async with aiosqlite.connect(self.shop_db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM items WHERE guild_id = ? ORDER BY upload_timestamp DESC"
            params = [guild_id]
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            cursor = await db.execute(query, tuple(params))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_all_items(self, guild_id):
        async with aiosqlite.connect(self.shop_db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM items WHERE guild_id = ? ORDER BY item_name ASC", (guild_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_items_by_creator(self, creator_id: int, guild_id: int):
        async with aiosqlite.connect(self.shop_db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM items WHERE creator_id = ? AND guild_id = ? ORDER BY upload_timestamp DESC", (creator_id, guild_id))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def bump_item(self, item_id: int):
        async with aiosqlite.connect(self.shop_db_path) as db:
            await db.execute("UPDATE items SET upload_timestamp = ? WHERE item_id = ?", (time.time(), item_id))
            await db.commit()

    async def get_featured_item(self, guild_id):
        async with aiosqlite.connect(self.shop_db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM items WHERE guild_id = ? AND is_featured = 1 LIMIT 1", (guild_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def set_featured_item(self, item_id, guild_id):
        async with aiosqlite.connect(self.shop_db_path) as db:
            await db.execute("UPDATE items SET is_featured = 0 WHERE guild_id = ?", (guild_id,))
            await db.execute("UPDATE items SET is_featured = 1 WHERE item_id = ? AND guild_id = ?", (item_id, guild_id))
            await db.commit()

    async def search_items(self, guild_id, query):
        async with aiosqlite.connect(self.shop_db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT item_id, item_name, price FROM items WHERE guild_id = ? AND item_name LIKE ?", (guild_id, f'%{query}%'))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
            
    async def increment_purchase_count(self, item_id: int, guild_id: int):
        async with aiosqlite.connect(self.shop_db_path) as db:
            await db.execute("UPDATE items SET purchase_count = purchase_count + 1 WHERE item_id = ? AND guild_id = ?", (item_id, guild_id))
            await db.commit()