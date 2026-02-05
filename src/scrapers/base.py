import asyncio
import re


class BaseScraper:
	def __init__(self, config):
		self.config = config
		self.keywords = config.get('keywords', [])
		# 编译正则，提高匹配效率
		self.keyword_patterns = [re.compile(re.escape(k), re.IGNORECASE) for k in self.keywords]
		self.conference_name = "Base"
        
	async def fetch(self, session, url):
		"""通用的 HTTP GET 请求"""
		try:
			async with session.get(url, timeout=self.config.get('timeout', 30)) as response:
				if response.status == 200:
					return await response.text()
				return None
		except Exception as e:
			print(f"Error fetching {url}: {e}")
			return None

	def is_match(self, title, abstract):
		"""检查标题或摘要是否命中任意关键词"""
		for pattern in self.keyword_patterns:
			if pattern.search(title) or pattern.search(abstract):
				return True
		return False

	async def run(self, session):
		"""子类必须实现此方法"""
		raise NotImplementedError
