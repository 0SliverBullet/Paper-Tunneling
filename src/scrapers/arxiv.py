import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime
from tqdm import tqdm
from .base import BaseScraper


class ArxivScraper(BaseScraper):
    def __init__(self, config):
        super().__init__(config)
        self.conference_name = "arXiv"
        self.base_url = "http://export.arxiv.org/api/query"
        # We need a fallback structure for stats based on the years queried
        self.stats = {year: {"scanned": 0, "found": 0} for year in self.config.get("years", [])}

    def _build_query_url(self, year, max_results=1000, start=0):
        """Build the arXiv API query URL for a specific year and optional keywords."""
        # Note: arXiv API uses the `submittedDate` for date filtering
        # Format: [YYYYMMDDHHMM TO YYYYMMDDHHMM]
        date_range = f"[{year}01010000 TO {year}12312359]"
        
        # Combine date range with keywords if provided
        query_parts = []
        for keyword in self.config.get("keywords", []):
            # To get maximum relevant yield without overwhelming the API (like 10000+ papers),
            # we use unquoted words joined by AND if there are spaces.
            # Example: "AI Scientist" -> all:AI+AND+all:Scientist
            words = keyword.split()
            and_query = "+AND+".join(f"all:{w}" for w in words)
            query_parts.append(f"({and_query})")
            
        if not query_parts:
            # If no keywords, just query by date (can be very large!)
            search_query = f"submittedDate:{date_range}"
        else:
            # Join multiple keywords with OR, then AND with date range
            keywords_query = "+OR+".join(query_parts)
            search_query = f"({keywords_query})+AND+submittedDate:{date_range}"

        url = f"{self.base_url}?search_query={search_query}&start={start}&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
        return url

    async def _fetch_and_parse_batch(self, session, year, start, max_results):
        url = self._build_query_url(year, max_results, start)
        xml_data = await self.fetch(session, url)
        
        if not xml_data:
            return [], 0

        # Parse XML
        root = ET.fromstring(xml_data)
        
        # XML namespace for Atom
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        # Get total results for pagination
        total_results_elem = root.find('atom:totalResults', {'atom': 'http://a9.com/-/spec/opensearch/1.1/'})
        total_results = int(total_results_elem.text) if total_results_elem is not None else 0
        
        entries = root.findall('atom:entry', ns)
        
        parsed_papers = []
        for entry in entries:
            self.stats[year]["scanned"] += 1
            
            # Extract basic info
            title = entry.find('atom:title', ns).text.replace('\n', ' ').strip()
            abstract = entry.find('atom:summary', ns).text.replace('\n', ' ').strip()
            
            # Use local filtering to ensure exact keyword match as other scrapers
            if self.is_match(title, abstract):
                self.stats[year]["found"] += 1
                
                # Extract URL
                url = entry.find('atom:id', ns).text
                
                # Extract authors
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns).text
                    authors.append(name)
                authors_str = ", ".join(authors)
                
                parsed_papers.append({
                    "source": "arXiv",
                    "year": year,
                    "title": title,
                    "authors": authors_str,
                    "abstract": abstract,
                    "url": url,
                })
                
        return parsed_papers, total_results

    async def process_year(self, session, year):
        print(f"Scanning arXiv {year}...")
        
        all_year_papers = []
        start = 0
        max_results = 200 # Fetch up to 200 at a time
        
        # Fetch the first batch to get total_results
        first_batch_papers, total_results = await self._fetch_and_parse_batch(session, year, start, max_results)
        all_year_papers.extend(first_batch_papers)
        
        # We know total_results after the first fetch, so we can mock the ICML output format:
        # ICML prints: "[ICML 2024] Found X papers. Fetching details..."
        # Then uses tqdm for fetching
        # arXiv already fetched the first batch, so we report based on total_results.
        print(f"[arXiv {year}] Found {total_results} prospective papers. Fetching details...")
        
        # We want to show a progress bar for the actual processing.
        # arXiv fetches batches of up to 200. We can simulate the progress bar over the total batches.
        if total_results > 0:
            remaining_batches = []
            if total_results > max_results:
                for s in range(max_results, total_results, max_results):
                    remaining_batches.append(self._fetch_and_parse_batch(session, year, s, max_results))
            
            if remaining_batches:
                for coro in tqdm(asyncio.as_completed(remaining_batches), total=len(remaining_batches), desc=f"arXiv {year}"):
                    batch_papers, _ = await coro
                    all_year_papers.extend(batch_papers)
            else:
                # Mock a 100% progress bar if it all fit in the first batch
                for _ in tqdm(range(1), desc=f"arXiv {year}"):
                    pass
        
        return all_year_papers

    async def run(self, session):
        all_results = []
        
        for year in self.config.get("years", []):
            year_results = await self.process_year(session, year)
            all_results.extend(year_results)
            
        return all_results, self.stats
