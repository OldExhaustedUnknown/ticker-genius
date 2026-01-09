"""
Live test for SEC EDGAR EFTS Full-Text Search.

This test verifies the EFTS API actually works with real data.
"""
import sys
sys.path.insert(0, "src")

from tickergenius.collection.api_clients import SECEdgarClient


def test_efts_search():
    """Test EFTS full-text search with known PDUFA companies."""
    client = SECEdgarClient()

    test_tickers = ["BIIB", "MRNA", "VRTX"]  # Known pharma companies

    print("=" * 60)
    print("SEC EDGAR EFTS Full-Text Search Test")
    print("=" * 60)

    # First test: CIK mapping
    print("\n[1] Testing CIK Mapping...")
    for ticker in test_tickers:
        cik = client.get_company_cik(ticker)
        print(f"  {ticker} -> CIK: {cik}")

    # Second test: EFTS search
    print("\n[2] Testing EFTS Full-Text Search...")
    for ticker in test_tickers[:1]:  # Test with just BIIB first
        print(f"\n  Searching {ticker} for PDUFA keywords...")
        try:
            results = client._search_efts(
                ticker=ticker,
                keywords=["PDUFA", "FDA approval"],
                start_date="2020-01-01",
                end_date="2024-12-31",
            )
            print(f"  EFTS Results: {len(results)} filings found")
            if results:
                for r in results[:3]:
                    source = r.get("_source", {})
                    print(f"    - {source.get('file_date', 'N/A')}: {source.get('display_names', ['?'])[0][:60]}")
        except Exception as e:
            print(f"  EFTS Error: {type(e).__name__}: {e}")

    # Third test: Fallback to submissions API
    print("\n[3] Testing Submissions API Fallback...")
    for ticker in test_tickers[:1]:
        print(f"\n  Getting recent 8-K filings for {ticker}...")
        filings = client.get_recent_8k_filings(ticker, limit=10)
        print(f"  Found {len(filings)} 8-K filings via submissions API")
        if filings:
            for f in filings[:3]:
                print(f"    - {f.get('filingDate', 'N/A')}: {f.get('form', '')} - {f.get('primaryDocument', '')[:50]}")

    # Fourth test: Combined search with auto-fallback
    print("\n[4] Testing search_8k_filings (with auto-fallback)...")
    for ticker in test_tickers[:1]:
        results = client.search_8k_filings(
            ticker=ticker,
            keywords=["FDA", "approval", "PDUFA"],
            start_date="2020-01-01",
        )
        print(f"  {ticker}: {len(results)} total results")

        # Test keyword extraction
        if results:
            print("\n  Keyword extraction from first filing:")
            info = client.extract_pdufa_info(results[0])
            print(f"    PDUFA mention: {info['has_pdufa_mention']}")
            print(f"    Approval: {info['has_approval']}")
            print(f"    CRL: {info['has_crl']}")
            print(f"    Keywords: {info['detected_keywords']}")

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    test_efts_search()
