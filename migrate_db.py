import sqlite3
import os

def migrate_economy():
    db_path = "economy.db"
    
    if not os.path.exists(db_path):
        print(f"⚠️ {db_path} not found. Skipping.")
        return

    print(f"🔄 Migrating {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Add 'stream_start_timestamp' to users table (New in Rocks 2.0)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN stream_start_timestamp REAL DEFAULT 0")
            print("   ✅ Added column: stream_start_timestamp")
        except sqlite3.OperationalError:
            print("   ℹ️ Column 'stream_start_timestamp' already exists.")

        # 2. Add 'last_bump_timestamp' to users table (In case it's missing)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN last_bump_timestamp REAL DEFAULT 0")
            print("   ✅ Added column: last_bump_timestamp")
        except sqlite3.OperationalError:
            print("   ℹ️ Column 'last_bump_timestamp' already exists.")

        # 3. Create 'guild_settings' table (Replaces channel_config.json)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT,
                PRIMARY KEY (guild_id, setting_key)
            )
        """)
        print("   ✅ Verified table: guild_settings")

        conn.commit()
        conn.close()
        print(f"✅ {db_path} migration complete!\n")
    except Exception as e:
        print(f"❌ Error migrating {db_path}: {e}\n")

def migrate_shop():
    db_path = "shop.db"
    
    if not os.path.exists(db_path):
        print(f"⚠️ {db_path} not found. Skipping.")
        return

    print(f"🔄 Migrating {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Add missing columns to items table
        new_columns = [
            ("purchase_count", "INTEGER DEFAULT 0"),
            ("upload_timestamp", "REAL DEFAULT 0"),
            ("is_featured", "INTEGER DEFAULT 0")
        ]

        for col_name, col_type in new_columns:
            try:
                cursor.execute(f"ALTER TABLE items ADD COLUMN {col_name} {col_type}")
                print(f"   ✅ Added column: {col_name}")
            except sqlite3.OperationalError:
                print(f"   ℹ️ Column '{col_name}' already exists.")

        conn.commit()
        conn.close()
        print(f"✅ {db_path} migration complete!\n")
    except Exception as e:
        print(f"❌ Error migrating {db_path}: {e}\n")

if __name__ == "__main__":
    print("--- STARTING DATABASE MIGRATION ---\n")
    migrate_economy()
    migrate_shop()
    print("--- MIGRATION FINISHED ---")
    print("You can now delete this script and start your bot normally.")