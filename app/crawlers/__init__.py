from __future__ import annotations

from app.crawlers.base import BaseCrawler, PlaceholderCrawler
from app.crawlers.cde import CDECrawler
from app.crawlers.ema import EMACrawler
from app.crawlers.fda import FDACrawler
from app.crawlers.ich import ICHCrawler


def crawler_for_agency(agency: str) -> BaseCrawler:
    agency_key = agency.upper()
    if agency_key == "FDA":
        return FDACrawler()
    if agency_key == "EMA":
        return EMACrawler()
    if agency_key == "ICH":
        return ICHCrawler()
    if agency_key == "CDE":
        return CDECrawler()
    if agency_key == "PMDA":
        return PlaceholderCrawler("PMDA", "Japan")
    raise ValueError(f"Unsupported agency: {agency}")


def configured_agencies() -> list[str]:
    return ["FDA", "EMA", "ICH", "CDE", "PMDA"]
