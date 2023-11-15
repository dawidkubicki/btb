from dotenv import load_dotenv
import os
from bots.BullishSectorBot import BullishSectorBot

# Load env
load_dotenv()

class Bot:
    def __init__(self, symbols: list) -> None:
        self.bullish_sector_bot = BullishSectorBot(
            public_key=os.getenv("API_KEY_TESTNET"),
            secret_key=os.getenv("API_SECRET_TESTNET"),
            telegram_key=os.getenv("TELEGRAM_API_KEY"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            symbols=symbols,
            testnet=True,
            interval="4h",
            lookback=150
        )

    def run(self):
        self.bullish_sector_bot.run()
    
if __name__ == "__main__":
    # bot = Bot(symbols=["DARUSDT", "ILVUSDT", "MCUSDT", "PYRUSDT", "FLOKIUSDT"])
    bot = Bot(symbols=["DOTUSDT", "SOLUSDT", "AVAXUSDT"])
    bot.run()
