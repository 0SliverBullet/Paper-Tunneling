# Paper-Tunneling ⚡️

**Paper-Tunneling** 是一个基于 Python 的异步高性能论文抓取工具，专为从 **ICML**, **NeurIPS**, **ICLR** 等顶级 AI 会议中挖掘特定领域的论文而设计。

它利用 `aiohttp` 和 `asyncio` 实现高并发爬取，支持关键词过滤（如 "Quantum", "QAOA", "GNN"），并将结果导出为 Markdown 格式，方便科研人员快速建立文献库。


## ✨ Demo

<p align="center">
  <img src="assets/demo.gif" alt="Paper-Tunneling Running Demo" width="800">
</p>



## 📂 目录结构

```text
Paper-Tunneling/
├── config.yaml          # 核心配置文件 (关键词, 年份, 会议)
├── main.py              # 启动入口
├── requirements.txt     # Python 依赖列表
├── src/                 # 源代码
└── results/             # 抓取结果输出目录
```

## 🛠️ 安装指南 (Installation)

### 1. 克隆仓库

```bash
git clone https://github.com/0SliverBullet/Paper-Tunneling.git
cd Paper-Tunneling
```

### 2. 环境配置

推荐使用 Conda 进行一键安装。

#### 方式 A：快速安装（推荐）

直接使用配置文件创建环境，无需手动安装依赖。

```bash
# 这会自动创建名为 paper-tunneling 的环境并安装所有依赖
conda env create -f environment.yml

# 激活环境
conda activate paper-tunneling
```

#### 方式 B：手动安装

如果你希望手动控制安装过程：

```bash
conda create -n paper-tunneling python=3.10
conda activate paper-tunneling
pip install -r requirements.txt
```

## ⚙️ 配置 (Configuration)

在运行之前，请检查根目录下的 config.yaml 文件，根据你的需求修改：

```yaml
# 搜索关键词 (支持多个)
keywords:
  - "quantum"
  - "optimization"

# 目标会议年份
years: [2023, 2024, 2025]

# 并发设置 (建议保持在 10-20 之间以避免 IP 被封)
concurrency: 20
```

## 🚀 运行 (Usage)

环境配置完成后，直接运行 main.py：

```bash
python main.py
```

### 查看结果

运行结束后，程序会在 results/ 目录下生成 Markdown 报告，例如 icml_quantum_papers.md。

## 📝 License

MIT License