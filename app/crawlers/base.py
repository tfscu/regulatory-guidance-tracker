from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.storage.models import GuidanceDocument


logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    agency: str
    jurisdiction: str

    @abstractmethod
    def crawl(self) -> list[GuidanceDocument]:
        ...


class PlaceholderCrawler(BaseCrawler):
    def __init__(self, agency: str, jurisdiction: str) -> None:
        self.agency = agency
        self.jurisdiction = jurisdiction

    def crawl(self) -> list[GuidanceDocument]:
        logger.warning("Crawler not yet implemented for %s.", self.agency)
        return []

