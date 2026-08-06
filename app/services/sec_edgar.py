"""
SEC EDGAR Service - Real-time SEC Filings (10-K, 10-Q, 8-K) from SEC.gov
"""
import logging
import httpx
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "AtlasAI FinancialAssistant/1.0 (contact@atlasfinancial.ai)"
}


class SECEdgarService:
    """Service to query official SEC EDGAR database for public filings."""

    def __init__(self):
        self._cik_cache = {}

    async def _get_cik(self, ticker: str) -> str:
        """Resolve stock ticker to 10-digit CIK number."""
        ticker = ticker.upper().strip()
        if ticker in self._cik_cache:
            return self._cik_cache[ticker]

        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
                resp = await client.get("https://www.sec.gov/files/company_tickers.json")
                if resp.status_code == 200:
                    data = resp.json()
                    for entry in data.values():
                        if entry.get("ticker") == ticker:
                            cik = str(entry["cik_str"]).zfill(10)
                            self._cik_cache[ticker] = cik
                            return cik
        except Exception as e:
            logger.error(f"Error resolving CIK for {ticker}: {e}")

        return None

    async def get_recent_filings(self, ticker: str, form_type: str = None, limit: int = 5) -> Dict[str, Any]:
        """Fetch real recent SEC filings (10-K, 10-Q, 8-K) for a company."""
        ticker = ticker.upper().strip()
        cik = await self._get_cik(ticker)

        if not cik:
            return {"error": f"Could not find SEC CIK registration for '{ticker}'."}

        try:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    company_name = data.get("name", ticker)
                    recent = data.get("filings", {}).get("recent", {})

                    forms = recent.get("form", [])
                    dates = recent.get("filingDate", [])
                    accessions = recent.get("accessionNumber", [])
                    doc_names = recent.get("primaryDocument", [])
                    descriptions = recent.get("primaryDocDescription", [])

                    filings = []
                    for i in range(min(len(forms), 50)):
                        f_type = forms[i]
                        if form_type and form_type.upper() not in f_type.upper():
                            continue

                        acc_clean = accessions[i].replace("-", "")
                        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{doc_names[i]}"

                        filings.append({
                            "form": f_type,
                            "filing_date": dates[i],
                            "accession_number": accessions[i],
                            "description": descriptions[i] or f_type,
                            "sec_url": doc_url
                        })

                        if len(filings) >= limit:
                            break

                    return {
                        "ticker": ticker,
                        "company_name": company_name,
                        "cik": cik,
                        "filings": filings,
                        "source": "SEC EDGAR Official"
                    }
        except Exception as e:
            logger.error(f"Error fetching SEC filings for {ticker}: {e}")

        return {"error": f"Failed to retrieve SEC filings for '{ticker}'."}
