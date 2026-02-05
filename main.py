import asyncio
import yaml
import os
import sys
import argparse
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from src.core.engine import CrawlerEngine
from src.scrapers.icml import ICMLScraper
from src.scrapers.neurips import NeurIPSScraper
from src.scrapers.iclr import ICLRScraper
from src.scrapers.nature_machine_intelligence import NatureMachineIntelligenceScraper


def load_config(path="config.yaml"):
	if not os.path.exists(path):
		raise FileNotFoundError(f"Config file not found at {path}")
	with open(path, "r", encoding="utf-8") as f:
		return yaml.safe_load(f)


def parse_args():
	parser = argparse.ArgumentParser(description="Paper-Tunneling CLI")
	parser.add_argument("--keywords", nargs="+", help="关键词列表，例如: quantum qaoa")
	parser.add_argument("--years", nargs="+", type=int, help="年份列表，例如: 2023 2024 2025")
	parser.add_argument("--conferences", nargs="+", help="会议列表，例如: icml")
	parser.add_argument("--journals", nargs="+", help="期刊列表，例如: nmi")
	parser.add_argument("--concurrency", type=int, help="并发请求数，例如: 5")
	return parser.parse_args()


def _sanitize_token(token: str) -> str:
	allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-_+")
	return "".join(ch for ch in token.lower() if ch in allowed)



def build_output_filename(config):
	confs = config.get("conferences") or []
	journals = config.get("journals") or []
	if not confs and journals:
		confs = journals
	if not confs:
		confs = ["papers"]
	keywords = config.get("keywords") or ["all"]
	years = config.get("years") or ["all"]

	conf_part = "_".join(_sanitize_token(c) for c in confs)
	keyword_part = "_".join(_sanitize_token(k) for k in keywords)
	year_part = "_".join(str(y) for y in years)
	return f"{conf_part}_{keyword_part}_{year_part}.md"


async def main():
	print("🚀 Starting Paper-Tunneling...")
    
	# 1. 加载配置
	config = load_config()
	args = parse_args()

	# 1.1 CLI 覆盖配置
	cli_override = False
	if args.keywords:
		config["keywords"] = args.keywords
		cli_override = True
	if args.years:
		config["years"] = args.years
		cli_override = True
	if args.conferences:
		config["conferences"] = [c.lower() for c in args.conferences]
		cli_override = True
	if args.journals:
		config["journals"] = [j.lower() for j in args.journals]
		cli_override = True
	if args.concurrency is not None:
		config["concurrency"] = args.concurrency
		cli_override = True

	if cli_override:
		config["output_filename"] = build_output_filename(config)

	conferences = config.get("conferences")
	journals = config.get("journals") or []

	# 仅指定期刊时，不默认启用会议
	if conferences is None and journals:
		conferences = []
	if conferences is None:
		conferences = ["icml"]
	conference_aliases = {
		"natmachintell": "nmi",
		"nature-machine-intelligence": "nmi",
		"nature_machine_intelligence": "nmi",
		"nmi": "nmi",
	}
	conferences = [conference_aliases.get(c, c) for c in conferences]
	journals = [conference_aliases.get(j, j) for j in journals]
	config["conferences"] = conferences
	config["journals"] = journals
    
	# 2. 初始化爬虫列表 (目前只有 ICML)
	scrapers = []
    
	if "icml" in conferences:
		icml_scraper = ICMLScraper(config)
		scrapers.append(icml_scraper)
	if "neurips" in conferences:
		neurips_scraper = NeurIPSScraper(config)
		scrapers.append(neurips_scraper)
	if "iclr" in conferences:
		iclr_scraper = ICLRScraper(config)
		scrapers.append(iclr_scraper)
	if "nmi" in conferences or "nmi" in journals:
		nmi_scraper = NatureMachineIntelligenceScraper(config)
		scrapers.append(nmi_scraper)

	if not scrapers:
		raise ValueError("No valid conferences selected. Currently supported: icml, neurips, iclr, nmi")
    
	# 3. 启动引擎
	engine = CrawlerEngine(scrapers, config)
	await engine.run()
    
	print("\n✅ Job Done! Check the 'results' folder.")


if __name__ == "__main__":
	# Windows 兼容性处理
	if os.name == 'nt':
		asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
	asyncio.run(main())
