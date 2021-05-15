"""
"""

import os
import re
import csv
import math
import pprint
import warnings
import numpy
import quant_local

class Filter(object):
    """
    """

    def __init__(self, prop, comparator, value):
        """
        """
        self.property = prop
        self.comparator = comparator
        self.value = value
        self.numRelTol = 1e-3 # within 0.1%

    def isOkay(self, symbProps):
        """Returns True if the given symbol properties satisfy this filter.
           Specific comparison is based off of LHS (symbol property) format.
           Three comparison types are supported: string, numeric, and dollar.
           Dollar values are encoded as strings but begin with the "$"
           character and may be suffixed by a "k", "M", or "B" magnitude. These
           are cast to numeric values before a comparison is made.
        """
        try:
            lhs = symbProps[self.property]
            if type(lhs) is type("") and 0 < len(lhs) and lhs[0] == "$":
                lhs = quant_local.convertDollarString(lhs)
            if type(self.value) is type(0.0):
                lhs = float(lhs)
            if self.comparator == "<":
                return self.compareLT(lhs, self.value)
            elif self.comparator == "<=":
                return self.compareLE(lhs, self.value)
            elif self.comparator == "==":
                return self.compareEQ(lhs, self.value)
            elif self.comparator == "!=":
                return not self.compareEQ(lhs, self.value)
            elif self.comparator == ">=":
                return self.compareGE(lhs, self.value)
            elif self.comparator == ">":
                return self.compareGT(lhs, self.value)
            else:
                raise Exception("Invalid comparator '%s'" % self.comparator)
        except Exception as e:
            warnings.warn("\n".join([
                "Exception while evaluating:",
                "\tSecurity %s" % symbProps["Symbol"],
                "\tAgainst filter (%s,%s,%s)" % (self.property, self.comparator, str(self.value))
            ]))
            return False

    def compareLT(self, lhs, rhs):
        """For inequality this is asserted to be numeric-only lesser-than
        """
        assert(type(lhs) in [type(0), type(0.0)])
        assert(type(rhs) in [type(0), type(0.0)])
        return lhs < rhs

    def compareLE(self, lhs, rhs):
        """For inequality this is asserted to be numeric-only
           lesser-than-or-equal-to
        """
        assert(type(lhs) in [type(0), type(0.0)])
        assert(type(rhs) in [type(0), type(0.0)])
        return lhs <= rhs

    def compareEQ(self, lhs, rhs):
        """Switches specific comparison based on types; numeric is evaluated
           within relative tolerance (against RHS value specified in filter
           constructor), and string comparison is are case-insensitive. This
           interface is also used to define a NEQ (not equal) operation. We
           also now support/check-for bool-type comparisons, assuming they have
           both been cast to native 'bool' values upon deserialization.
        """
        assert(type(lhs) is type(rhs))
        if type(lhs) is type(True):
            return lhs == rhs
        elif type(lhs) in [type(0), type(0.0)]:
            return abs(rhs - lhs) / rhs < self.numRelTol
        elif type(lhs) is type(""):
            return lhs.lower() == rhs.lower()
        else:
            raise Exception("Invalid equality comparison for type %s" % type(lhs).__name__)

    def compareGE(self, lhs, rhs):
        """For inequality this is asserted to be numeric-only
           greater-than-or-equal-to
        """
        assert(type(lhs) in [type(0), type(0.0)])
        assert(type(rhs) in [type(0), type(0.0)])
        return lhs >= rhs

    def compareGT(self, lhs, rhs):
        """For inequality this is asserted to be numeric-only lesser-than
        """
        assert(type(lhs) in [type(0), type(0.0)])
        assert(type(rhs) in [type(0), type(0.0)])
        return lhs > rhs

def filterBuys(sectors, filtersBuy):
    """Returns dictionary mapping sector codes to lists of symbols that passed
       all buy filters.
    """
    allPassed = {}
    for sector in sectors:
        code = sector.getCode()
        secPassed = []
        symbols = sector.getSymbols()
        for symbol in symbols:
            security = sector.getSecurity(symbol)
            for ndx, fltr in enumerate(filtersBuy):
                if not fltr.isOkay(security):
                    break
                elif ndx == len(filtersBuy) - 1:
                    secPassed.append(symbol)
        if 0 < len(secPassed):
            allPassed[code] = secPassed
    return allPassed

def filterSells(positions, filtersSell):
    """Returns dictionary mapping sector codes to lists of symbols that passed
       all sell filters.
    """
    allPassed = {}
    for position in positions:
        if position["sector"] not in allPassed:
            allPassed[position["sector"]] = []
        for ndx, fltr in enumerate(filtersSell):
            if not fltr.isOkay(position):
                break
            elif ndx == len(filtersSell) - 1:
                allPassed[position["sector"]].append(position["symbol"])
    return allPassed

def getFiltersBuy():
    """Returns "buy" filter Objects as deserialized from the lone worksheet in
       the "datastore/filters_buy.xlsx" file.
    """
    datePaths = quant_local.getDatePaths()
    rows = quant_local.readXlsxDicts(datePaths[-1] + "/filters_buy.xlsx")
    filters = []
    for row in rows:
        filters.append(Filter(row["property"], row["comparator"], row["value"]))
    return filters

def getFiltersSell():
    """Returns "sell" filter Objects as deserialized from the lone worksheet in
       the "datastore/filters_sell.xlsx" file.
    """
    datePaths = quant_local.getDatePaths()
    rows = quant_local.readXlsxDicts(datePaths[-1] + "/filters_sell.xlsx")
    filters = []
    for row in rows:
        filters.append(Filter(row["property"], row["comparator"], row["value"]))
    return filters

def getMetrics(sector, symbols):
    """Returns a 2xN numpy.Array of metrics for the given symbols from the
       given sector.
    """
    metrics = [ # hard-coded for now, could easily be parameterized
        "Price Performance (52 Weeks)",
        "Standard Deviation (1 Yr Annualized)"
    ]
    table = numpy.zeros((2, len(symbols)))
    toDelete = [] # columns (symbols) to remove once populated
    for i, metric in enumerate(metrics):
        for j, symbol in enumerate(symbols):
            try:
                security = sector.getSecurity(symbol)
                table[i,j] = security[metric]
            except Exception as e:
                warnings.warn("Could not extract metric %s for symbol %s" % (metric, symbol))
                print(e)
                toDelete.append(j)
    for j in toDelete[::-1]:
        table = numpy.delete(table, j, 1)
    return table

def getFrontier(x, y):
    """Given x and y numpy.array objects (of matching 1d length), returns
       indices of a subset of points that constitute the frontier (in this
       case: max x, min y). Ordered in increasing y/x value.
    """
    order = numpy.argsort(x)[-1::-1]
    indices = [order[0]]
    y_ = y[indices[0]]
    for i in order[1:]:
        if y[i] < y_:
            indices.append(i)
            y_ = y[i]
    return indices[-1::-1]

def updatePositions(positions):
    """Adjusts the positions list and writes the results back out to the most
       recent positions.xlsx file. Latest price values are updated from the
       adjacent sector-specific spreadsheet.
    """
    # first cache map of symbols->sectors
    sectors = getSectors()
    ssMap = {}
    for sector in sectors:
        code = sector.getCode()
        symbols = sector.getSymbols()
        for symbol in symbols:
            ssMap[symbol] = code
    # now retrieve latest price
    for position in positions:
        symbol = position["symbol"]
        code = ssMap[symbol]
        sector = quant_local.getSectorByCode(sectors, code)
        security = sector.getSecurity(symbol)
        position["latest_price"] = "$%.2f" % security["Security Price"]
    pprint.pprint(positions)

def main():
    """
    """
    sectors = quant_local.getSectors()
    filtersBuy = getFiltersBuy()
    filtersSell = getFiltersSell()
    positions = quant_local.getPositions(sectors)
    allBuys = filterBuys(sectors, filtersBuy)
    allSells = filterSells(positions, filtersSell)
    recs = []
    for sector in sectors:
        code = sector.getCode()
        if code not in allBuys:
            continue
        buySymbols = allBuys[code]
        # filter buys by second-highest frontier in metric space
        xy = getMetrics(sector, buySymbols)
        frontier = getFrontier(xy[0,:], xy[1,:])
        ndx = None
        if 1 < len(frontier):
            ndx = frontier[-2]
            buySymbols = [buySymbols[ndx]]
        else:
            buySymbols = []
        # filter sells
        if code not in allSells:
            allSells[code] = []
        sellSymbols = allSells[code]
        # if a symbol appears in both buys and sells, mark as "HOLD" instead
        holdSymbols = list(set(buySymbols).intersection(set(sellSymbols)))
        ownedSymbols = [position["symbol"] for position in positions]
        print("Recommendations for sector %s:" % code)
        for symbol in buySymbols:
            if symbol not in holdSymbols and symbol not in ownedSymbols:
                print("\tBUY %s" % symbol)
        for symbol in holdSymbols:
            print("\tHOLD %s" % symbol)
        for symbol in sellSymbols:
            if symbol not in holdSymbols:
                print("\tSELL %s" % symbol)

if __name__ == "__main__":
    main()
