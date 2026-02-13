"""
scraper.py - Playwright-based web scraper for stock news and data
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
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def start(self):
        """Initialize browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = self.context.new_page()

    def close(self):
        """Close browser"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()

    def get_stock_news(self, ticker: str, max_articles: int = 5) -> List[Dict[str, str]]:
        """
        Get news headlines for a specific ticker from Yahoo Finance

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            max_articles: Maximum number of articles to retrieve

        Returns:
            List of dictionaries with 'title', 'link', and 'time' keys
        """
        # Use dedicated news page (not main quote page) - structure is more stable
        url = f"https://finance.yahoo.com/quote/{ticker}/news"

        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)  # Wait for dynamic content (news loads via JS)

            news_items = []
            elements = []

            # Try multiple selectors for news items (Yahoo often changes structure)
            selectors = [
                'li.stream-item',  # Dedicated news page uses this
                'section[data-testid="news"] li',
                'div[data-testid="news-stream"] li',
                'div.stream-items li',
                'ul li[class*="stream"]',
                'article',
                'div[class*="news"] li'
            ]

            for selector in selectors:
                try:
                    found = self.page.query_selector_all(selector)
                    if found and len(found) > 0:
                        elements = found
                        break
                except Exception:
                    continue

            if not elements:
                print(f"Warning: No news elements found for {ticker}")
                return []

            for element in elements[:max_articles]:
                try:
                    # Extract headline
                    title_elem = element.query_selector('h3, a h3, div h3')
                    title = title_elem.inner_text().strip() if title_elem else None

                    # Extract link
                    link_elem = element.query_selector('a')
                    link = link_elem.get_attribute('href') if link_elem else None
                    if link and link.startswith('/'):
                        link = f"https://finance.yahoo.com{link}"

                    # Extract time
                    time_elem = element.query_selector('time, span[class*="time"]')
                    publish_time = time_elem.inner_text().strip() if time_elem else 'Unknown'

                    if title:
                        news_items.append({
                            'title': title,
                            'link': link or '',
                            'time': publish_time
                        })
                except Exception as e:
                    continue

            return news_items

        except PlaywrightTimeout:
            print(f"Timeout while loading {ticker}")
            return []
        except Exception as e:
            print(f"Error scraping {ticker}: {str(e)}")
            return []

    def get_top_gainers(self, limit: int = 20) -> List[Dict[str, str]]:
        """
        Get top gaining stocks from Yahoo Finance

        Args:
            limit: Maximum number of gainers to retrieve

        Returns:
            List of dictionaries with ticker info
        """
        url = "https://finance.yahoo.com/markets/stocks/gainers/"

        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)  # Wait for table to load

            gainers = []

            # Find table rows
            rows = self.page.query_selector_all('table tbody tr')

            for row in rows[:limit]:
                try:
                    cells = row.query_selector_all('td')
                    if len(cells) >= 3:
                        # Extract ticker symbol
                        symbol_elem = cells[0].query_selector('a')
                        symbol = symbol_elem.inner_text().strip() if symbol_elem else None

                        # Extract company name
                        name_elem = cells[1]
                        name = name_elem.inner_text().strip() if name_elem else ''

                        # Extract price
                        price_elem = cells[2]
                        price = price_elem.inner_text().strip() if price_elem else '0'

                        # Extract change percentage
                        change_elem = cells[3] if len(cells) > 3 else None
                        change = change_elem.inner_text().strip() if change_elem else '0%'

                        if symbol:
                            gainers.append({
                                'symbol': symbol,
                                'name': name,
                                'price': price,
                                'change': change
                            })
                except Exception as e:
                    continue

            return gainers

        except Exception as e:
            print(f"Error scraping top gainers: {str(e)}")
            return []

    def check_keywords_in_news(
        self,
        ticker: str,
        keywords: List[str],
        news_items: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, any]:
        """
        Check if any important keywords appear in recent news

        Args:
            ticker: Stock ticker symbol
            keywords: List of keywords to search for
            news_items: Optional pre-fetched news (avoids duplicate API/scrape calls)

        Returns:
            Dictionary with 'found' (bool) and 'matches' (list of found keywords)
        """
        if news_items is None:
            news_items = self.get_stock_news(ticker, max_articles=10)

        found_keywords = set()

        for item in news_items:
            title_lower = item['title'].lower()
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    found_keywords.add(keyword)

        return {
            'found': len(found_keywords) > 0,
            'matches': list(found_keywords),
            'news_count': len(news_items)
        }


def test_scraper():
    """Test the scraper functionality"""
    with StockScraper(headless=True) as scraper:
        # Test 1: Get news for a specific ticker
        print("Testing news scraper for TSLA...")
        news = scraper.get_stock_news('TSLA', max_articles=3)
        for item in news:
            print(f"  - {item['title']}")

        print("\nTesting top gainers...")
        gainers = scraper.get_top_gainers(limit=5)
        for gainer in gainers:
            print(f"  {gainer['symbol']}: {gainer['change']}")

        print("\nTesting keyword detection...")
        result = scraper.check_keywords_in_news('TSLA', ['FDA', 'approval', 'earnings'])
        print(f"  Keywords found: {result['matches']}")


if __name__ == '__main__':
    test_scraper()
