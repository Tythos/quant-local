quant_local
===========

Locally-hosted quantitative analysis for financial markets. Date-stamped
folders in the "datastore" directory are saved from Fidelity market research
for each sector. These folders also include tables for:

* Sector definitions

* Buy filters (each row is AND-joined)

* Sell fitlers (each row is AND-joined)

* Positions (currently open as of that date)

The script in the primary package "__init__.py" file performs the following
when run from the command line:

1. Filters securities for each sector based on the conditions in the
   "filters_buy.xlsx" spreadsheet

2. Two metrics are computed for each sector. These are currently 52-week growth
   and standard deviation.

3. A frontier is computed to optimize between those two metrics. The
   second-highest point is selected as a recommended security.

4. Buy recommendations are reported to STDOUT (ignored if the position is
   already held).

5. Sell recommendations are similarly filtered (though no metrics are computed
   and no frontier selection is made; they are merely drawn from the existing
   positions).
