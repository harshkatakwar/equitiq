"""News and material filing monitor tool.

Ported from day-trader-skill `trader-news`:
Watches breaking headlines and SEC 8-K material event filings for monitored stocks.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any
import httpx

from src.modules.trader_agent.sec_analyst import get_company_cik, _get_sec_headers

logger = logging.getLogger(__name__)

YAHOO_RSS = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
SEC_8K_FEED = (
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
    "&type=8-K&dateb=&owner=include&count=5&output=atom"
)


async def fetch_company_news_and_filings(symbol: str) -> dict[str, Any]:
    """Fetch recent headlines from Yahoo RSS and material 8-K filings from SEC."""
    sym = symbol.strip().upper()
    articles: list[dict[str, Any]] = []
    filings: list[dict[str, Any]] = []

    # 1. Fetch Yahoo RSS headlines
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(
                YAHOO_RSS.format(symbol=sym),
                headers={"User-Agent": "Mozilla/5.0 (compatible; EquitIQNewsBot/1.0)"},
            )
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for item in root.findall(".//item")[:10]:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    pub_date_elem = item.find("pubDate")

                    title = title_elem.text if title_elem is not None else ""
                    link = link_elem.text if link_elem is not None else ""
                    pub_date = pub_date_elem.text if pub_date_elem is not None else ""

                    if title:
                        articles.append({
                            "title": title.strip(),
                            "link": link.strip(),
                            "published_at": pub_date.strip(),
                            "source": "Yahoo Finance",
                        })
    except Exception as e:
        logger.warning("Could not fetch Yahoo headlines for %s: %s", sym, e)

    # 2. Fetch SEC 8-K material filings
    try:
        cik_info = await get_company_cik(sym)
        if cik_info and cik_info.get("cik"):
            cik = cik_info["cik"]
            sec_headers = await _get_sec_headers()
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(SEC_8K_FEED.format(cik=cik), headers=sec_headers)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    for entry in root.findall("atom:entry", ns)[:5]:
                        title_el = entry.find("atom:title", ns)
                        updated_el = entry.find("atom:updated", ns)
                        link_el = entry.find("atom:link", ns)
                        href = link_el.get("href", "") if link_el is not None else ""

                        title = title_el.text if title_el is not None else ""
                        updated = updated_el.text if updated_el is not None else ""

                        if title:
                            filings.append({
                                "title": title.strip(),
                                "form": "8-K",
                                "link": href,
                                "filed_at": updated[:10] if updated else "",
                                "source": "SEC EDGAR",
                            })
    except Exception as e:
        logger.warning("Could not fetch SEC 8-K filings for %s: %s", sym, e)

    return {
        "symbol": sym,
        "articles": articles[:8],
        "material_8k_filings": filings,
        "total_news_items": len(articles) + len(filings),
    }
