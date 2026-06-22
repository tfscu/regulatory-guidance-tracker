from __future__ import annotations

from app.crawlers.base import BaseCrawler, PlaceholderCrawler
from app.crawlers.fda import FDACrawler


def crawler_for_agency(agency: str) -> BaseCrawler:
    agency_key = agency.upper()
    if agency_key == "FDA":
        return FDACrawler()
    if agency_key == "EMA":
        return PlaceholderCrawler("EMA", "EU")
    if agency_key == "ICH":
        return PlaceholderCrawler("ICH", "International")
    if agency_key == "CDE":
        return PlaceholderCrawler("CDE", "China")
    if agency_key == "PMDA":
        return PlaceholderCrawler("PMDA", "Japan")
    raise ValueError(f"Unsupported agency: {agency}")


def configured_agencies() -> list[str]:
    return ["FDA", "EMA", "ICH", "CDE", "PMDA"]

