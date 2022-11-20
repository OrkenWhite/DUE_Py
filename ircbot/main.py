import asyncio
from bot_controller import Controller

def main():
    loop = asyncio.new_event_loop()
    close_future = loop.create_future()
    Controller(loop,close_future)
    loop.run_until_complete(close_future)

if __name__ == "__main__":
    main()