import asyncio
import random
import json
import aiohttp
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from tqdm import tqdm
from .base import BaseScraper


class OpenAlexScraper(BaseScraper):
	def __init__(self, config, target: Dict[str, Any]):
		super().__init__(config)
		self.target = target
		self.source_name = target.get("name", "OpenAlex Source")
		self.issn = target.get("issn", "")
		self.conference_name = self.source_name
		self.stats = {year: {"scanned": 0, "found": 0} for year in self.config.get("years", [])}

	def _reconstruct_abstract(self, inverted: Dict[str, List[int]]) -> str:
		if not inverted:
			return ""
		index_to_word = {}
		max_pos = 0
		for word, positions in inverted.items():
			for pos in positions:
				index_to_word[pos] = word
				if pos > max_pos:
					max_pos = pos
		words = [index_to_word.get(i, "") for i in range(max_pos + 1)]
		return " ".join(w for w in words if w)

	async def _fetch_doi_metadata(self, session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
		await asyncio.sleep(random.uniform(3, 5))
		headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
			"Accept-Language": "en-US,en;q=0.9",
		}
		try:
			async with session.get(url, headers=headers, timeout=self.config.get("timeout", 30)) as resp:
				if resp.status != 200:
					return {"abstract": "", "authors": []}
				html = await resp.text()
		except Exception:
			return {"abstract": "", "authors": []}

		soup = BeautifulSoup(html, "html.parser")
		abstract = ""
		meta_desc = soup.find("meta", attrs={"name": "description"})
		if meta_desc and meta_desc.get("content"):
			abstract = meta_desc.get("content").strip()
		if not abstract:
			og_desc = soup.find("meta", attrs={"property": "og:description"})
			if og_desc and og_desc.get("content"):
				abstract = og_desc.get("content").strip()
		if not abstract:
			abs_section = soup.find("section", attrs={"data-title": "Abstract"})
			if abs_section:
				abstract = abs_section.get_text(" ", strip=True)
		if not abstract:
			abs_div = soup.find("div", id="Abs1-content")
			if abs_div:
				abstract = abs_div.get_text(" ", strip=True)

		authors = []
		meta_authors = [
			m.get("content", "").strip()
			for m in soup.find_all("meta", attrs={"name": "citation_author"})
			if m.get("content")
		]
		if meta_authors:
			authors = meta_authors
		else:
			author_list = soup.find_all(class_="c-article-author-list__item")
			if author_list:
				authors = [a.get_text(strip=True) for a in author_list if a.get_text(strip=True)]

		return {"abstract": abstract, "authors": authors}

	async def _fetch_page(self, session: aiohttp.ClientSession, year: int, cursor: str, retries: int = 3) -> Dict[str, Any]:
		base_url = "https://api.openalex.org/works"
		params = {
			"filter": f"primary_location.source.issn:{self.issn},publication_year:{year}",
			"per-page": 200,
			"select": "title,publication_year,primary_location,authorships,abstract_inverted_index",
			"cursor": cursor,
		}
		for attempt in range(retries):
			async with session.get(base_url, params=params, timeout=self.config.get("timeout", 30)) as resp:
				resp.raise_for_status()
				text = await resp.text()
				try:
					return json.loads(text)
				except json.JSONDecodeError:
					if attempt == retries - 1:
						raise
					await asyncio.sleep(1 + attempt)
		return {}

	async def _fetch_year(self, session: aiohttp.ClientSession, year: int) -> List[Dict[str, Any]]:
		results: List[Dict[str, Any]] = []
		cursor = "*"
		while True:
			data = await self._fetch_page(session, year, cursor)
			items = data.get("results", [])
			if not items:
				break
			results.extend(items)
			cursor = data.get("meta", {}).get("next_cursor")
			if not cursor:
				break
		return results

	async def run(self, session: aiohttp.ClientSession):
		all_results = []
		years = self.config.get("years", [])
		if not years:
			print(f"[{self.source_name}] No years provided. Use --years to specify years.")
			return [], self.stats

		for year in years:
			print(f"[{self.source_name} {year}] Fetching from OpenAlex...")
			items = await self._fetch_year(session, year)
			if year not in self.stats:
				self.stats[year] = {"scanned": 0, "found": 0}

			for work in tqdm(items, desc=f"{self.source_name} {year}"):
				title = work.get("title", "") or ""
				abstract = self._reconstruct_abstract(work.get("abstract_inverted_index"))
				authors = []
				for auth in work.get("authorships", []) or []:
					author = auth.get("author", {}) or {}
					name = author.get("display_name")
					if name:
						authors.append(name)
				authors_text = ", ".join(authors) if authors else "Unknown Authors"
				url = (work.get("primary_location") or {}).get("landing_page_url", "")

				self.stats[year]["scanned"] += 1
				matched = self.is_match(title, abstract)
				if matched and (not abstract or not authors) and url:
					fallback = await self._fetch_doi_metadata(session, url)
					if not abstract:
						abstract = fallback.get("abstract", "")
					if not authors:
						authors = fallback.get("authors", [])
					authors_text = ", ".join(authors) if authors else "Unknown Authors"
					matched = self.is_match(title, abstract)

				if matched:
					self.stats[year]["found"] += 1
					print(f"[{self.source_name} {year}] Found: {title[:50]}...")
					all_results.append({
						"source": self.source_name,
						"year": year,
						"title": title,
						"authors": authors_text,
						"abstract": abstract,
						"url": url,
					})

			print(
				f"[{self.source_name} {year}] Scanned {self.stats[year]['scanned']} papers, "
				f"{self.stats[year]['found']} found matching keywords."
			)

		return all_results, self.stats
