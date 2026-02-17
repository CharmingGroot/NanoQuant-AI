"""
core/scraper.py - Playwright-based web scraper for stock news and data
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from typing import List, Dict, Optional
import time


class StockScraper:
    """Scrapes stock news and data from Yahoo Finance and other sources"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.page = self.context.new_page()

    def close(self):
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()

    def get_stock_news(self, ticker: str, max_articles: int = 5) -> List[Dict[str, str]]:
        url = f"https://finance.yahoo.com/quote/{ticker}/news"
        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            news_items = []
            elements = []
            selectors = ['li.stream-item', 'section[data-testid="news"] li', 'div[data-testid="news-stream"] li', 'div.stream-items li', 'ul li[class*="stream"]', 'article', 'div[class*="news"] li']
            for selector in selectors:
                try:
                    found = self.page.query_selector_all(selector)
                    if found and len(found) > 0:
                        elements = found
                        break
                except Exception:
                    continue
            if not elements:
                return []
            for element in elements[:max_articles]:
                try:
                    title_elem = element.query_selector('h3, a h3, div h3')
                    title = title_elem.inner_text().strip() if title_elem else None
                    link_elem = element.query_selector('a')
                    link = link_elem.get_attribute('href') if link_elem else None
                    if link and link.startswith('/'):
                        link = f"https://finance.yahoo.com{link}"
                    time_elem = element.query_selector('time, span[class*="time"]')
                    publish_time = time_elem.inner_text().strip() if time_elem else 'Unknown'
                    if title:
                        news_items.append({'title': title, 'link': link or '', 'time': publish_time})
                except Exception:
                    continue
            return news_items
        except PlaywrightTimeout:
            return []
        except Exception as e:
            print(f"Error scraping {ticker}: {str(e)}")
            return []

    def get_top_gainers(self, limit: int = 20) -> List[Dict[str, str]]:
        url = "https://finance.yahoo.com/markets/stocks/gainers/"
        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)
            gainers = []
            rows = self.page.query_selector_all('table tbody tr')
            for row in rows[:limit]:
                try:
                    cells = row.query_selector_all('td')
                    if len(cells) >= 3:
                        symbol_elem = cells[0].query_selector('a')
                        symbol = symbol_elem.inner_text().strip() if symbol_elem else None
                        name = cells[1].inner_text().strip() if cells[1] else ''
                        price = cells[2].inner_text().strip() if cells[2] else '0'
                        change_elem = cells[3] if len(cells) > 3 else None
                        change = change_elem.inner_text().strip() if change_elem else '0%'
                        if symbol:
                            gainers.append({'symbol': symbol, 'name': name, 'price': price, 'change': change})
                except Exception:
                    continue
            return gainers
        except Exception as e:
            print(f"Error scraping top gainers: {str(e)}")
            return []

    def check_keywords_in_news(self, ticker: str, keywords: List[str], news_items: Optional[List[Dict[str, str]]] = None) -> Dict:
        if news_items is None:
            news_items = self.get_stock_news(ticker, max_articles=10)
        found_keywords = set()
        for item in news_items:
            title_lower = item['title'].lower()
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    found_keywords.add(keyword)
        return {'found': len(found_keywords) > 0, 'matches': list(found_keywords), 'news_count': len(news_items)}
