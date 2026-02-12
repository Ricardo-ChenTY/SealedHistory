# 文献搜索

**接口路径：** `POST https://ai4scholar.net/pubmed/v1/paper/search`

## 接口信息

| 属性 | 值 |
|------|----|
| 接口路径 | `POST https://ai4scholar.net/pubmed/v1/paper/search` |
| 所属分类 | 论文搜索 |
| Base URL | `https://ai4scholar.net` |

## 描述

根据关键词搜索 PubMed 文献，支持多种过滤条件

## 请求体

```json
{
  "query": "COVID-19 vaccine efficacy",
  "limit": 10,
  "offset": 0,
  "sort": "relevance",
  "minDate": "2020/01/01",
  "maxDate": "2024/12/31"
}
```

## Python 示例

```python
import requests
import json

# 设置 API Key
API_KEY = "YOUR_API_KEY"

url = "https://ai4scholar.net/pubmed/v1/paper/search"
headers = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

# 请求体
data = {
    "query": "COVID-19 vaccine efficacy",
    "limit": 10,
    "offset": 0,
    "sort": "relevance",
    "minDate": "2020/01/01",
    "maxDate": "2024/12/31"
}

# 发送请求
response = requests.post(url, headers=headers, json=data)

# 处理响应
result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))
```

## cURL 示例

```bash
curl -X POST "https://ai4scholar.net/pubmed/v1/paper/search" \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"COVID-19 vaccine efficacy","limit":10,"offset":0,"sort":"relevance","minDate":"2020/01/01","maxDate":"2024/12/31"}'
```

## 响应

### 200 搜索成功

**响应示例：**

```json
{
  "total": 12345,
  "offset": 0,
  "data": [
    {
      "pmid": "38123456",
      "title": "COVID-19 vaccine efficacy: a systematic review",
      "abstract": "string",
      "authors": [
        "..."
      ],
      "journal": "Nature Medicine",
      "pubDate": "2024-01-15",
      "doi": "10.1038/s41591-024-12345",
      "keywords": [
        "..."
      ],
      "meshTerms": [
        "..."
      ]
    }
  ]
}
```

**顶层字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `total` | integer | 总结果数 |
| `offset` | integer | 当前偏移量 |
| `data` | array[PubMedPaper] | 论文列表 |

## 数据模型

以下是响应中使用的数据模型详细说明：

### PubMedPaper

**示例：**

```json
{
  "pmid": "38123456",
  "title": "COVID-19 vaccine efficacy: a systematic review",
  "abstract": "string",
  "authors": [
    {
      "name": "string",
      "affiliation": "string"
    }
  ],
  "journal": "Nature Medicine",
  "pubDate": "2024-01-15",
  "doi": "10.1038/s41591-024-12345",
  "keywords": [
    "string"
  ],
  "meshTerms": [
    "string"
  ]
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `pmid` | string | PubMed ID |
| `title` | string | 论文标题 |
| `abstract` | string | 摘要 |
| `authors` | array[object] | 作者列表 |
| `journal` | string | 期刊名称 |
| `pubDate` | string | 发表日期 |
| `doi` | string | DOI |
| `keywords` | array[string] | 关键词 |
| `meshTerms` | array[string] | MeSH 主题词 |

