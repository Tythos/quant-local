"""Survey U.S. energy companies, by market cap:
   * Who is the current ceo, coo, and cfo?
   * Where did they work in the past?
   * Fit security price (with lag?) to participation
   * Resolve "winners" (employment leads to positive growth)
   * Resolve "losers" (employment leads to positive growth)
   * Purchase securities with "winners" employed
   * Purchase put options with "losers" employed
"""

import re
import json
import numpy
import requests
import bs4
import quant_local

#NAME_PREFIXES = ["Mr.", "Ms.", "Mrs.", "Dr."]
#NAME_SUFFIXES = ["Ph.D.", "Jr.", "Sr."]
BLOOMBERG_SEARCH_URL = r"https://search.bloomberg.com/lookup.json?types=Person&exclude_subtypes=label:editorial&group_size=1&fields=url&query=%s%s%s"

def getSecuritiesByMarketCap(sector):
    """
    """
    symbols = sector.getSymbols()
    securities = [sector.getSecurity(symbol) for symbol in symbols]
    markCaps = [quant_local.convertDollarString(security["Market Capitalization"]) for security in securities]
    indices = numpy.argsort(markCaps)[::-1]
    return [securities[i] for i in indices]

def filterByTitle(person, titles):
    """Returns True if the given dictionary of person attributes includes a
       "Title" field in which one of the given title abbreviations exists
       (False otherwise). This could appear in several different forms:
       * "CEO" could appear part of a larger title like "CEO & Director"
       * "CFO" could appear as an abbreviation of sequential terms, like "Chief Financial Officer"

       It may be necessary/desirable to return the SPECIFIC title (or index
       thereof) that is successfully matched. For the time being, however, we
       only focus on whether the match is found.
    """
    firsts = "".join([w[0] for w in person["Title"].split()])
    for title in titles:
        if re.search(title, person["Title"]):
            return True
        if re.search(title, firsts):
            return True
    return False

def addNameIdentifiers(officer):
    """Given the "name" field of a chief officer, returns a (hopefully) unique
       identifier consisting of:
       * Best-guess last name
       * Best-guess first name
       * Date of birth (YYYY)

       ...concatenated by underscore ("_"). This identifier will be used to
       search and compile a dossier on that particular individual. First and
       last names are chosen after the name parts have been split and any parts
       ending in a period ("Mr.", "Dr.", "Jr.", "PhD.", etc.).
    """
    parts = officer["Name"].split()
    n = len(parts)
    for i in range(n-1, -1, -1):
        if parts[i].endswith("."):
            parts.pop(i)
    officer["Identifier"] = "%s_%s_%u" % (parts[-1].lower(), parts[0].lower(), int(officer["Year Born"]))
    officer["First"] = parts[0]
    officer["Last"] = parts[-1]

def getSecurityCSuite(security, titles=["CEO", "COO", "CFO"]):
    """This could probably go in the "scrapefe" package
    """
    res = requests.get("https://finance.yahoo.com/quote/%s/profile?p=%s" % (security["Symbol"], security["Symbol"]))
    assert res.status_code == 200
    soup = bs4.BeautifulSoup(res.content, features="lxml")
    h3 = soup.findAll("h3", text="Key Executives")[0]
    cSuiteTable = h3.parent.findAll("table")[0]
    headers = cSuiteTable.find("thead").findAll("th")
    headers = [h.text for h in headers]
    rows = cSuiteTable.find("tbody").findAll("tr")
    people = []
    for row in rows:
        cols = row.findAll("td")
        person = {}
        for ndx, key in enumerate(headers):
            person[key] = cols[ndx].text
        people.append(person)
    # now filter by title, and augment with identifier, before returning
    officers = [person for person in people if filterByTitle(person, titles)]
    for officer in officers:
        addNameIdentifiers(officer)
    return officers

def getBloombergProfile(officer):
    """Uses a site-specific search in an attempt to look up the unique ID used
       by their Bloomberg profile page.
    """
    url = BLOOMBERG_SEARCH_URL % (officer["First"], "%20", officer["Last"])
    res = requests.get(url)
    data = json.loads(res)
    profileUrl = data[0]["results"][0]["url"]
    officer["BloombergId"] = int(profileUrl.split("/")[-1])
    
def main():
    """
    """
    sectors = quant_local.getSectors()
    sector = quant_local.getSectorByCode(sectors, "ENERGY")
    securities = getSecuritiesByMarketCap(sector)
    for security in securities:
        csuite = getSecurityCSuite(security)
        for officer in csuite:


if __name__ == "__main__":
   main()
