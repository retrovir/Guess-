import os
import asyncio
from telethon import events, TelegramClient, Button
from telethon.sessions import StringSession
from telethon.tl.types import PhotoStrippedSize

# === CONFIGURATION ===
# Try to get the session string from environment variables for deployment
# If not found, it will use the hardcoded string below.
SESSION_STRING = os.environ.get('SESSION_STRING', None)
API_ID = 24433804
API_HASH = 'e7f9cd7182550a68df68718efb4b2d12'
CHAT_ID = -1002100889006  # Your target chat ID

# Hardcoded session string if the environment variable isn't set
if not SESSION_STRING:
    SESSION_STRING = '1BVtsOIIBuxEeBDtF9BhLtoZWbbrgpN6D1PTf4t_0Rj3r9sxqE3bvu8lEc64FMzPTC0xdTLV8zwXxAbS9ungt3nPNADJiiuWQbeU_YEtV0VkxspfeTlXqpigiNf-G8LZFl50mhiy1XvWL8PXSld6q1vLdn60C0up2aObfJQfTRD9qLpYlIvzpDpa2nlQUCnRLrh7BGvwn8pqZn_CE0r6g-ZVdQQBjFu_CcQGNDFqsK6Ig8Kch7J0u4ScLItiu3Vbsslinlq96NtjPzACNemopT34nOMHYgvl47ncSUSB153kL7pPVZNYDRFx0S7pnHD8vCI1zGLKSeZTCId9yiTZMcb0OVW1s_Ak='

# Initialize the client
if SESSION_STRING:
    guessSolver = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    # This will create a 'temp.session' file for you to log in and get a string
    guessSolver = TelegramClient('temp', API_ID, API_HASH)

# === STATE & COUNTER ===
is_running = False
pause_flag = False

class Counter:
    # CORRECT: The constructor must be __init__
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1

guesser_counter = Counter()

# === INACTIVITY WATCHDOG ===
INACTIVITY_TIMEOUT = 15  # seconds
last_activity = None

def reset_inactivity():
    """Resets the inactivity timer."""
    global last_activity
    if is_running and not pause_flag:
        last_activity = asyncio.get_event_loop().time()

async def inactivity_watchdog():
    """Sends /guess if the bot has been idle for too long."""
    global last_activity
    while True:
        await asyncio.sleep(1) # Check every second
        if is_running and not pause_flag and last_activity is not None:
            now = asyncio.get_event_loop().time()
            if (now - last_activity) > INACTIVITY_TIMEOUT:
                print("Inactivity detected, sending /guess...")
                try:
                    await guessSolver.send_message(entity=CHAT_ID, message='/guess')
                except Exception as e:
                    print(f"Failed to send /guess due to inactivity: {e}")
                reset_inactivity() # Reset timer after sending

# === BOT HANDLERS ===

@guessSolver.on(events.NewMessage(pattern=r"\.guess", outgoing=True))
async def start_guess(event):
    """Starts the guessing process."""
    global is_running, pause_flag
    reset_inactivity()
    is_running = True
    pause_flag = False
    await event.edit("✅ **Guessing started.**")
    await guessSolver.send_message(entity=CHAT_ID, message='/guess')

@guessSolver.on(events.NewMessage(pattern=r"\.paus", outgoing=True))
async def pause_guess(event):
    """Pauses the guessing process."""
    global pause_flag
    reset_inactivity()
    pause_flag = True
    await event.edit("⏸️ **Guessing paused.**")

@guessSolver.on(events.NewMessage(from_users=1182033957, pattern=".bin", outgoing=True))
async def guesser_spam(event): # CORRECT: Renamed function
    """Spams /guess command every 5 minutes."""
    reset_inactivity()
    if not is_running:
        return
    await guessSolver.send_message(entity=CHAT_ID, message='/guess')
    for i in range(1, 3000):
        if pause_flag or not is_running:
            break
        await asyncio.sleep(300)
        if not pause_flag and is_running: # Check again after sleep
            await guessSolver.send_message(entity=CHAT_ID, message='/guess')

@guessSolver.on(events.NewMessage(from_users=572621020, pattern="Who's that pokemon?", chats=CHAT_ID, incoming=True))
async def pokemon_guesser(event): # CORRECT: Renamed function
    """Identifies the pokemon from the image hash and sends the guess."""
    reset_inactivity()
    if not is_running or pause_flag:
        return

    # Create cache directory if it doesn't exist
    os.makedirs("cache", exist_ok=True)

    for size in event.message.photo.sizes:
        if isinstance(size, PhotoStrippedSize):
            size_str = str(size)
            for file_name in os.listdir("cache/"):
                if file_name.endswith(".txt"):
                    with open(os.path.join("cache", file_name), 'r') as f:
                        file_content = f.read()
                    if file_content == size_str:
                        guesser_counter.increment()
                        pokemon_name = file_name.split(".txt")[0]
                        print(f"Match found! Guessing: {pokemon_name}. Total guesses: {guesser_counter.count}")
                        await guessSolver.send_message(CHAT_ID, pokemon_name)
                        # No need to send /guess here, the answer handler will do it
                        return # Exit after finding a match

            # If no match was found, save the new hash for learning
            with open("cache.txt", 'w') as temp_cache_file:
                temp_cache_file.write(size_str)
            print("New Pokemon detected. Awaiting answer to learn...")
            break

@guessSolver.on(events.NewMessage(from_users=572621020, pattern="The pokemon was ", chats=CHAT_ID))
async def cache_updater(event): # CORRECT: Renamed function
    """Learns the name of the last unknown pokemon and saves it to the cache."""
    reset_inactivity()
    if not is_running:
        return

    # CORRECT: Fixed the invalid .split("")[0]
    pokemon_name = event.message.text.split("The pokemon was ")[1].split(".")[0]

    # Check if we have a pending hash to learn
    if os.path.exists("cache.txt"):
        with open("cache.txt", 'r') as temp_file:
            hash_content = temp_file.read()
        
        # Save the hash with the correct pokemon name
        with open(os.path.join("cache", f"{pokemon_name}.txt"), 'w') as file:
            file.write(hash_content)
        
        os.remove("cache.txt") # Clean up the temporary file
        print(f"Learned and cached: {pokemon_name}")

    # Always trigger the next round
    await asyncio.sleep(2) # Small delay before next guess
    await guessSolver.send_message(CHAT_ID, "/guess")


# === MAIN EXECUTION ===
async def main():
    """Connects the client, starts the watchdog, and runs until disconnected."""
    print("Bot starting...")
    await guessSolver.start()
    print("Bot started successfully!")
    print("Use .guess to start and .paus to pause in your saved messages or any chat.")

    # Start the inactivity watchdog as a background task
    asyncio.create_task(inactivity_watchdog())

    await guessSolver.run_until_disconnected()

if __name__ == "__main__":
    # Ensures the cache directory exists on startup
    os.makedirs("cache", exist_ok=True)
    asyncio.run(main())
                 
