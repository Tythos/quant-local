"""
"""

import os
import numpy
import alpaca_trade_api as ata
from quant_local import keys

MOD_PATH, _ = os.path.split(os.path.abspath(__file__))
_, MOD_NAME = os.path.split(MOD_PATH)

BASE_URL = "https://paper-api.alpaca.markets"

def getSymbols(index="nasdaq100"):
    """
    """
    filePath = os.path.abspath(MOD_PATH + "/../definitions/indices/%s.txt" % index)
    if not os.path.isfile(filePath):
        raise Exception("Unable to locate index '%s'" % index)
    with open(filePath, 'r') as f:
        raw = f.read()
    return raw.strip().splitlines()

def symbolTensor(symbols):
    """Returns a numpy matrix giving time series (first dimension) across
       symbols (second dimension) for closing price.
    """
    I = 100
    J = len(symbols)
    keypair = keys.get("alpaca")
    api = ata.REST(key_id=keypair[1], secret_key=keypair[0], base_url=BASE_URL)
    market_data = api.get_barset(symbols, "day", limit=I)
    st = numpy.zeros((I, J))
    for i, s in enumerate(symbols):
        series = numpy.array([point.c for point in market_data[s]], dtype=numpy.float64)
        normalized = series / series[0]
        st[:,i] = normalized
    return st

def main():
    """
    from S&P500 index
    fit across models
    choose lowest-error model
    project out 5 trading sessions
    chose top 8 performers (quantified)
    """
    symbols = getSymbols()
    st = symbolTensor(symbols)

if __name__ == "__main__":
    main()
