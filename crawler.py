from collections import deque
from dataclasses import dataclass
from typing import Set
from urllib.parse import urljoin, urlparse, urldefrag

from playwright.async_api import BrowserContext


@dataclass
class CrawlConfig:
    max_pages: int = 8


class WebsiteCrawler:
    def __init__(self, start_url: str, config: CrawlConfig | None = None):
        self.start_url = start_url
        self.config = config or CrawlConfig()
        self.base_domain = urlparse(start_url).netloc
        self.visited: Set[str] = set()

    def _normalize(self, url: str) -> str:
        clean, _ = urldefrag(url)
        return clean.rstrip("/")

    def _is_internal(self, url: str) -> bool:
        return urlparse(url).netloc == self.base_domain

    async def crawl(self, context: BrowserContext) -> list[str]:
        queue = deque([self._normalize(self.start_url)])
        collected: list[str] = []

        while queue and len(collected) < self.config.max_pages:
            current_url = queue.popleft()
            if current_url in self.visited:
                continue

            self.visited.add(current_url)
            page = await context.new_page()
            try:
                await page.goto(current_url, wait_until="domcontentloaded", timeout=30000)
                collected.append(current_url)

                links = await page.eval_on_selector_all(
                    "a[href]",
                    """anchors => anchors.map(a => a.getAttribute('href')).filter(Boolean)""",
                )

                for href in links:
                    absolute = self._normalize(urljoin(current_url, href))
                    if not absolute.startswith(("http://", "https://")):
                        continue
                    if not self._is_internal(absolute):
                        continue
                    if absolute in self.visited:
                        continue
                    if absolute not in queue:
                        queue.append(absolute)
            finally:
                await page.close()

        return collected
