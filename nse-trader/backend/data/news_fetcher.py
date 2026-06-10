# data/news_fetcher.py
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Stock name mapping for better news search
STOCK_NAMES = {
    "HDFCBANK.NS": "HDFC Bank",
    "ICICIBANK.NS": "ICICI Bank",
    "KOTAKBANK.NS": "Kotak Mahindra Bank",
    "SBIN.NS": "State Bank of India SBI",
    "AXISBANK.NS": "Axis Bank",
    "BAJFINANCE.NS": "Bajaj Finance",
    "BAJAJFINSV.NS": "Bajaj Finserv",
    "HDFCLIFE.NS": "HDFC Life Insurance",
    "SBILIFE.NS": "SBI Life Insurance",
    "ICICIPRULI.NS": "ICICI Prudential Life",
    "TCS.NS": "TCS Tata Consultancy Services",
    "INFY.NS": "Infosys",
    "WIPRO.NS": "Wipro",
    "HCLTECH.NS": "HCL Technologies",
    "TECHM.NS": "Tech Mahindra",
    "LTM.NS": "LTIMindtree",
    "RELIANCE.NS": "Reliance Industries",
    "ONGC.NS": "ONGC Oil Natural Gas",
    "BPCL.NS": "BPCL Bharat Petroleum",
    "POWERGRID.NS": "Power Grid Corporation",
    "NTPC.NS": "NTPC Limited",
    "COALINDIA.NS": "Coal India",
    "HINDUNILVR.NS": "Hindustan Unilever HUL",
    "ITC.NS": "ITC Limited",
    "NESTLEIND.NS": "Nestle India",
    "BRITANNIA.NS": "Britannia Industries",
    "TATACONSUM.NS": "Tata Consumer Products",
    "MARUTI.NS": "Maruti Suzuki",
    "BAJAJ-AUTO.NS": "Bajaj Auto",
    "HEROMOTOCO.NS": "Hero MotoCorp",
    "EICHERMOT.NS": "Eicher Motors Royal Enfield",
    "SUNPHARMA.NS": "Sun Pharmaceutical",
    "DRREDDY.NS": "Dr Reddy Laboratories",
    "CIPLA.NS": "Cipla",
    "DIVISLAB.NS": "Divi's Laboratories",
    "TATASTEEL.NS": "Tata Steel",
    "JSWSTEEL.NS": "JSW Steel",
    "HINDALCO.NS": "Hindalco Industries",
    "ULTRACEMCO.NS": "UltraTech Cement",
    "GRASIM.NS": "Grasim Industries",
    "BHARTIARTL.NS": "Bharti Airtel",
    "ADANIENT.NS": "Adani Enterprises",
    "ADANIPORTS.NS": "Adani Ports",
    "LT.NS": "Larsen Toubro L&T",
    "ASIANPAINT.NS": "Asian Paints",
    "TITAN.NS": "Titan Company",
    "INDUSINDBK.NS": "IndusInd Bank",
    "M&M.NS": "Mahindra Mahindra",
    "APOLLOHOSP.NS": "Apollo Hospitals",
}


def fetch_stock_news(symbol: str, max_articles: int = 5) -> list:
    """
    Fetch recent news headlines for a stock
    Uses RSS feeds — completely free, no API key needed
    """
    company_name = STOCK_NAMES.get(symbol, symbol.replace('.NS', ''))
    ticker = symbol.replace('.NS', '').replace('.BO', '')

    news_items = []

    # Try multiple free sources
    sources = [
        f"https://news.google.com/rss/search?q={company_name.replace(' ', '+')}+NSE+stock&hl=en-IN&gl=IN&ceid=IN:en",
        f"https://news.google.com/rss/search?q={ticker}+NSE+India+stock+market&hl=en-IN&gl=IN&ceid=IN:en",
    ]

    for url in sources:
        try:
            response = requests.get(url, timeout=5,
                headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code != 200:
                continue

            # Parse RSS manually — no library needed
            content = response.text
            items = content.split('<item>')

            for item in items[1:max_articles+1]:
                try:
                    title = item.split('<title>')[1].split('</title>')[0]
                    title = title.replace('<![CDATA[', '').replace(']]>', '').strip()

                    pub_date = ''
                    if '<pubDate>' in item:
                        pub_date = item.split('<pubDate>')[1].split('</pubDate>')[0].strip()

                    if title and len(title) > 10:
                        news_items.append({
                            'title': title,
                            'date': pub_date[:16] if pub_date else 'Recent',
                            'source': 'Google News'
                        })
                except:
                    continue

            if news_items:
                break

        except Exception as e:
            continue

    # Deduplicate
    seen = set()
    unique_news = []
    for item in news_items:
        if item['title'] not in seen:
            seen.add(item['title'])
            unique_news.append(item)

    return unique_news[:max_articles]


def format_news_for_claude(symbol: str, news_items: list) -> str:
    """Format news items as a string for Claude prompt"""
    if not news_items:
        return "No recent news found."

    company = STOCK_NAMES.get(symbol, symbol.replace('.NS', ''))
    lines = [f"Recent news for {company}:"]

    for i, item in enumerate(news_items, 1):
        lines.append(f"{i}. [{item['date']}] {item['title']}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Test with a few stocks
    test_stocks = ["TCS.NS", "RELIANCE.NS", "HDFCBANK.NS"]
    for symbol in test_stocks:
        print(f"\n📰 News for {symbol}:")
        news = fetch_stock_news(symbol)
        if news:
            for item in news:
                print(f"  • {item['title'][:80]}")
        else:
            print("  No news found")