# 相关论文推荐

**接口路径：** `GET https://ai4scholar.net/pubmed/v1/paper/{pmid}/related`

## 接口信息

| 属性 | 值 |
|------|----|
| 接口路径 | `GET https://ai4scholar.net/pubmed/v1/paper/{pmid}/related` |
| 所属分类 | 相关论文 |
| Base URL | `https://ai4scholar.net` |

## 描述

获取与指定论文相关的其他论文

## 路径参数

| 参数名 | 类型 | 必填 |
|--------|------|------|
| [`pmid`](#pmid) | string | 是 |

### 参数详细说明

#### `pmid`

PubMed ID

## 查询参数

| 参数名 | 类型 | 必填 | 默认值 |
|--------|------|------|--------|
| [`limit`](#limit) | integer | 否 | `20` |

### 参数详细说明

#### `limit`

返回数量（默认 20）

## Python 示例

```python
import requests
import json

# 设置 API Key
API_KEY = "YOUR_API_KEY"

url = "https://ai4scholar.net/pubmed/v1/paper/{pmid}/related"
headers = {
    "x-api-key": API_KEY,
}

# 查询参数
params = {
    "limit": 20
}

# 发送请求
response = requests.get(url, headers=headers, params=params)

# 处理响应
result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))
```

## cURL 示例

```bash
curl -X GET "https://ai4scholar.net/pubmed/v1/paper/{pmid}/related" \
  -H "x-api-key: YOUR_API_KEY"
```

## 响应

### 200 获取成功

**响应示例：**

```json
{
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
| `data` | array[PubMedPaper] |  |

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

