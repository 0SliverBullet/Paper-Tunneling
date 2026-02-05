
import asyncio
from bs4 import BeautifulSoup
from tqdm import tqdm
from .base import BaseScraper


class NeurIPSScraper(BaseScraper):
	def __init__(self, config):
		super().__init__(config)
		self.conference_name = "NeurIPS"
		self.base_url = "https://neurips.cc"
		self.stats = {year: {"scanned": 0, "found": 0} for year in self.config["years"]}

	def _build_list_urls(self, year):
		if year == 2025:
			return [
				f"{self.base_url}/virtual/2025/loc/san-diego/papers.html",
				f"{self.base_url}/virtual/2025/loc/mexico-city/papers.html",
			]
		return [f"{self.base_url}/virtual/{year}/papers.html"]

	async def parse_paper_details(self, session, url, title, year, semaphore):
		async with semaphore:
			html = await self.fetch(session, url)
			if not html:
				return None

			soup = BeautifulSoup(html, "html.parser")
			# title (fallback to page title if missing)
			title_tag = None
			if not title:
				title_tag = soup.find("h4") or soup.find("h2") or soup.find("h3")
				if title_tag:
					title = title_tag.get_text(strip=True)

			# authors
			authors_text = "Unknown Authors"

			def _clean_authors_text(text: str) -> str:
				for label in ["Poster", "OpenReview", "Slides", "Video", "PDF"]:
					text = text.replace(label, "")
				text = " ".join(text.split())
				if "·" in text:
					parts = [p.strip() for p in text.split("·") if p.strip()]
					return ", ".join(parts)
				return text

			# 1) meta citation_author
			meta_authors = [
				m.get("content", "").strip()
				for m in soup.find_all("meta", attrs={"name": "citation_author"})
				if m.get("content")
			]
			if meta_authors:
				authors_text = ", ".join(meta_authors)
			else:
				# 2) JSON-LD authors
				for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
					try:
						import json
						data = json.loads(script.string or "{}")
						authors = data.get("author")
						if isinstance(authors, list):
							names = []
							for a in authors:
								name = a.get("name") if isinstance(a, dict) else None
								if name:
									names.append(name)
							if names:
								authors_text = ", ".join(names)
								break
						elif isinstance(authors, dict) and authors.get("name"):
							authors_text = authors.get("name")
							break
					except Exception:
						continue
				if authors_text == "Unknown Authors":
					# 3) 常见作者区 class
					author_p = soup.find("p", class_="authors") or soup.find("p", class_="author")
					if author_p:
						authors_text = author_p.get_text(" ", strip=True)
					else:
						# 4) 标题后作者行（用“·”分隔）
						if title_tag:
							steps = 0
							for sib in title_tag.find_all_next():
								if sib.name in ["h1", "h2", "h3", "h4"]:
									break
								text = sib.get_text(" ", strip=True)
								if "·" in text:
									authors_text = _clean_authors_text(text)
									break
								steps += 1
								if steps >= 6:
									break

			# abstract
			abstract_text = ""
			abs_header = soup.find(lambda tag: tag.name in ["h4", "h3", "strong"] and "Abstract" in tag.get_text())
			if abs_header:
				next_node = abs_header.find_next_sibling()
				if next_node:
					abstract_text = next_node.get_text(strip=True)
			if not abstract_text:
				abstract_div = soup.find(id="abstract") or soup.find(class_="abstract")
				if abstract_div:
					abstract_text = abstract_div.get_text(strip=True)

			# stats
			self.stats[year]["scanned"] += 1
			if self.is_match(title, abstract_text):
				self.stats[year]["found"] += 1
				print(f"[NeurIPS {year}] Found: {title[:50]}...")
				return {
					"source": "NeurIPS",
					"year": year,
					"title": title,
					"authors": authors_text,
					"abstract": abstract_text,
					"url": url,
				}
			return None

	async def process_year(self, session, year, semaphore):
		print(f"Scanning NeurIPS {year} list...")
		list_urls = self._build_list_urls(year)

		tasks = []
		unique_urls = set()

		for list_url in list_urls:
			html = await self.fetch(session, list_url)
			if not html:
				print(f"Failed to load paper list for NeurIPS {year}: {list_url}")
				continue

			soup = BeautifulSoup(html, "html.parser")
			links = soup.find_all("a", href=True)

			for link in links:
				href = link["href"]
				# 过滤逻辑：只看 poster/oral/spotlight
				if f"/virtual/{year}/" in href and any(t in href for t in ["/poster/", "/oral/", "/spotlight/"]):
					full_url = href
					if href.startswith("/"):
						full_url = self.base_url + href

					if full_url in unique_urls:
						continue
					unique_urls.add(full_url)

					title = link.get_text(strip=True)
					if not title:
						continue

					tasks.append(self.parse_paper_details(session, full_url, title, year, semaphore))

		print(f"[NeurIPS {year}] Found {len(tasks)} papers. Fetching details...")
		results = []
		for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=f"NeurIPS {year}"):
			res = await coro
			if res:
				results.append(res)
		return results

	async def run(self, session):
		semaphore = asyncio.Semaphore(self.config.get("concurrency", 20))
		all_results = []

		for year in self.config["years"]:
			year_results = await self.process_year(session, year, semaphore)
			all_results.extend(year_results)

		return all_results, self.stats

