import aiohttp
import os
from .exporter import MarkdownExporter


class CrawlerEngine:
	def __init__(self, scrapers, config):
		self.scrapers = scrapers
		self.config = config
		self.exporter = MarkdownExporter(config)

	async def run(self):
		# 创建统一的 Session，复用 TCP 连接
		async with aiohttp.ClientSession() as session:
			all_papers = []
			global_stats = {}

			for scraper in self.scrapers:
				print(f"--- Launching {scraper.conference_name} Scraper ---")
				papers, stats = await scraper.run(session)
				all_papers.extend(papers)
				global_stats[scraper.conference_name] = stats
            
			# 导出结果
			self.exporter.save(all_papers, global_stats)
