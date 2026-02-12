# S2 论文下载器（替换旧脚本）

该脚本已按 `docs/S2` 改为纯 S2 接口实现：

- DOI 批量查询：`POST /graph/v1/paper/batch`（每次最多 500 条，最少调用次数）
- 标题查询：`GET /graph/v1/paper/search/match`
- 可选 PDF 下载（来自 `openAccessPdf.url`）
- 输出 `meta.json` + `papers.csv` + `failed.json`（批量失败项）

## 文件

```text
S17_pdf-download/
├── S17_pdf-download.py
├── input_title.csv
├── input_doi.csv
├── requirements.txt
└── README.md
```

## 用法

### 单篇

```bash
# DOI
python S17_pdf-download.py --api-key YOUR_KEY --doi "10.1038/s41586-021-03819-2"

# 标题
python S17_pdf-download.py --api-key YOUR_KEY --title "Attention is All You Need"

# 仅元数据，不下载 PDF
python S17_pdf-download.py --api-key YOUR_KEY --doi "10.1038/s41586-021-03819-2" --no-pdf
```

### 批量（CSV）

```bash
# 自动识别 doi/title 列
python S17_pdf-download.py --api-key YOUR_KEY --csv papers.csv -o ./batch_output

# 指定列
python S17_pdf-download.py --api-key YOUR_KEY --csv papers.csv --column DOI
python S17_pdf-download.py --api-key YOUR_KEY --csv papers.csv --column title
```

## 参数

- `--api-key` 必填，S2 key
- `--doi` 单篇 DOI
- `--title` 单篇标题
- `--csv` 批量输入
- `--column` 指定 CSV 列
- `--output/-o` 输出目录，默认 `./output`
- `--base-url` 默认 `https://ai4scholar.net`
- `--rate-limit-qps` 客户端限速，默认 `1`
- `--sleep` 标题查询间隔秒数，默认 `0.2`
- `--no-pdf` 跳过 PDF 下载

## CSV 示例

```csv
doi
10.1038/s41586-021-03819-2
10.1109/CVPR.2016.90
```

```csv
title
Attention is All You Need
Deep Residual Learning for Image Recognition
```
