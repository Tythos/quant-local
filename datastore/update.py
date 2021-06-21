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

def main():
    """
    """
    date = createNewSnapshot()
    clearSnapshotSectors(date)
    openSectorTabs(date)

if __name__ == "__main__":
    main()
