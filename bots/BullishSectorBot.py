import ccxt
import ta
import pandas as pd
import random
import time


class BullishSectorBot:
    def __init__(
            self,
            public_key: str,
            secret_key: str,
            testnet: bool,
            symbols: list,
            interval: str,
            lookback: int,
        ) -> None:
        self.binance_client = ccxt.binance({
            'apiKey': public_key,   
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            }
        })
        if testnet:
            self.binance_client.set_sandbox_mode(True)
        self.symbols = symbols
        self.interval = interval
        self.lookback = lookback

    def fetch_historical_data_binance(self, symbol, interval, lookback):
            """
            Fetch historical candlestick data for a given symbol and interval.

            :param symbol: String, symbol pair to fetch data for (e.g., 'BTC/USDT')
            :param interval: String, timeframe interval (e.g., '1d' for one day)
            :param lookback: Integer, number of data points to fetch
            :return: DataFrame, containing the historical candlestick data
            """
            if interval == "1m" or "5min" or "15min":
                 limit = 500
            elif interval == "1h" or "4h":
                 limit = 134
            else:
                 limit = 12

            all_candles = []

            while lookback > 0:
                fetch_limit = min(lookback, limit)
                candles = self.binance_client.fetch_ohlcv(symbol, timeframe=interval, limit=fetch_limit)
                if not candles:
                    break
                all_candles = candles + all_candles
                lookback -= fetch_limit
                # Adjusting the since parameter to fetch earlier data
                since = candles[0][0] - self.binance_client.parse_timeframe(interval) * fetch_limit * 1000
                self.binance_client.options['params'] = {'startTime': since}

            # Convert to DataFrame
            columns = ['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
            df = pd.DataFrame(all_candles, columns=columns)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')

            return df

    def get_balance(self):
        non_zero_balances = []
        balances = self.binance_client.fetch_balance()
        for currency, amount in balances['total'].items():
            if amount > 0:
                non_zero_balances.append({currency: round(amount, 6)})
        return non_zero_balances
    
    def calculate_indicators(self, symbol, interval, lookback):
        df = self.fetch_historical_data_binance(symbol, interval, lookback)

        df['ema_short'] = ta.trend.ema_indicator(df['Close'], window=10)
        df['ema_long'] = ta.trend.ema_indicator(df['Close'], window=50)
        df['rsi'] = ta.momentum.rsi(df['Close'])
        macd = ta.trend.MACD(df['Close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()

        df = df.dropna()
        df = df.reset_index()

        return df
    
    def calculate_score(self, data):
        score = 0

        # Ensure data is not empty
        if data.empty:
            return score

        # Get the latest data point
        latest_data = data.iloc[-1]

        # EMA Crossover
        if latest_data['ema_short'] > latest_data['ema_long']:
            score += 1  # Adjust the points based on your criteria

        # RSI
        if 50 < latest_data['rsi'] < 70:
            score += 2  # Adjust the points based on your criteria

        # MACD
        if latest_data['macd'] > latest_data['macd_signal']:
            score += 1  # Adjust the points based on your criteria

        return score
    
    def get_highest_potential_token(self):
        ta_df = []
        scores = {}
        for symbol in self.symbols:
            df = self.calculate_indicators(symbol, self.interval, self.lookback)
            ta_df.append({symbol: df})
            scores[symbol] = self.calculate_score(df)

        # Find the maximum score
        max_score = max(scores.values())

        # Check if all scores are zero
        if max_score == 0:
            print("No suitable symbols found. All scores are zero.")
            return None

        # Filter symbols with the maximum score
        top_symbols = [symbol for symbol, score in scores.items() if score == max_score]

        # Randomly select one symbol from those with the highest score
        selected_symbol = random.choice(top_symbols) if top_symbols else None

        # Print or return the selected symbol
        print(f"Selected Symbol: {selected_symbol}")

        return selected_symbol
    
    def wait_for_oco_order_close(self, symbol, oco_order_id, check_interval=60):
        """
        Wait for an OCO order to close.

        :param symbol: The symbol for the OCO order
        :param oco_order_id: The ID of the OCO order
        :param check_interval: Interval in seconds to check the order status
        """
        while True:
            try:
                # Fetch the current status of the OCO order
                order_status = self.binance_client.fetch_order(symbol=symbol, id=oco_order_id)

                # Check if the order is closed
                if order_status['status'] in ['closed', 'canceled', 'filled']:
                    print(f"OCO order {oco_order_id} closed.")
                    return order_status
                else:
                    print(f"OCO order {oco_order_id} is still open. Waiting...")

                # Wait for the specified check interval before checking again
                time.sleep(check_interval)

            except Exception as e:
                print(f"Error checking order status: {e}")
                # Handle the error as appropriate (e.g., retry, log, raise)
                time.sleep(check_interval)

    def place_market_order_with_stop_loss_and_take_profit(self, symbol, stop_loss_percent=30, take_profit_percent=0.9):
        """
        Place a market order with stop loss and take profit.

        :param symbol: The symbol to trade (e.g., 'BTC/USDT')
        :param quantity: The quantity of the symbol to trade
        :param stop_loss_percent: The stop loss percentage
        :param take_profit_percent: The take profit percentage
        :return: Order details if successful, None otherwise
        """

        try:
            # Fetch USDT balance
            balance = self.binance_client.fetch_balance()
            usdt_balance = balance['total']['USDT']

            # Fetch current market price for the symbol
            ticker = self.binance_client.fetch_ticker(symbol)
            current_price = ticker['last']

            
            # Calculate the quantity of the base asset to buy
            base_asset = symbol[:-4]  # Assuming all pairs end with 'USDT'
            market = self.binance_client.market(symbol)
            quantity = usdt_balance / current_price
            quantity = self.binance_client.amount_to_precision(symbol, quantity)

            market_order = self.binance_client.create_market_buy_order(symbol, quantity)
            print(f"Market order placed: {market_order}")

        except Exception as e:
            print(f"An error occurred: {e}")

            return None
        
        # Check if the market order is filled and get the filled price
        filled_price = market_order['price']  # Adjust based on how Binance returns the filled price

        # Calculate stop loss and take profit prices
        stop_loss_price = filled_price * (1 - stop_loss_percent / 100)
        take_profit_price = filled_price * (1 + take_profit_percent / 100)

        # Place an OCO order for stop loss and take profit
        oco_order = self.binance_client.private_post_order_oco(
            symbol=symbol,
            side='sell',
            quantity=quantity,
            price=take_profit_price,
            stopPrice=stop_loss_price,
            stopLimitPrice=stop_loss_price * (1 - 25 / 100),  # Adjust the offset as needed
            stopLimitTimeInForce='GTC'
        )
        print(f"OCO order placed: {oco_order}")

        oco_order_status = self.wait_for_oco_order_close(symbol, oco_order['id'])

        # Return the order details
        return market_order, oco_order
    
    def run(self):
        while True:
            highest_score_symbol = self.get_highest_potential_token()
            if highest_score_symbol is not None:
                order = self.place_market_order_with_stop_loss_and_take_profit(highest_score_symbol)
            else:
                time.wait(60)
