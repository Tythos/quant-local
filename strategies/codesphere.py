"""
"""

import time
import numpy
import alpaca_trade_api as ata
from quant_local import keys

BASE_URL = "https://paper-api.alpaca.markets"

def buy(symbol, nShares):
    """
    """
    keypair = keys.get("alpaca")
    api = ata.REST(key_id=keypair[1], secret_key=keypair[0], base_url=BASE_URL)
    api.submit_order(symbol=symbol, qty=nShares, side="buy", type="market", time_in_force="gtc")

def sell(symbol, nShares):
    """
    """
    keypair = keys.get("alpaca")
    api = ata.REST(key_id=keypair[1], secret_key=keypair[0], base_url=BASE_URL)
    api.submit_order(symbol=symbol, qty=nShares, side="sell", type="market", time_in_force="gtc")

def trading():
    """
    """
    buy("SPY", 1)
    sell("SPY", 1)

def reading(symbol="SPY"):
    """
    """
    keypair = keys.get("alpaca")
    api = ata.REST(key_id=keypair[1], secret_key=keypair[0], base_url=BASE_URL)
    while True:
        print("")
        print("Checking price...")
        market_data = api.get_barset(symbol, "minute", limit=5)
        close_list = []
        for bar in market_data[symbol]:
            close_list.append(bar.c)
        close_list = numpy.array(close_list, dtype=numpy.float64)
        ma = numpy.mean(close_list)
        last_price = close_list[4]
        print("Moving average: %s" % str(ma))
        print("Last price: %s" % str(last_price))
        time.sleep(10)

def strategy(symbol="SPY"):
    """
    """
    pos_held = False
    keypair = keys.get("alpaca")
    api = ata.REST(key_id=keypair[1], secret_key=keypair[0], base_url=BASE_URL)
    while True:
        print("")
        print("Checking price...")
        market_data = api.get_barset(symbol, "minute", limit=5)
        close_list = []
        for bar in market_data[symbol]:
            close_list.append(bar.c)
        close_list = numpy.array(close_list, dtype=numpy.float64)
        ma = numpy.mean(close_list)
        last_price = close_list[4]
        print("Moving average: %s" % str(ma))
        print("Last price: %s" % str(last_price))
        if ma + 0.1 < last_price and not pos_held:
            # if moving average is more than 10 cents under price, and we haven't already bought
            print("Buying...")
            buy(symbol, 1)
            pos_held = True
        elif ma - 0.1 > last_price and pos_held:
            # if moving average is more than 10 cents above price, and we already bought
            print("Selling...")
            sell(symbol, 1)
            pos_held = False
        time.sleep(60)

def backtest(symbol="SPY"):
    """
    """
    pos_held = False
    keypair = keys.get("alpaca")
    api = ata.REST(key_id=keypair[1], secret_key=keypair[0], base_url=BASE_URL)
    hours_to_test = 2
    print("Checking price")
    market_data = api.get_barset(symbol, "minute", limit=(60 * hours_to_test))
    close_list = []
    for bar in market_data[symbol]:
        close_list.append(bar.c)
    print("Open: %s" % str(close_list[0]))
    print("Close: %s" % str(close_list[60 * hours_to_test - 1]))
    close_list = numpy.array(close_list, dtype=numpy.float64)
    startBal = 2000
    balance = startBal
    buys = 0
    sells = 0
    for i in range(4, 60 * hours_to_test):
        # start four minutes in, so that moving average can be calculated
        ma = numpy.mean(close_list[i-4:i+1])
        last_price = close_list[i]
        print("Moving average: %s" % str(ma))
        print("Last price: %s" % str(last_price))
        if ma + 0.1 < last_price and not pos_held:
            print("'Buying'...")
            balance -= last_price
            pos_held = True
            buys += 1
        elif ma - 0.1 > last_price and pos_held:
            print("'Selling'...")
            balance += last_price
            pos_held = False
            sells += 1
        print(balance)
        time.sleep(0.01)
    print("")
    print("Buys: %s" % str(buys))
    print("Sells: %s" % str(sells))
    if buys > sells:
        balance += close_list[60 * hours_to_test - 1]
    gain_pct = (balance - startBal) / startBal
    hours_in_session = 6.5 # NYSE: 9:30am to 4:00pm
    gain_rate = gain_pct * hours_in_session / hours_to_test
    print("Final balance: %s" % str(balance))
    print("Profit if held: %s" % str(close_list[60 * hours_to_test - 1] - close_list[0]))
    print("Profit from algorithm: %s" % str(balance - startBal))
    print("Gain rate: %f [%%/session]" % (100.0 * gain_rate))

def main():
    """
    """
    backtest()

if __name__ == "__main__":
    main()
