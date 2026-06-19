"""
Data ingestion module.

IMPORTANT NOTE ON DATA SOURCE:
This generates realistic synthetic price + fundamental data for 100+ NSE/BSE
listed companies and loads it into the database in the same schema real
scraped data would use. This was necessary because live internet access to
Yahoo Finance / Screener.in was not available in the build environment.

To use REAL data instead, replace fetch_prices() and fetch_fundamentals()
below with actual API/scraping calls (e.g. yfinance.download(), or a
Screener.in scraper) — the rest of the pipeline (storage, backtest engine,
frontend) does not need to change, since it only depends on the DB schema
defined in database.py.
"""

import random
from datetime import date, timedelta

from database import Company, Price, Fundamental, init_db, get_session

random.seed(42)

SECTORS = [
    "IT", "Banking", "Pharma", "FMCG", "Auto", "Metals", "Energy",
    "Infrastructure", "Chemicals", "Consumer Durables", "Cement", "Realty",
]

# 100 representative Indian company name/symbol pairs
COMPANIES = [
    ("RELIANCE", "Reliance Industries"), ("TCS", "Tata Consultancy Services"),
    ("HDFCBANK", "HDFC Bank"), ("INFY", "Infosys"), ("ICICIBANK", "ICICI Bank"),
    ("HINDUNILVR", "Hindustan Unilever"), ("ITC", "ITC Ltd"), ("SBIN", "State Bank of India"),
    ("BHARTIARTL", "Bharti Airtel"), ("KOTAKBANK", "Kotak Mahindra Bank"),
    ("LT", "Larsen & Toubro"), ("AXISBANK", "Axis Bank"), ("BAJFINANCE", "Bajaj Finance"),
    ("ASIANPAINT", "Asian Paints"), ("MARUTI", "Maruti Suzuki"), ("HCLTECH", "HCL Technologies"),
    ("SUNPHARMA", "Sun Pharmaceutical"), ("TITAN", "Titan Company"), ("ULTRACEMCO", "UltraTech Cement"),
    ("WIPRO", "Wipro"), ("NESTLEIND", "Nestle India"), ("ONGC", "Oil & Natural Gas Corp"),
    ("NTPC", "NTPC Ltd"), ("POWERGRID", "Power Grid Corp"), ("TATAMOTORS", "Tata Motors"),
    ("TATASTEEL", "Tata Steel"), ("ADANIENT", "Adani Enterprises"), ("ADANIPORTS", "Adani Ports"),
    ("JSWSTEEL", "JSW Steel"), ("COALINDIA", "Coal India"), ("BAJAJFINSV", "Bajaj Finserv"),
    ("HDFCLIFE", "HDFC Life Insurance"), ("SBILIFE", "SBI Life Insurance"), ("GRASIM", "Grasim Industries"),
    ("DRREDDY", "Dr Reddy's Laboratories"), ("CIPLA", "Cipla"), ("DIVISLAB", "Divi's Laboratories"),
    ("BRITANNIA", "Britannia Industries"), ("EICHERMOT", "Eicher Motors"), ("HEROMOTOCO", "Hero MotoCorp"),
    ("BAJAJ-AUTO", "Bajaj Auto"), ("M&M", "Mahindra & Mahindra"), ("INDUSINDBK", "IndusInd Bank"),
    ("TECHM", "Tech Mahindra"), ("UPL", "UPL Ltd"), ("APOLLOHOSP", "Apollo Hospitals"),
    ("BPCL", "Bharat Petroleum"), ("IOC", "Indian Oil Corp"), ("HINDALCO", "Hindalco Industries"),
    ("VEDL", "Vedanta Ltd"), ("GAIL", "GAIL India"), ("PIDILITIND", "Pidilite Industries"),
    ("DABUR", "Dabur India"), ("GODREJCP", "Godrej Consumer Products"), ("MARICO", "Marico Ltd"),
    ("COLPAL", "Colgate-Palmolive India"), ("BERGEPAINT", "Berger Paints"), ("HAVELLS", "Havells India"),
    ("SIEMENS", "Siemens Ltd"), ("ABB", "ABB India"), ("BOSCHLTD", "Bosch Ltd"),
    ("PAGEIND", "Page Industries"), ("MUTHOOTFIN", "Muthoot Finance"), ("CHOLAFIN", "Cholamandalam Investment"),
    ("LICHSGFIN", "LIC Housing Finance"), ("PFC", "Power Finance Corp"), ("RECLTD", "REC Ltd"),
    ("CANBK", "Canara Bank"), ("PNB", "Punjab National Bank"), ("BANKBARODA", "Bank of Baroda"),
    ("FEDERALBNK", "Federal Bank"), ("IDFCFIRSTB", "IDFC First Bank"), ("AUBANK", "AU Small Finance Bank"),
    ("LUPIN", "Lupin Ltd"), ("AUROPHARMA", "Aurobindo Pharma"), ("BIOCON", "Biocon Ltd"),
    ("TORNTPHARM", "Torrent Pharmaceuticals"), ("ALKEM", "Alkem Laboratories"),
    ("AMBUJACEM", "Ambuja Cements"), ("ACC", "ACC Ltd"), ("SHREECEM", "Shree Cement"),
    ("DLF", "DLF Ltd"), ("GODREJPROP", "Godrej Properties"), ("OBEROIRLTY", "Oberoi Realty"),
    ("INDIGO", "InterGlobe Aviation"), ("IRCTC", "IRCTC Ltd"), ("CONCOR", "Container Corp of India"),
    ("ZOMATO", "Zomato Ltd"), ("NYKAA", "FSN E-Commerce (Nykaa)"), ("PAYTM", "One97 (Paytm)"),
    ("POLICYBZR", "PB Fintech (Policybazaar)"), ("DMART", "Avenue Supermarts (DMart)"),
    ("TRENT", "Trent Ltd"), ("NAUKRI", "Info Edge (Naukri)"), ("MPHASIS", "Mphasis Ltd"),
    ("LTIM", "LTIMindtree"), ("PERSISTENT", "Persistent Systems"), ("COFORGE", "Coforge Ltd"),
    ("OFSS", "Oracle Financial Services"), ("MFSL", "Max Financial Services"),
    ("ICICIPRULI", "ICICI Prudential Life"), ("ICICIGI", "ICICI Lombard General Insurance"),
    ("BANDHANBNK", "Bandhan Bank"), ("YESBANK", "Yes Bank"), ("RBLBANK", "RBL Bank"),
    ("JINDALSTEL", "Jindal Steel & Power"), ("SAIL", "Steel Authority of India"),
    ("NMDC", "NMDC Ltd"), ("NATIONALUM", "National Aluminium Co"),
]

START_DATE = date(2019, 1, 1)
END_DATE = date(2024, 12, 31)


def _trading_days(start, end):
    """Approximate trading days: weekdays only, no holiday calendar (kept simple)."""
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:  # Mon-Fri
            days.append(d)
        d += timedelta(days=1)
    return days


def _quarter_ends(start, end):
    dates = []
    y = start.year
    for y in range(start.year, end.year + 1):
        for m in (3, 6, 9, 12):
            qd = date(y, m, 28) + timedelta(days=4)
            qd = qd - timedelta(days=qd.day)  # last day of month
            if start <= qd <= end:
                dates.append(qd)
    return dates


def generate_price_series(base_price, n_days, drift=0.0003, vol=0.018):
    """Simple geometric random walk to simulate a stock price series."""
    prices = [base_price]
    for _ in range(n_days - 1):
        change = random.gauss(drift, vol)
        new_price = max(prices[-1] * (1 + change), 1.0)
        prices.append(new_price)
    return prices


def load_all_data():
    init_db()
    session = get_session()

    # wipe existing data for a clean reload
    session.query(Price).delete()
    session.query(Fundamental).delete()
    session.query(Company).delete()
    session.commit()

    trading_days = _trading_days(START_DATE, END_DATE)
    quarter_ends = _quarter_ends(START_DATE, END_DATE)

    print(f"Generating data for {len(COMPANIES)} companies, "
          f"{len(trading_days)} trading days, {len(quarter_ends)} quarters...")

    for symbol, name in COMPANIES:
        sector = random.choice(SECTORS)
        company = Company(symbol=symbol, name=name, sector=sector)
        session.add(company)
        session.flush()  # get company.id

        base_price = random.uniform(50, 4000)
        drift = random.uniform(-0.0002, 0.0008)
        vol = random.uniform(0.012, 0.028)
        series = generate_price_series(base_price, len(trading_days), drift, vol)

        price_rows = []
        for d, close in zip(trading_days, series):
            open_p = close * random.uniform(0.985, 1.0)
            high_p = max(open_p, close) * random.uniform(1.0, 1.02)
            low_p = min(open_p, close) * random.uniform(0.98, 1.0)
            vol_traded = random.randint(50_000, 5_000_000)
            price_rows.append(Price(
                company_id=company.id, date=d,
                open=round(open_p, 2), high=round(high_p, 2),
                low=round(low_p, 2), close=round(close, 2), volume=vol_traded
            ))
        session.bulk_save_objects(price_rows)

        # fundamentals: generate with mild trend + noise per quarter
        shares_outstanding_cr = random.uniform(5, 600)  # crore shares
        base_pat = random.uniform(20, 5000)
        base_revenue = base_pat * random.uniform(3, 12)
        fundamental_rows = []
        for i, qd in enumerate(quarter_ends):
            growth = (1 + random.uniform(-0.04, 0.07)) ** (i + 1)
            pat = base_pat * growth * random.uniform(0.85, 1.15)
            revenue = base_revenue * growth * random.uniform(0.9, 1.1)
            close_near_q = min(series[:len(_trading_days(START_DATE, qd))] or [base_price], key=lambda x: x)
            idx = min(range(len(trading_days)), key=lambda k: abs((trading_days[k] - qd).days))
            price_at_q = series[idx]
            market_cap = price_at_q * shares_outstanding_cr  # INR Cr (price in Rs, shares in Cr)
            roce = max(random.gauss(15, 8), -10)
            roe = max(random.gauss(14, 9), -10)
            pe = max(market_cap / pat, 1) if pat > 0 else random.uniform(40, 100)
            de = max(random.gauss(0.6, 0.5), 0)

            fundamental_rows.append(Fundamental(
                company_id=company.id, report_date=qd,
                market_cap_cr=round(market_cap, 2),
                pat_cr=round(pat, 2),
                revenue_cr=round(revenue, 2),
                roce=round(roce, 2),
                roe=round(roe, 2),
                pe_ratio=round(pe, 2),
                debt_to_equity=round(de, 2),
            ))
        session.bulk_save_objects(fundamental_rows)
        session.commit()
        print(f"  loaded {symbol}")

    print("Done. Database populated.")


if __name__ == "__main__":
    load_all_data()
