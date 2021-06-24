"""Stages a new datastore snapshot by:
   #. Copying the most recent snapshot
   #. Removing the sector spreadsheets
   #. Opening a series of browser windows to stage the new snapshots
"""

import os
import shutil
import datetime
import webbrowser
import quant_local as ql

FIDELITY_SECTOR_URL = r"https://eresearch.fidelity.com/eresearch/markets_sectors/sectors/sectors_in_market.jhtml?tab=investments&sector=%u"

def getSnapshotPath(date):
    """
    """
    return ql.DATASTORE_PATH + "/%s" % date.strftime("%Y%m%d")
    
def getIsTodayExists():
    """Returns True if there already exists a snapshot for today
    """
    date = datetime.date.today()
    toPath = getSnapshotPath(date)
    return os.path.isdir(toPath)

def createNewSnapshot():
    """Copies the most recent snapshot to create a new one. Returns the
       datetime object used to determine today's date, for subsequent
       reference.
    """
    datePaths = ql.getDatePaths()
    fromPath = datePaths[-1]
    date = datetime.date.today()
    toPath = getSnapshotPath(date)
    shutil.copytree(fromPath, toPath)
    return date

def getSectorTable(date):
    """Returns the table listing sectors defined within the current snapshot
    """
    sectorPath = getSnapshotPath(date) + "/sectors.xlsx"
    return ql.readXlsxDicts(sectorPath)

def clearSnapshotSectors(date):
    """Removes sector-specific spreadsheets from the snapshot with the given
       date
    """
    sectorTable = getSectorTable(date)
    snapshotPath = getSnapshotPath(date)
    for sector in sectorTable:
        sectorPath = snapshotPath + "/%s.xls" % sector["Code"]
        if os.path.isfile(sectorPath):
            os.remove(sectorPath)

def openSectorTabs(date):
    """
    """
    sectorTable = getSectorTable(date)
    for sector in sectorTable:
        url = FIDELITY_SECTOR_URL % sector["ID"]
        webbrowser.open(url)

def renameXlsxSectors():
    """
    """
    date = datetime.date.today()
    sectorTable = getSectorTable(date)
    snapshotPath = getSnapshotPath(date)
    for filename in os.listdir(snapshotPath):
        if filename.endswith(".xls"):
            absPath = os.path.abspath(snapshotPath + "/%s" % filename)
            basics = ql.readXlsDicts(absPath, "Search Criteria")
            sectorName = basics[0]["Sector"]
            sectorCode = None
            for sector in sectorTable:
                if sector["Name"] == sectorName:
                    sectorCode = sector["Code"]
            if sectorCode is None:
                raise Exception("Unable to find matching sector for name '%s'" % sectorName)
            newPath = os.path.abspath(snapshotPath + "/%s.xls" % sectorCode)
            shutil.move(absPath, newPath)

def main():
    """
    """
    if not getIsTodayExists():
        # first pass: create snapshot, open tabs
        date = createNewSnapshot()
        clearSnapshotSectors(date)
        openSectorTabs(date)
    else:
        # second pass: rename spreadsheets by sector
        renameXlsxSectors()

if __name__ == "__main__":
    main()
