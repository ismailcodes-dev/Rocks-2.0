import json
import sqlite3
import os

DB_PATH = "economy.db"
JSON_PATH = "channel_config.json"

def migrate():
    if not os.path.exists(JSON_PATH):
        print(f"❌ Could not find {JSON_PATH}. Are you sure it's in this folder?")
        return

    print(f"📖 Reading {JSON_PATH}...")
    try:
        with open(JSON_PATH, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read JSON: {e}")
        return

    print(f"🔄 Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER NOT NULL,
            setting_key TEXT NOT NULL,
            setting_value TEXT,
            PRIMARY KEY (guild_id, setting_key)
        )
    """)

    # --- DETECT FORMAT ---
    # Check if the file is "Flat" (Single Server) or "Nested" (Multi Server)
    is_flat_structure = False
    for key, value in data.items():
        if not isinstance(value, dict):
            is_flat_structure = True
            break
    
    count = 0
    
    if is_flat_structure:
        print("\n⚠️  Detected Single-Server Config Format.")
        print("ℹ️  Since the file doesn't have the Server ID inside it, you must provide it.")
        print("👉  To get your ID: Right-click your Server Icon -> 'Copy Server ID'.")
        print("    (If you don't see it, enable Developer Mode in Discord Settings > Advanced)\n")
        
        guild_input = input("⌨️  Paste your Server ID here: ").strip()
        
        if not guild_input.isdigit():
            print("❌ Invalid ID. It must be a number. Migration cancelled.")
            return
            
        guild_id = int(guild_input)
        
        print(f"   Processing settings for Guild ID: {guild_id}")
        for key, value in data.items():
            value_str = str(value)
            cursor.execute("""
                INSERT OR REPLACE INTO guild_settings (guild_id, setting_key, setting_value)
                VALUES (?, ?, ?)
            """, (guild_id, key, value_str))
            count += 1
            
    else:
        # Standard Multi-Server Format
        for guild_id, settings in data.items():
            print(f"   Processing Guild ID: {guild_id}")
            for key, value in settings.items():
                value_str = str(value) 
                cursor.execute("""
                    INSERT OR REPLACE INTO guild_settings (guild_id, setting_key, setting_value)
                    VALUES (?, ?, ?)
                """, (guild_id, key, value_str))
                count += 1
            
    conn.commit()
    conn.close()
    print(f"\n✅ Success! Moved {count} settings to the database.")
    print("You can now safely delete channel_config.json")

if __name__ == "__main__":
    migrate()