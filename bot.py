import os
import asyncio
from telethon import events, TelegramClient, Button
from telethon.sessions import StringSession
from telethon.tl.types import PhotoStrippedSize
from telethon.errors.rpcerrorlist import SessionPasswordNeededError

# ==============================================================================
# === CONFIGURATION: ADD YOUR ACCOUNTS HERE ===
# ==============================================================================
#
# Instructions:
# 1. Run the `generate_session.py` script to get a SESSION_STRING for each account.
# 2. Add a dictionary for each account to the `ACCOUNTS` list below.
# 3. For deployment, it's recommended to use environment variables instead of
#    hardcoding session strings directly in the script.
#
# Example using environment variables:
# 'SESSION_STRING': os.environ.get('SESSION_STRING_1'),
# 'CHAT_ID': int(os.environ.get('CHAT_ID_1', 0)),

ACCOUNTS = [
    {
        'NAME': 'Account 1',  # A friendly name for logging
        'API_ID': 28589254,    # API ID for Account 1
        'API_HASH': '1aff8819e75343aefd318078d1dd60f3',
        'CHAT_ID': -4790971666, # Target Group/Channel ID for Account 1
        'SESSION_STRING': '1BVtsOLMBu7VOU-xwIqTxkQblWmreO2OM7eClFJoJ9eVOyXxiwC9OdQ7NOmyuL0hMqA_f4s_-7HGIRpPZPUvtogf0Sw-vXGPXOJTF0CiWuGbuB4sCtVeipT5x1KTd2q856EYxOWFXY0G3YdfYVGk0qSYO29yZl_wFmhf1w8xPKYwp05KLB_8rDxyP7QsBU6I3fJ5R9JFOJ-AJgzz37l5a5l13N63sha_jEjjMHwb_lX57_dRHSxpQM-pD3zWbAmS8Jn_WH_420Y2Br9DBoGXU5xxsPJeaiqBWha4ZXcry19k_BhGRz8GXGyWN-BOkLudm3og5c_zVDTIU4U7RXmPH-URzaalm3bA=',
    },
    {
        'NAME': 'Account 2',
        'API_ID': 24433804,    # API ID for Account 2
        'API_HASH': 'e7f9cd7182550a68df68718efb4b2d12',
        'CHAT_ID': -1002100889006, # Target Group/Channel ID for Account 2
        'SESSION_STRING': '1BVtsOIIBuxEeBDtF9BhLtoZWbbrgpN6D1PTf4t_0Rj3r9sxqE3bvu8lEc64FMzPTC0xdTLV8zwXxAbS9ungt3nPNADJiiuWQbeU_YEtV0VkxspfeTlXqpigiNf-G8LZFl50mhiy1XvWL8PXSld6q1vLdn60C0up2aObfJQfTRD9qLpYlIvzpDpa2nlQUCnRLrh7BGvwn8pqZn_CE0r6g-ZVdQQBjFu_CcQGNDFqsK6Ig8Kch7J0u4ScLItiu3Vbsslinlq96NtjPzACNemopT34nOMHYgvl47ncSUSB153kL7pPVZNYDRFx0S7pnHD8vCI1zGLKSeZTCId9yiTZMcb0OVW1s_Ak=',
    },
    # Add more accounts here by copying the dictionary structure above
]

# Universal IDs
POKEBOT_ID = 572621020 # The user ID of the Pokebot

# ==============================================================================
# === HELPER CLASS ===
# ==============================================================================

class Counter:
    """A simple counter class."""
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1
        return self.count

# ==============================================================================
# === MAIN BOT CLASS ===
# ==============================================================================

class PokemonGuesserBot:
    """An independent instance of the Pokémon guessing bot for a single account."""

    def __init__(self, name, api_id, api_hash, session_string, chat_id):
        self.name = name
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_string = session_string
        self.chat_id = chat_id

        if not self.session_string or 'PASTE_SESSION' in self.session_string:
            raise ValueError(f"Session string for '{self.name}' is missing or not set.")

        self.client = TelegramClient(StringSession(self.session_string), self.api_id, self.api_hash)

        # === State & Counter for this instance ===
        self.is_running = False
        self.pause_flag = False
        self.guesser_counter = Counter()

        # === Inactivity Watchdog for this instance ===
        self.inactivity_timeout = 15  # seconds
        self.last_activity = None

        self._register_handlers()
        print(f"[{self.name}] Instance created for chat ID: {self.chat_id}")


    def _register_handlers(self):
        """Binds the class methods to Telethon events."""
        self.client.on(events.NewMessage(pattern=r"\.guess", outgoing=True))(self.start_guess)
        self.client.on(events.NewMessage(pattern=r"\.paus", outgoing=True))(self.pause_guess)
        self.client.on(events.NewMessage(pattern=r"\.bin", outgoing=True))(self.guesser_spam)
        self.client.on(events.NewMessage(from_users=POKEBOT_ID, pattern="Who's that pokemon?", chats=self.chat_id, incoming=True))(self.pokemon_guesser)
        self.client.on(events.NewMessage(from_users=POKEBOT_ID, pattern="The pokemon was ", chats=self.chat_id, incoming=True))(self.cache_updater)

    def _reset_inactivity(self):
        """Resets the inactivity timer for this instance."""
        if self.is_running and not self.pause_flag:
            self.last_activity = asyncio.get_event_loop().time()

    async def inactivity_watchdog(self):
        """Sends /guess if this bot instance has been idle for too long."""
        while True:
            await asyncio.sleep(1) # Check every second
            if self.is_running and not self.pause_flag and self.last_activity is not None:
                now = asyncio.get_event_loop().time()
                if (now - self.last_activity) > self.inactivity_timeout:
                    print(f"[{self.name}] Inactivity detected, sending /guess...")
                    try:
                        await self.client.send_message(entity=self.chat_id, message='/guess')
                    except Exception as e:
                        print(f"[{self.name}] Failed to send /guess due to inactivity: {e}")
                    self._reset_inactivity() # Reset timer after sending

    # === BOT HANDLERS ===

    async def start_guess(self, event):
        """Starts the guessing process for this instance."""
        self._reset_inactivity()
        self.is_running = True
        self.pause_flag = False
        await event.edit(f"✅ **[{self.name}] Guessing started.**")
        await self.client.send_message(entity=self.chat_id, message='/guess')

    async def pause_guess(self, event):
        """Pauses the guessing process for this instance."""
        self._reset_inactivity()
        self.pause_flag = True
        await event.edit(f"⏸️ **[{self.name}] Guessing paused.**")

    async def guesser_spam(self, event):
        """Spams /guess command every 5 minutes for this instance."""
        self._reset_inactivity()
        if not self.is_running:
            return
        # Send initial guess immediately
        await self.client.send_message(entity=self.chat_id, message='/guess')
        # Loop to send periodically
        while self.is_running:
            await asyncio.sleep(300) # 5 minutes
            if self.pause_flag or not self.is_running:
                break # Exit loop if paused or stopped
            await self.client.send_message(entity=self.chat_id, message='/guess')


    async def pokemon_guesser(self, event):
        """Identifies the pokemon from the image hash and sends the guess."""
        self._reset_inactivity()
        if not self.is_running or self.pause_flag:
            return

        for size in event.message.photo.sizes:
            if isinstance(size, PhotoStrippedSize):
                size_str = str(size)
                # Check shared cache for a match
                for file_name in os.listdir("cache/"):
                    if file_name.endswith(".txt"):
                        with open(os.path.join("cache", file_name), 'r') as f:
                            if f.read() == size_str:
                                count = self.guesser_counter.increment()
                                pokemon_name = file_name.split(".txt")[0]
                                print(f"[{self.name}] Match found! Guessing: {pokemon_name}. (Total for this account: {count})")
                                await self.client.send_message(self.chat_id, pokemon_name)
                                return # Exit after finding a match

                # If no match, save hash to temporary file to be learned
                with open(f"cache_{self.name}.tmp", 'w') as temp_cache_file:
                    temp_cache_file.write(size_str)
                print(f"[{self.name}] New Pokémon detected. Awaiting answer to learn...")
                break

    async def cache_updater(self, event):
        """Learns the name of the last unknown pokemon and saves it to the shared cache."""
        self._reset_inactivity()
        if not self.is_running:
            return

        pokemon_name = event.message.text.split("The pokemon was ")[1].split(".")[0]
        temp_file_path = f"cache_{self.name}.tmp"

        if os.path.exists(temp_file_path):
            with open(temp_file_path, 'r') as temp_file:
                hash_content = temp_file.read()

            # Save to the shared cache with the correct pokemon name
            with open(os.path.join("cache", f"{pokemon_name}.txt"), 'w') as file:
                file.write(hash_content)

            os.remove(temp_file_path) # Clean up the instance-specific temporary file
            print(f"[{self.name}] Learned and cached: {pokemon_name}")

        # Always trigger the next round after an answer
        await asyncio.sleep(2)
        if self.is_running and not self.pause_flag:
            await self.client.send_message(self.chat_id, "/guess")


    async def run(self):
        """Connects the client, starts the watchdog, and runs until disconnected."""
        try:
            await self.client.start()
            print(f"✅ [{self.name}] Client started successfully!")
            print(f"   - Use '.guess' to start and '.paus' to pause this account.")
            # Start the inactivity watchdog as a background task for this instance
            asyncio.create_task(self.inactivity_watchdog())
            await self.client.run_until_disconnected()
        except Exception as e:
            print(f"❌ [{self.name}] An error occurred: {e}")
        finally:
            print(f"🛑 [{self.name}] Client has been disconnected.")

# ==============================================================================
# === MAIN EXECUTION ===
# ==============================================================================
async def main():
    """Initializes and runs all configured bot accounts concurrently."""
    print("--- Multi-Account Pokémon Guesser Initializing ---")
    # Ensures the shared cache directory exists on startup
    os.makedirs("cache", exist_ok=True)

    tasks = []
    for config in ACCOUNTS:
        try:
            bot = PokemonGuesserBot(
                name=config['NAME'],
                api_id=config['API_ID'],
                api_hash=config['API_HASH'],
                session_string=config['SESSION_STRING'],
                chat_id=config['CHAT_ID']
            )
            tasks.append(bot.run())
        except ValueError as e:
            print(f"⚠️  Skipping account '{config.get('NAME', 'Unnamed')}' due to configuration error: {e}")
        except Exception as e:
            print(f"🚨 An unexpected error occurred while setting up '{config.get('NAME', 'Unnamed')}': {e}")


    if not tasks:
        print("\nNo valid accounts were configured to run. Please check the `ACCOUNTS` list. Exiting.")
        return

    print(f"\n🚀 Starting {len(tasks)} bot(s) concurrently...")
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down all bots.")
