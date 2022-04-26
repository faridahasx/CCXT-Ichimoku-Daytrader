"""
STRATEGY

ENTRY: If candle closes as green and ichimoku conversion line crosses above base line, wait and BUY at the close of second candle.

TAKE PROFIT: Sell at the first closing where profit is more than 0.01%

Time frame: 15 Minute

"""

import logging
import ccxt
import pandas as pd
import warnings
from config import *
from ta.trend import IchimokuIndicator
from datetime import datetime as dt

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, filename='bot.log', format='%(asctime)s:%(levelname)s:%(message)s', )

exchange = ccxt.ftx({
    'options': {
        'adjustForTimeDifference': True,
        'recvWindow': 50000,
    },
    'enableRateLimit': True,
    'apiKey': API_KEY,
    'secret': API_SECRET,
})
exchange.load_markets()

SYMBOL = 'BTCUSD'

in_position = False
ENTRY_PRICE = 0
USD_AMOUNT_TO_SPEND = 100
sellsize = 0
buy_quote_quantity = 0
def bot():
    global sellsize, in_position, buy_quote_quantity
    data = exchange.fetch_ohlcv(symbol=SYMBOL, timeframe='15m', limit=100)
    df = pd.DataFrame(data, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])

    ichimoku = IchimokuIndicator(high=df['High'], low=df['Low'], window1=9, window2=26, window3=52)
    ichimoku_base = ichimoku.ichimoku_base_line()
    ichimoku_conversion = ichimoku.ichimoku_conversion_line()
    df['ichimoku_base'] = ichimoku_base
    df['ichimoku_conversion'] = ichimoku_conversion

    if not in_position:
        if df['ichimoku_conversion'][len(df.index) - 1] > df['ichimoku_base'][len(df.index) - 1] \
                and df['ichimoku_conversion'][len(df.index) - 2] > df['ichimoku_base'][len(df.index) - 2] \
                and df['ichimoku_conversion'][len(df.index) - 3] < df['ichimoku_base'][len(df.index) - 3] \
                and df['Close'][len(df.index) - 2] > df['Open'][len(df.index) - 2]:
            # BUY
            try:
                buy_close = df['Close'][len(df.index) - 1]
                buysize = USD_AMOUNT_TO_SPEND / buy_close
                formatted_buy_amount = exchange.amount_to_precision(SYMBOL,buysize)
                order = exchange.create_market_buy_order(SYMBOL, formatted_buy_amount)
                in_position = True
                sellsize = float(order['info']['origQty'])
                buy_quote_quantity = float(order['info']['cummulativeQuoteQty'])
                logging.info(f'BUY ORDER FILLED')

            except Exception as e:
                logging.info(f'BUY ERROR: {e}')


    else:
        if (df['Close'][len(df.index) - 1] - ENTRY_PRICE) * 100 / ENTRY_PRICE > 0.01:
            # SELL
            formatted_sell_amount = exchange.amount_to_precision(SYMBOL, sellsize)
            try:
                order = exchange.create_market_sell_order(SYMBOL, formatted_sell_amount)
                in_position = False
                rtn = float(order['info']['cummulativeQuoteQty']) - buy_quote_quantity
                logging.info(f'SELL ORDER FILLED, Quote Return: {rtn}')

            except Exception as e:
                logging.info(f'SELL ERROR: {e}')


run = True

while True:
    # Run at every 15 minute
    if dt.now().minute % 15 == 0 and run:
        bot()
        run = False

    elif dt.now().minute % 15 != 0 and not run:
        run = True
