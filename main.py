import asyncio
import yaml
import os
from src.core.engine import CrawlerEngine
from src.scrapers.icml import ICMLScraper


def load_config(path="config.yaml"):
	if not os.path.exists(path):
		raise FileNotFoundError(f"Config file not found at {path}")
	with open(path, "r", encoding="utf-8") as f:
		return yaml.safe_load(f)


async def main():
	print("🚀 Starting Paper-Tunneling...")
    
	# 1. 加载配置
	config = load_config()
    
	# 2. 初始化爬虫列表 (目前只有 ICML)
	scrapers = []
    
	# 这里未来可以加 if "neurips" in config['targets']...
	icml_scraper = ICMLScraper(config)
	scrapers.append(icml_scraper)
    
	# 3. 启动引擎
	engine = CrawlerEngine(scrapers, config)
	await engine.run()
    
	print("\n✅ Job Done! Check the 'results' folder.")


if __name__ == "__main__":
	# Windows 兼容性处理
	if os.name == 'nt':
		asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
	asyncio.run(main())
