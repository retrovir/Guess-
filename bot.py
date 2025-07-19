from telethon import events, TelegramClient, Button
import os
import asyncio
from telethon.sessions import StringSession
from telethon.tl.types import PhotoStrippedSize

# === CONFIGURATION ===
api_id = 24433804
api_hash = 'e7f9cd7182550a68df68718efb4b2d12'
session_string = '1BVtsOIIBuxEeBDtF9BhLtoZWbbrgpN6D1PTf4t_0Rj3r9sxqE3bvu8lEc64FMzPTC0xdTLV8zwXxAbS9ungt3nPNADJiiuWQbeU_YEtV0VkxspfeTlXqpigiNf-G8LZFl50mhiy1XvWL8PXSld6q1vLdn60C0up2aObfJQfTRD9qLpYlIvzpDpa2nlQUCnRLrh7BGvwn8pqZn_CE0r6g-ZVdQQBjFu_CcQGNDFqsK6Ig8Kch7J0u4ScLItiu3Vbsslinlq96NtjPzACNemopT34nOMHYgvl47ncSUSB153kL7pPVZNYDRFx0S7pnHD8vCI1zGLKSeZTCId9yiTZMcb0OVW1s_Ak='
 os.environ.get('SESSION_STRING', None)  # You can set this as an env variable for deployment
chatid = -1002100889006 # change

# === INACTIVITY WATCHDOG ===
INACTIVITY_TIMEOUT = 15  # seconds
last_activity = None
watchdog_task = None

async def inactivity_watchdog():
    global last_activity
    while True:
        if last_activity is not None:
            now = asyncio.get_event_loop().time()
            if now - last_activity > INACTIVITY_TIMEOUT:
                try:
                    await guessSolver.send_message(entity=chatid, message='/guess')
                except Exception as e:
                    print("Failed to send /guess due to inactivity:", e)
                last_activity = now  # reset timer after sending
        await asyncio.sleep(1)

def reset_inactivity():
    global last_activity
    last_activity = asyncio.get_event_loop().time()

# Start the watchdog when bot starts
async def main():
    global watchdog_task
    await guessSolver.start()
    watchdog_task = asyncio.create_task(inactivity_watchdog())
    print("Bot started. Use .guess to start and .paus to pause.")
    await guessSolver.run_until_disconnected()

# === Modify all event handlers to call reset_inactivity() at the top ===

@guessSolver.on(events.NewMessage(pattern=r"\.guess", outgoing=True))
async def start_guess(event):
    reset_inactivity()
    # ... rest of your handler

@guessSolver.on(events.NewMessage(pattern=r"\.paus", outgoing=True))
async def pause_guess(event):
    reset_inactivity()
    # ... rest of your handler

@guessSolver.on(events.NewMessage(from_users=1182033957, pattern=".bin", outgoing=True))
async def guesser(event):
    reset_inactivity()
    # ... rest of your handler

@guessSolver.on(events.NewMessage(from_users=572621020, pattern="Who's that pokemon?", chats=chatid, incoming=True))
async def guesser(event):
    reset_inactivity()
    # ... rest of your handler

@guessSolver.on(events.NewMessage(from_users=572621020, pattern="The pokemon was ", chats=chatid))
async def guesser(event):
    reset_inactivity()
    # ... rest of your handler


if session_string:
    guessSolver = TelegramClient(StringSession(session_string), api_id, api_hash)
else:
    guessSolver = TelegramClient('temp', api_id, api_hash)


from telethon.tl.types import PhotoStrippedSize

# === STATE FLAGS ===
is_running = False
pause_flag = False

class Counter:
    def init(self):
        self.count = 0

    def increment(self):
        self.count += 1

guesserA_counter = Counter()

# === CONTROL HANDLERS ===

@guessSolver.on(events.NewMessage(pattern=r"\.guess", outgoing=True))
async def start_guess(event):
    global is_running, pause_flag
    is_running = True
    pause_flag = False
    await event.reply("Guessing started.")

@guessSolver.on(events.NewMessage(pattern=r"\.paus", outgoing=True))
async def pause_guess(event):
    global pause_flag
    pause_flag = True
    await event.reply("Guessing paused.")

# === AUTO GUESS SPAM ===

@guessSolver.on(events.NewMessage(from_users=1182033957, pattern=".bin", outgoing=True))
async def guesser(event):
    if not is_running:
        return
    await guessSolver.send_message(entity=chatid, message='/guess')
    for i in range(1, 3000):
        if pause_flag:
            break
        await asyncio.sleep(300)
        await guessSolver.send_message(entity=chatid, message='/guess')

# === POKEMON GUESS HANDLER ===

@guessSolver.on(events.NewMessage(from_users=572621020, pattern="Who's that pokemon?", chats=chatid, incoming=True))
async def guesser(event):
    if not is_running or pause_flag:
        return
    for size in event.message.photo.sizes:
        if isinstance(size, PhotoStrippedSize):
            size_str = str(size)
            for file in os.listdir("cache/"):
                with open(os.path.join("cache", file), 'r') as f:
                    file_content = f.read()
                if file_content == size_str:
                    guesserA_counter.increment()
                    chat = await event.get_chat()
                    print((guesserA_counter.count * 5))
                    await guessSolver.send_message(chat, file.split(".txt")[0])
                    await asyncio.sleep(8)
                    await guessSolver.send_message(chat, "/guess")
                    break
            with open("cache.txt", 'w') as file:
                file.write(size_str)

# === CACHE UPDATE HANDLER ===

@guessSolver.on(events.NewMessage(from_users=572621020, pattern="The pokemon was ", chats=chatid))
async def guesser(event):
    message = ((event.message.text).split("The pokemon was ")[1]).split("")[0]
    with open(os.path.join("cache", message + ".txt"), 'w') as file:
        with open("cache.txt", 'r') as inf:
            cont = inf.read()
            file.write(cont)
    os.remove("cache.txt")
    chat = await event.get_chat()
    await guessSolver.send_message(chat, "/guess")

# === MAIN LOOP ===

async def main():
    await guessSolver.start()
    print("Bot started. Use .guess to start and .paus to pause.")
    await guessSolver.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
