"""
"""

import sys
import numpy
import alpaca_trade_api as ata
from quant_local import keys

BASE_URL = "https://paper-api.alpaca.markets"
#SYMBOLS = [
#    "SLB",
#    "HAL",
#    "BKR",
#    "NOV",
#    "CHX",
#    "HP",
#    "LBRT",
#    "WHD",
#    "USAC",
#    "PTEN",
#    "OII",
#    "AROC",
#    "NESR"
#] # sector=energy; industry=equipment/services; hq=usa; cap>=$1b
SYMBOLS = [
    "TXG",
    "ME",
    "ABSI",
    "ADPT",
    "A",
    "AKYA",
    "TKNO",
    "AVTR",
    "BLI",
    "BIO",
    "TECH",
    "BNGO",
    "BRKR",
    "CSBR",
    "CRL",
    "CDXC",
    "DNAY",
    "CDXS",
    "CTKB",
    "FLDM",
    "HBIO",
    "ILMN",
    "NOTV",
    "IQV",
    "MRVI",
    "MEDP",
    "MTD",
    "MIRO",
    "NSTG",
    "NAUT",
    "NEO",
    "PACB",
    "PKI",
    "PSNL",
    "PPD",
    "QTRX",
    "QSI",
    "RPID",
    "RGEN",
    "SEER",
    "OMIC",
    "SHC",
    "SYNH",
    "TMO",
    "WAT"
] # sector=healthcare; industry=life sciences; hq=usa
SYMBOLS.sort()

def singleSymbol(symbol):
    """Evaluates a bollinger band strategy from Alpaca-driven historical data
       for the given symbol. Returns one of three given states: "SELL", "HOLD",
       and "BUY", depending where in the 10-session moving average the most
       recent closing (adjusted?) indicator is located.
    """
    keypair = keys.get("alpaca")
    api = ata.REST(key_id=keypair[1], secret_key=keypair[0], base_url=BASE_URL)
    market_data = api.get_barset([symbol], "day", limit=10)[symbol]
    close = numpy.array([point.c for point in market_data], dtype=numpy.float64)
    lower = numpy.median(close) - numpy.std(close)
    upper = numpy.median(close) + numpy.std(close)
    if close[-1] < lower:
        norm = (close[-1] - lower) / (upper - lower)
        return (symbol, "BUY", norm)
    elif upper < close[-1]:
        norm = (upper - close[-1]) / (upper - lower)
        return (symbol, "SELL", norm)
    else:
        return (symbol, "HOLD", 0)

def main():
    """Iterates over SYMBOLS to report strategy actions (non-holds)
    """
    actions = [singleSymbol(symbol) for symbol in SYMBOLS]
    ndcs = numpy.argsort([a[2] for a in actions])
    actions = [actions[i] for i in ndcs]
    for action in actions:
        if action[1] == "HOLD":
            continue
        print("%s: %s (%f)" % (action[0], action[1], action[2] * 100))

if __name__ == "__main__":
    main()
