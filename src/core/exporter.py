import os
import time


class MarkdownExporter:
	def __init__(self, config):
		self.output_dir = config.get('output_dir', 'results')
		self.filename = config.get('output_filename', 'papers.md')
		self.keywords = config.get('keywords', [])
		self.years = config.get('years', [])
		self.conferences = config.get('conferences', [])
        
		if not os.path.exists(self.output_dir):
			os.makedirs(self.output_dir)

	def save(self, papers, stats):
		filepath = os.path.join(self.output_dir, self.filename)
        
		# 按年份降序排序
		papers.sort(key=lambda x: x['year'], reverse=True)
        
		with open(filepath, "w", encoding="utf-8") as f:
			f.write(f"# Paper-Tunneling Report\n")
			f.write(f"**Generated on:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
			f.write(f"**Keywords:** {', '.join(self.keywords)}\n\n")
			if self.years:
				f.write(f"**Years:** {', '.join(str(y) for y in self.years)}\n")
			if self.conferences:
				f.write(f"**Conferences:** {', '.join(self.conferences)}\n")
			f.write("\n")
            
			current_year = None
			for paper in papers:
				if paper['year'] != current_year:
					current_year = paper['year']
					f.write(f"## {paper['source']} {current_year}\n\n")
                
				f.write(f"### [{paper['title']}]({paper['url']})\n")
				f.write(f"**Authors:** {paper['authors']}\n\n")
				f.write(f"**Abstract:**\n{paper['abstract']}\n\n")
				f.write("---\n\n")
            
			# 统计信息 (最后三行)
			f.write("\n### Statistics\n")
			# 这里我们需要把不同会议的统计合并展示，或者按会议展示
			# 根据你的需求，ICML 的统计如下：
			for conf_name, conf_stats in stats.items():
				for year, data in conf_stats.items():
					f.write(f"[{conf_name} {year}]: Scanned {data['scanned']} papers, {data['found']} found matching keywords.\n")
        
		print(f"📄 Report saved to: {filepath}")
