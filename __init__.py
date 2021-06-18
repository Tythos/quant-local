"""Base module for the quant_local Python package. Contains common models and
   utilities, like the Sector class and dollar string conversions. Specific
   strategies are under the "strategies" subpackage.
"""

import os
import re
import math
import openpyxl
import xlrd

PACK_PATH, _ = os.path.split(os.path.abspath(__file__))
DATASTORE_PATH = PACK_PATH + "/datastore"

def convertDollarString(ds):
    """Convert to numerical dollar amount. This can be a dollar string without
       magnitude suffix (e.g., "$100,000"), or a dollar string WITH a magnitude
       suffix (e.g., "$123k"). Supported suffixes include "k", "M", and "B".
    """
    suffix = ds[-1]
    assert ds[0] == "$"
    if re.match(r"^\d$", suffix):
        # last character is numeric, strip of commas and convert directly
        ds = re.sub(r",", "", ds)
        dv = float(ds[1:])
    else:
        # last character should be a suffix (and have no commas)
        ds = ds[1:-1]
        mag = 0
        if suffix == "k":
            mag = 3
        elif suffix == "M":
            mag = 6
        elif suffix == "B":
            mag = 9
        else:
            raise Exception("Unsupported financial magnitude suffix '%s'" % suffix)
        dv = float(ds) * math.pow(10, mag)
    return dv

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

def getSectors():
    """Returns a list of Sector objects as parsed from the most recent
       datastore snapshot.
    """
    datePaths = getDatePaths()
    sectorPaths = getSectorPaths(datePaths[-1])
    return [Sector(sectorPath) for sectorPath in sectorPaths]

def getSectorByCode(sectors, code):
    """Returns a specific Sector object as identified by the name/code (as
       returned by *Sector.getCode()*).
    """
    for sector in sectors:
        if sector.getCode() == code:
            return sector
    raise Exception("Could not find sector matching code %s" % code)

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

class Sector(object):
    """Models a specific sector of industry, as organized under the Fidelity
       dashboard categorization. Specific sector properties can be seen in the
       "sectors.xlsx" spreadsheet captured under a specific datastore snapshot.
    """

    def __init__(self, xlsPath):
        """Initializes a sector model from a given spreadsheet. (For example,
           the energy sector would be initialized from the *ENERGY.xlsx*
           spreadsheet.) Sector spreadsheets are organized under specific
           datastore snapshots.
        """
        self.sectorPath = xlsPath
        self.wb = xlrd.open_workbook(xlsPath)

    def getCode(self):
        """Returns the code for this sector. A "code" is the alphabetic
           shorthand/abbreviation for a specific sector, as identified by
           filename (and referenced by the Fidelity API / URL scheme). For
           example, "CONS_DISC" is "consumer (discretionary)".
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
