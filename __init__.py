"""
"""

import os
import re
import math
import pprint
import csv
import xlrd

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

def getSectors():
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
    sectors = getSectors()
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
        lhs = symbProps[self.property]
        if type(lhs) is type("") and lhs[0] == "$":
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
        self.wb = xlrd.open_workbook(xlsPath)

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

    def getSymbol(self, symbol):
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

def main():
    """
    """
    datePaths = getDatePaths()
    sectorPaths = getSectorPaths(datePaths[0])
    sector = Sector(sectorPaths[3])
    symbols = sector.getSymbols()
    symbol = sector.getSymbol(symbols[19])
    filters = [
        Filter("Company Headquarters Location", "==", "United States of America"),
        Filter("Equity Summary Score from StarMine from Refinitiv", "==", "Very Bullish"),
        Filter("Security Price", ">", 10.0),
        Filter("Security Price", "<", 100.0),
        Filter("Market Capitalization", ">=", 1e9)
    ]
    pprint.pprint(symbol)
    for ndx, fltr in enumerate(filters):
        print("Evaluating %s" % fltr.property)
        if not fltr.isOkay(symbol):
            print("Does not pass")
            break
        elif ndx == len(filters) - 1:
            print("It passed")

if __name__ == "__main__":
    main()
