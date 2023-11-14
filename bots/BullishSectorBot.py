import ccxt
import urllib.parse
import requests
import json
import ta
import pandas as pd
import random
import time



class BullishSectorBot:
    def __init__(
            self,
            public_key: str,
            secret_key: str,
            telegram_key: str,
            telegram_chat_id: str,
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
        self.telegram_key = telegram_key
        self.chat_id = str(telegram_chat_id)
        self.initial_balance = self.binance_client.fetch_balance()['total']['USDT']
 

    def get_updates(self):
        url = f"https://api.telegram.org/bot{self.telegram_key}/getUpdates"
        return json.loads(requests.get(url).content)
    
    def send_message(self, message):
        encoded_message = urllib.parse.quote_plus(message)
        url = f"https://api.telegram.org/bot{self.telegram_key}/sendMessage?chat_id={self.chat_id}&parse_mode=Markdown&text={encoded_message}"
        return requests.get(url).status_code == 200

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

        indicator_bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)

        df['bb_bbm'] = indicator_bb.bollinger_mavg()
        df['bb_bbh'] = indicator_bb.bollinger_hband()
        df['bb_bbl'] = indicator_bb.bollinger_lband()
        df['ema'] = ta.trend.ema_indicator(df['Close'], window=24)
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

        # BB
        distance_to_upper = abs(latest_data['Close'] - latest_data['bb_bbh'])
        distance_to_lower = abs(latest_data['Close'] - latest_data['bb_bbl'])

        if distance_to_lower < distance_to_upper:
            score += 1

        # MA
        if latest_data['Close'] > latest_data['ema']:
            score += 1

        # EMA Crossover
        if latest_data['ema_short'] > latest_data['ema_long']:
            score += 1  # Adjust the points based on your criteria

        # RSI
        if 50 < latest_data['rsi'] < 70:
            score += 1  # Adjust the points based on your criteria

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
        print(f"Selected Symbol: {selected_symbol} with score {scores[selected_symbol]}")

        return selected_symbol
    
    def place_oco_order(self, symbol, quantity, take_profit_price, stop_loss_price, stop_loss_limit_percent) -> str:
        """
        Place an OCO order for stop loss and take profit.

        :param symbol: Trading symbol (e.g., 'BTCUSDT')
        :param quantity: Quantity of the asset to trade
        :param take_profit_price: Price at which to take profit
        :param stop_loss_price: Price at which to set the stop loss

        :return oco_order_id:str
        """
        try:
            stop_loss_limit_price = stop_loss_price * (1 - stop_loss_limit_percent)  # Adjust the offset as needed
            oco_order = self.binance_client.private_post_order_oco(
                symbol=symbol,
                side='sell',
                quantity=quantity,
                price=take_profit_price,
                stopPrice=stop_loss_price,
                stopLimitPrice=stop_loss_limit_price,
                stopLimitTimeInForce='GTC'
            )
            print(f"OCO order placed: {oco_order}")
            self.send_message(f"OCO order placed with TP: {take_profit_price}, and SL: {stop_loss_price}. Price of {symbol}: {self.binance_client.fetch_ticker(symbol)['last']}")
            oco_order_id = oco_order.get('orderListId', None)

            return oco_order_id
        except Exception as e:
            print(f"Error placing OCO order: {e}")
            # Further error handling as needed (e.g., retry, log, raise)

    def wait_for_oco_order_close(self, symbol, oco_order_id, check_interval=600):
        """
        Wait for an OCO order to close.

        :param symbol: The symbol for the OCO order
        :param oco_order_id: The ID of the OCO order
        :param check_interval: Interval in seconds to check the order status
        """
        while True:
            try:
                order_status = self.binance_client.fetch_order(symbol=symbol, id=oco_order_id)
                if order_status['status'] in ['closed', 'canceled', 'filled']:
                    print(f"OCO order {oco_order_id} closed.")
                    current_balance = self.binance_client.fetch_balance()['total']['USDT']
                    difference = round((float(current_balance)-float(self.initial_balance)), 2)
                    avg = (float(current_balance)-float(self.initial_balance))/2
                    pct = round(((difference/avg)*100), 2)
                    self.send_message(f"OCO order completed as {order_status['status']}. Initial balance: {self.initial_balance}, current {current_balance}. Pct Difference: {pct}%")
                    return order_status
                else:
                    print(f"OCO order {oco_order_id} is still open. Waiting...")
                time.sleep(check_interval)
            except Exception as e:
                print(f"Error checking order status: {e}")
                time.sleep(check_interval)  # Implement retry or backoff strategy as needed

    def close_all_orders(self, symbol):
        """
        Cancel all open orders for a specified symbol.

        :param symbol: Trading symbol (e.g., 'BTCUSDT')
        :return: A list of responses from the exchange for each order cancellation attempt
        """
        try:
            # Fetch all open orders for the specified symbol
            open_orders = self.binance_client.fetch_open_orders(symbol=symbol)
            print(f"Found {len(open_orders)} open orders for {symbol}.")

            # Attempt to cancel each open order
            cancellation_responses = []
            for order in open_orders:
                response = self.binance_client.cancel_order(id=order['id'], symbol=symbol)
                cancellation_responses.append(response)
                print(f"Canceled order {order['id']}.")

            return cancellation_responses

        except Exception as e:
            print(f"Error closing orders: {e}")
            # Further error handling as needed (e.g., retry, log, raise)
            return []

    def place_market_order_with_stop_loss_and_take_profit(self, symbol, max_balance_percent=10, stop_loss_percent=30, take_profit_percent=0.9):
        """
        Place a market order with stop loss and take profit.

        :param symbol: The symbol to trade (e.g., 'BTC/USDT')
        :param max_balance_percent: Maximum percentage of balance to use for the order
        :param stop_loss_percent: The stop loss percentage
        :param take_profit_percent: The take profit percentage
        :return: Order details if successful, None otherwise
        """

        try:
            # Close all orders
            # self.close_all_orders(symbol)

            # Fetch USDT balance
            balance = self.binance_client.fetch_balance()
            usdt_balance = balance['total']['USDT']

            # Use only a portion of the balance for this order
            order_balance = usdt_balance * (max_balance_percent / 100)

            # Fetch current market price for the symbol
            ticker = self.binance_client.fetch_ticker(symbol)
            current_price = ticker['last']

            # Calculate the quantity of the base asset to buy
            base_asset = symbol[:-4]  # Assuming all pairs end with 'USDT'
            quantity = (order_balance / current_price)
            quantity = float(self.binance_client.amount_to_precision(symbol, quantity))

            # Create a market buy order
            buy_order = self.binance_client.create_market_buy_order(f"{base_asset}/USDT", 1.5)
            self.send_message(f"Buy order of {quantity} {base_asset}. Balance before order: {usdt_balance} USDT, after order {order_balance} USDT.")

            # Additional logic to set stop loss and take profit

            # Check if the market order is filled and get the filled price
            filled_price = current_price
            
            # Calculate stop loss and take profit prices
            stop_loss_price = filled_price * (1 - stop_loss_percent / 100)
            take_profit_price = filled_price * (1 + take_profit_percent / 100)
            
            print(stop_loss_price, take_profit_price)

            # HERE TAKE PROFIT, STOP LOSS AND MONITORING
            oco_order_id = self.place_oco_order(f"{base_asset}/USDT", quantity, take_profit_price, stop_loss_price, stop_loss_limit_percent=0.25)
            
            # Wait for OCO order
            self.wait_for_oco_order_close(symbol, oco_order_id, check_interval=60)


        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        

    def run(self):
        while True:
            highest_score_symbol = self.get_highest_potential_token()
            if highest_score_symbol is not None:
                self.place_market_order_with_stop_loss_and_take_profit(highest_score_symbol)
            else:
                time.wait(60)
