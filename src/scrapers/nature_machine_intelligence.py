import asyncio
import re
from bs4 import BeautifulSoup
from tqdm import tqdm
from .base import BaseScraper


class NatureMachineIntelligenceScraper(BaseScraper):
	def __init__(self, config):
		super().__init__(config)
		self.conference_name = "Nature Machine Intelligence"
		self.base_url = "https://www.nature.com"
		self.stats = {year: {"scanned": 0, "found": 0} for year in self.config.get("years", [])}
		self.year_urls = {
			year: f"{self.base_url}/natmachintell/research-articles?type=article&year={year}"
			for year in self.config.get("years", [])
		}

	async def fetch(self, session, url):
		"""覆盖 fetch，增加 UA 以降低被拦截概率"""
		headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
			"Accept-Language": "en-US,en;q=0.9",
		}
		try:
			async with session.get(url, headers=headers, timeout=self.config.get("timeout", 30)) as response:
				if response.status == 200:
					return await response.text()
				return None
		except Exception as e:
			print(f"Error fetching {url}: {e}")
			return None

	def _extract_year(self, soup):
		for name in ["citation_publication_date", "citation_online_date"]:
			meta = soup.find("meta", attrs={"name": name})
			if meta and meta.get("content"):
				match = re.search(r"(20\d{2})", meta.get("content"))
				if match:
					return int(match.group(1))
			meta = soup.find("meta", attrs={"property": "article:published_time"})
			if meta and meta.get("content"):
				match = re.search(r"(20\d{2})", meta.get("content"))
				if match:
					return int(match.group(1))
		return None

	async def parse_paper_details(self, session, url, title, semaphore):
		async with semaphore:
			html = await self.fetch(session, url)
			if not html:
				return None

			soup = BeautifulSoup(html, "html.parser")

			# title
			if not title:
				meta_title = soup.find("meta", attrs={"name": "citation_title"})
				if meta_title and meta_title.get("content"):
					title = meta_title.get("content").strip()
				else:
					og_title = soup.find("meta", attrs={"property": "og:title"})
					if og_title and og_title.get("content"):
						title = og_title.get("content").strip()
					else:
						h1 = soup.find("h1")
						title = h1.get_text(strip=True) if h1 else ""

			# authors
			authors_text = "Unknown Authors"
			meta_authors = [
				m.get("content", "").strip()
				for m in soup.find_all("meta", attrs={"name": "citation_author"})
				if m.get("content")
			]
			if meta_authors:
				authors_text = ", ".join(meta_authors)
			else:
				author_list = soup.find_all(class_="c-article-author-list__item")
				if author_list:
					authors_text = ", ".join(a.get_text(strip=True) for a in author_list)

			# abstract
			abstract_text = ""
			meta_desc = soup.find("meta", attrs={"name": "description"})
			if meta_desc and meta_desc.get("content"):
				abstract_text = meta_desc.get("content").strip()
			if not abstract_text:
				og_desc = soup.find("meta", attrs={"property": "og:description"})
				if og_desc and og_desc.get("content"):
					abstract_text = og_desc.get("content").strip()
			if not abstract_text:
				abs_section = soup.find("section", attrs={"data-title": "Abstract"})
				if abs_section:
					abstract_text = abs_section.get_text(" ", strip=True)

			year = self._extract_year(soup)
			if year is None:
				years_cfg = self.config.get("years") or []
				year = years_cfg[0] if years_cfg else None

			if year is None:
				return None

			if self.config.get("years") and year not in self.config.get("years"):
				return None

			if year not in self.stats:
				self.stats[year] = {"scanned": 0, "found": 0}

			self.stats[year]["scanned"] += 1
			if self.is_match(title, abstract_text):
				self.stats[year]["found"] += 1
				print(f"[NMI {year}] Found: {title[:50]}...")
				return {
					"source": "Nature Machine Intelligence",
					"year": year,
					"title": title,
					"authors": authors_text,
					"abstract": abstract_text,
					"url": url,
				}
			return None

	async def process_year(self, session, year, list_url, semaphore):
		html = await self.fetch(session, list_url)
		if not html:
			print(f"Failed to load list: {list_url}")
			return []

		soup = BeautifulSoup(html, "html.parser")
		links = soup.find_all("a", href=True)

		tasks = []
		unique_urls = set()
		for link in links:
			href = link["href"]
			if "/articles/" in href:
				full_url = href
				if href.startswith("/"):
					full_url = self.base_url + href

				if full_url in unique_urls:
					continue
				unique_urls.add(full_url)

				title = link.get_text(strip=True)
				tasks.append(self.parse_paper_details(session, full_url, title, semaphore))

		print(f"[NMI {year}] Found {len(tasks)} articles. Fetching details...")
		results = []
		for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=f"NMI {year}"):
			res = await coro
			if res:
				results.append(res)
		return results

	async def run(self, session):
		semaphore = asyncio.Semaphore(self.config.get("concurrency", 20))
		all_results = []

		if not self.year_urls:
			print("[NMI] No years provided. Use --years to specify years.")
			return [], self.stats

		for year, list_url in self.year_urls.items():
			year_results = await self.process_year(session, year, list_url, semaphore)
			all_results.extend(year_results)

		return all_results, self.stats
