import os
import time


class MarkdownExporter:
	def __init__(self, config):
		self.output_dir = config.get('output_dir', 'results')
		self.filename = config.get('output_filename', 'papers.md')
		self.keywords = config.get('keywords', [])
		self.years = config.get('years', [])
		self.conferences = config.get('conferences', [])
		self.journals = config.get('journals', [])
		self.journals_only = bool(self.journals) and not self.conferences
        
		if not os.path.exists(self.output_dir):
			os.makedirs(self.output_dir)

	def save(self, papers, stats):
		def _slug(text: str) -> str:
			return "-".join(text.lower().split()) if text else "all"

		keywords_folder = _slug(" ".join(self.keywords))

		# 按会议与年份分组输出
		grouped = {}
		for paper in papers:
			key = (paper['source'], paper['year'])
			grouped.setdefault(key, []).append(paper)

		for (conf, year), items in grouped.items():
			items.sort(key=lambda x: x['title'])
			folder = os.path.join(self.output_dir, keywords_folder, _slug(conf), str(year))
			os.makedirs(folder, exist_ok=True)
			filepath = os.path.join(folder, self.filename)

			with open(filepath, "w", encoding="utf-8") as f:
				f.write("# Paper-Tunneling Report\n")
				f.write(f"**Generated on:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
				f.write(f"**Keywords:** {', '.join(self.keywords)}\n")
				f.write(f"**Years:** {year}\n")
				label = "Journals" if self.journals_only else "Conferences"
				f.write(f"**{label}:** {_slug(conf)}\n\n")

				f.write(f"## {conf} {year}\n\n")
				for paper in items:
					f.write(f"### [{paper['title']}]({paper['url']})\n")
					f.write(f"**Authors:** {paper['authors']}\n\n")
					f.write(f"**Abstract:**\n{paper['abstract']}\n\n")
					f.write("---\n\n")

				f.write("\n### Statistics\n")
				conf_stats = stats.get(conf, {})
				data = conf_stats.get(year)
				if data:
					f.write(f"[{conf} {year}]: Scanned {data['scanned']} papers, {data['found']} found matching keywords.\n")

			print(f"📄 Report saved to: {filepath}")
