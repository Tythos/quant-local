"""
"""

import os
import re
import csv
import math
import pprint
import warnings
import xlrd
import numpy
import openpyxl

MOD_PATH, _ = os.path.split(os.path.abspath(__file__))
DATASTORE_PATH = MOD_PATH + "/datastore"

def getDatePaths():
    """Returns list of absolute paths to date folders (8-digit names) in the
       datastore
    """
    candidates = []
    for folderName in os.listdir(DATASTORE_PATH):
        if re.match("^\d{8}$", folderName):
            candidates.append(os.path.abspath(DATASTORE_PATH + "/%s" % folderName))
    return candidates

def getSectorsTable():
    """Returns dictionary entries in the Sectors table
    """
    datePaths = getDatePaths()
    return readXlsxDicts(datePaths[-1] + "/sectors.xlsx")

def getSectorPaths(datePath):
    """Returns absolute paths to all available sector spreadsheets acquired on
       the given date
    """
    candidates = []
    sectors = getSectorsTable()
    pattern = "^(%s)\.xls$" % "|".join([sector["Code"] for sector in sectors])
    for fileName in os.listdir(datePath):
        if re.match(pattern, fileName):
            candidates.append(os.path.abspath(datePath + "/%s" % fileName))
    return candidates

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
                # convert to numerical dollar amount
                suffix = lhs[-1]
                if not re.match(r"^\d$", suffix):
                    lhs = lhs[1:-1]
                    mag = 0
                    if suffix == "k":
                        mag = 3
                    elif suffix == "M":
                        mag = 6
                    elif suffix == "B":
                        mag = 9
                    else:
                        raise Exception("Unsupported financial magnitude suffix '%s'" % suffix)
                    lhs = float(lhs) * math.pow(10, mag)
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

class Sector(object):
    """
    """

    def __init__(self, xlsPath):
        """
        """
        self.sectorPath = xlsPath
        self.wb = xlrd.open_workbook(xlsPath)

    def getCode(self):
        """
        """
        _, sectorFile = os.path.split(self.sectorPath)
        sectorCode, _ = os.path.splitext(sectorFile)
        return sectorCode

    def getSymbols(self):
        """Returns list of all symbols listed for this sector
        """
        sheet_names = self.wb.sheet_names()
        sheet_ndx = sheet_names.index("Search Criteria")
        ws = self.wb.sheet_by_index(sheet_ndx)
        header = ws.row_values(0)
        col_ndx = header.index("Symbol")
        symbols = []
        for row_ndx, row in enumerate(ws.col_values(col_ndx)):
            if len(row.strip()) == 0:
                break
            if row_ndx > 0:
                symbols.append(row)
        return symbols

    def getSecurity(self, symbol):
        """Aggregates all symbol properties across all worksheets
        """
        sheet_names = self.wb.sheet_names()
        properties = {}
        for sheet_name in sheet_names:
            sheet_ndx = sheet_names.index(sheet_name)
            ws = self.wb.sheet_by_index(sheet_ndx)
            header = ws.row_values(0)
            symbCol_ndx = header.index("Symbol")
            symbRow_ndx = ws.col_values(symbCol_ndx).index(symbol)
            values = ws.row_values(symbRow_ndx)
            assert(len(header) == len(values))
            for i in range(len(header)):
                properties[header[i]] = values[i]
        return properties

def getSectors():
    """
    """
    datePaths = getDatePaths()
    sectorPaths = getSectorPaths(datePaths[-1])
    return [Sector(sectorPath) for sectorPath in sectorPaths]

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

def readXlsDicts(xlsPath, sheetName=None):
    """Reads an .XLS file and returns a list of dictionaries corresponding to
       the continuous table in the given sheet (defaults to the first sheet if
       no name is specified).
    """
    wb = xlrd.open_workbook(xlsPath)
    sheet_names = wb.sheet_names()
    sheet_ndx = 0
    if sheetName is not None:
        sheet_ndx = sheet_names.index(sheetName)
    ws = wb.sheet_by_index(sheet_ndx)
    header = ws.row_values(0)
    rows = []
    for i in range(ws.nrows):
        rv = ws.row_values(i+1)
        if len("".join([str(v) for v in rv]).strip()) == 0:
            break
        assert(len(rv) == len(header))
        entry = {}
        for j, key in enumerate(header):
            entry[key] = rv[j]
        rows.append(entry)
    return rows

def readXlsxDicts(xlsxPath, sheetName=None):
    """Reads an .XLSX file and returns a list of dictionaries corresponding to
       the continuous table in the given sheet (defaults to the first sheet if
       no name is specified).
    """
    wb = openpyxl.open(xlsxPath)
    sheet_names = wb.sheetnames
    sheet_ndx = 0
    if sheetName is not None:
        sheet_ndx = sheet_names.index(sheetName)
    ws = wb.worksheets[sheet_ndx]
    header = []
    rows = []
    for i, row in enumerate(ws.rows):
        if i == 0:
            header = [cell.value for cell in row]
        else:
            rv = [cell.value for cell in row]
            if len("".join([str(v) for v in rv]).strip()) == 0:
                break
            assert(len(rv) == len(header))
            entry = {}
            for j, key in enumerate(header):
                entry[key] = rv[j]
            rows.append(entry)
    return rows

def getFiltersBuy():
    """Returns "buy" filter Objects as deserialized from the lone worksheet in
       the "datastore/filters_buy.xlsx" file.
    """
    datePaths = getDatePaths()
    rows = readXlsxDicts(datePaths[-1] + "/filters_buy.xlsx")
    filters = []
    for row in rows:
        filters.append(Filter(row["property"], row["comparator"], row["value"]))
    return filters

def getFiltersSell():
    """Returns "sell" filter Objects as deserialized from the lone worksheet in
       the "datastore/filters_sell.xlsx" file.
    """
    datePaths = getDatePaths()
    rows = readXlsxDicts(datePaths[-1] + "/filters_sell.xlsx")
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
    for i, metric in enumerate(metrics):
        for j, symbol in enumerate(symbols):
            security = sector.getSecurity(symbol)
            table[i,j] = security[metric]
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

def getPositions(sectors):
    """In addition to position information stored in positions.xlsx, augments
       with specific security information gleaned from that sector.
    """
    datePaths = getDatePaths()
    positions = readXlsxDicts(datePaths[-1] + "/positions.xlsx")
    codes = [sector.getCode() for sector in sectors]
    for position in positions:
        sector_ndx = codes.index(position["sector"])
        sector = sectors[sector_ndx]
        security = sector.getSecurity(position["symbol"])
        position.update(security)
    return positions

def getSectorByCode(sectors, code):
    """
    """
    for sector in sectors:
        if sector.getCode() == code:
            return sector
    raise Exception("Could not find sector matching code %s" % code)

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
        sector = getSectorByCode(sectors, code)
        security = sector.getSecurity(symbol)
        position["latest_price"] = "$%.2f" % security["Security Price"]
    pprint.pprint(positions)
    # finally, write back out to latest datastore .CSV file
    #datePaths = getDatePaths()
    #datePath = datePaths[-1]
    #_, date = os.path.split(datePath)
    #positionsPath = datePath + "/positions.csv"
    #fieldnames = list(positions[0].keys())
    #with open(positionsPath, 'w') as f:
    #    dw = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
    #    dw.writeheader()
    #    dw.writerows(positions)

def main():
    """
    """
    sectors = getSectors()
    filtersBuy = getFiltersBuy()
    filtersSell = getFiltersSell()
    positions = getPositions(sectors)
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
        ownedSymbols = [position["symbol"] for position in positions if position["is_open"]]
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
