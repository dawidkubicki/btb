from bots.BullishSectorBot import BullishSectorBot


class Bot:
    def __init__(self, symbols: list) -> None:
        self.bullish_sector_bot = BullishSectorBot(
            public_key="",
            secret_key="",
            # public_key="",
            # secret_key="",
            symbols=symbols,
            testnet=True,
            interval="4h",
            lookback=150
        )

    def run(self):
        self.bullish_sector_bot.run()
    
if __name__ == "__main__":
    bot = Bot(symbols=["BTCUSDT", "ILVUSDT"])
    balances = bot.bullish_sector_bot.get_balance()
    for item in balances:
        if item.get('USDT') != None:
            print(item['USDT'])
