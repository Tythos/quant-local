"""
"""

import os
import re
import csv
import math
import pprint
import xlrd
import numpy

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
    sectorsPath = DATASTORE_PATH + "/sectors.csv"
    with open(sectorsPath, 'r') as f:
        dr = csv.DictReader(f)
        rows = [row for row in dr]
    return rows

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
           are cast to numeric values before a comparison is made. If an error
           occurs, the property is likely ill-formed and the filter is
           therefore rejected.
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
        except Exception:
            return False

    def compareLT(self, lhs, rhs):
        """For inequality this is asserted to be numeric-only lesser-than
        """
        assert(type(lhs) is type(0.0))
        assert(type(rhs) is type(0.0))
        return lhs < rhs

    def compareLE(self, lhs, rhs):
        """For inequality this is asserted to be numeric-only
           lesser-than-or-equal-to
        """
        assert(type(lhs) is type(0.0))
        assert(type(rhs) is type(0.0))
        return lhs <= rhs

    def compareEQ(self, lhs, rhs):
        """Switches specific comparison based on types; numeric is evaluated
           within relative tolerance (against RHS value specified in filter
           constructor), and string comparison is are case-insensitive.
        """
        assert(type(lhs) is type(rhs))
        if type(lhs) is type(0.0):
            return abs(rhs - lhs) / rhs < self.numRelTol
        elif type(lhs) is type(""):
            return lhs.lower() == rhs.lower()
        else:
            raise Exception("Invalid equality comparison for type %s" % type(lhs).__name__)

    def compareGE(self, lhs, rhs):
        """For inequality this is asserted to be numeric-only
           greater-than-or-equal-to
        """
        assert(type(lhs) is type(0.0))
        assert(type(rhs) is type(0.0))
        return lhs >= rhs

    def compareGT(self, lhs, rhs):
        """For inequality this is asserted to be numeric-only lesser-than
        """
        assert(type(lhs) is type(0.0))
        assert(type(rhs) is type(0.0))
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
    sectorPaths = getSectorPaths(datePaths[0])
    return [Sector(sectorPath) for sectorPath in sectorPaths]

def filterSymbols(sectors, filters):
    """
    """
    allPassed = {}
    for sector in sectors:
        code = sector.getCode()
        secPassed = []
        symbols = sector.getSymbols()
        for symbol in symbols:
            security = sector.getSecurity(symbol)
            for ndx, fltr in enumerate(filters):
                if not fltr.isOkay(security):
                    break
                elif ndx == len(filters) - 1:
                    secPassed.append(symbol)
        if 0 < len(secPassed):
            allPassed[code] = secPassed
    return allPassed

def getFilters():
    """
    """
    return [
        Filter("Company Headquarters Location", "==", "United States of America"),
        Filter("Equity Summary Score from StarMine from Refinitiv", "==", "Very Bullish"),
        Filter("Security Price", ">", 10.0),
        Filter("Security Price", "<", 100.0),
        Filter("Market Capitalization", ">=", 1e9),
        Filter("Price Performance (52 Weeks)", ">", 0.0)
    ]

def getMetrics(sector, symbols):
    """Returns a 2xn numpy.Array of metrics for the given symbols from the
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

def main():
    """
    """
    sectors = getSectors()
    filters = getFilters()
    allPassed = filterSymbols(sectors, filters)
    for sector in sectors:
        code = sector.getCode()
        if code not in allPassed:
            continue
        symbols = allPassed[code]
        xy = getMetrics(sector, symbols)
        frontier = getFrontier(xy[0,:], xy[1,:])
        if 1 < len(frontier):
            ndx = frontier[-2] # second-highest on frontier
            print("Recommended buy for sector %s: %s" % (sector.getCode(), symbols[ndx]))

if __name__ == "__main__":
    main()
