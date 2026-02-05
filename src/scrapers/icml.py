import asyncio
from bs4 import BeautifulSoup
from tqdm import tqdm
from .base import BaseScraper


class ICMLScraper(BaseScraper):
	def __init__(self, config):
		super().__init__(config)
		self.conference_name = "ICML"
		self.base_url = "https://icml.cc"
		# 初始化统计数据
		self.stats = {year: {"scanned": 0, "found": 0} for year in self.config['years']}

	async def parse_paper_details(self, session, url, title, year, semaphore):
		async with semaphore:  # 限制并发
			html = await self.fetch(session, url)
			if not html:
				return None

			soup = BeautifulSoup(html, 'html.parser')
            
			# 1. 提取摘要
			abstract_text = ""
			abstract_div = soup.find(class_="abstract") or soup.find(id="abstract")
			if abstract_div:
				abstract_text = abstract_div.get_text(strip=True)
			else:
				# 备用方案：找 "Abstract" 标题后面
				abs_header = soup.find(lambda tag: tag.name in ["h3", "h4", "strong"] and "Abstract" in tag.get_text())
				if abs_header:
					next_node = abs_header.find_next_sibling()
					if next_node:
						abstract_text = next_node.get_text(strip=True)

			# 2. 提取作者
			authors_text = "Unknown Authors"

			# 2.1 优先从 citation_author 元数据获取
			meta_authors = [
				m.get("content", "").strip()
				for m in soup.find_all("meta", attrs={"name": "citation_author"})
				if m.get("content")
			]
			if meta_authors:
				authors_text = ", ".join(meta_authors)
			else:
				# 2.2 常见作者区域 class 名
				author_div = (
					soup.find(class_="authors")
					or soup.find(class_="author-block")
					or soup.find(class_="authors-list")
					or soup.find(class_="author")
				)
				if author_div:
					authors_text = author_div.get_text(" ", strip=True)
				else:
					# 2.3 兜底：从 JSON-LD 中提取 author
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

			# 3. 更新统计 (Scanned)
			self.stats[year]["scanned"] += 1

			# 4. 匹配检查
			if self.is_match(title, abstract_text):
				self.stats[year]["found"] += 1
				print(f"[ICML {year}] Found: {title[:50]}...")
				return {
					"source": "ICML",
					"year": year,
					"title": title,
					"authors": authors_text,
					"abstract": abstract_text,
					"url": url
				}
			return None

	async def process_year(self, session, year, semaphore):
		print(f"Scanning ICML {year} list...")
		list_url = f"{self.base_url}/virtual/{year}/papers.html"
        
		html = await self.fetch(session, list_url)
		if not html:
			print(f"Failed to load paper list for ICML {year}")
			return []

		soup = BeautifulSoup(html, 'html.parser')
		links = soup.find_all('a', href=True)
        
		tasks = []
		unique_urls = set()

		for link in links:
			href = link['href']
			# 过滤逻辑：只看 poster/oral/spotlight
			if f"/virtual/{year}/" in href and any(t in href for t in ["/poster/", "/oral/", "/spotlight/"]):
				full_url = self.base_url + href if href.startswith("/") else href
                
				if full_url in unique_urls:
					continue
				unique_urls.add(full_url)
                
				title = link.get_text(strip=True)
				if not title: continue
                
				tasks.append(self.parse_paper_details(session, full_url, title, year, semaphore))

		print(f"[ICML {year}] Found {len(tasks)} papers. Fetching details...")
		results = []
		for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc=f"ICML {year}"):
			res = await coro
			if res:
				results.append(res)
		return results

	async def run(self, session):
		# 创建信号量限制并发
		semaphore = asyncio.Semaphore(self.config.get('concurrency', 20))
		all_results = []
        
		for year in self.config['years']:
			year_results = await self.process_year(session, year, semaphore)
			all_results.extend(year_results)
            
		return all_results, self.stats
