# 论文查询自动补全建议

**接口路径：** `GET https://ai4scholar.net/graph/v1/paper/autocomplete`

## 接口信息

| 属性 | 值 |
|------|----|
| 接口路径 | `GET https://ai4scholar.net/graph/v1/paper/autocomplete` |
| 所属分类 | 论文数据 |
| Base URL | `https://ai4scholar.net` |

## 描述

支持交互式查询补全，返回匹配部分查询的论文的最少信息。

示例：
`https://ai4scholar.net/graph/v1/paper/autocomplete?query=semanti`

## 查询参数

| 参数名 | 类型 | 必填 | 默认值 |
|--------|------|------|--------|
| [`query`](#query) | string | 是 | - |

### 参数详细说明

#### `query`

纯文本部分查询字符串。将截断为前 100 个字符。

## Python 示例

```python
import requests
import json

# 设置 API Key
API_KEY = "YOUR_API_KEY"

url = "https://ai4scholar.net/graph/v1/paper/autocomplete"
headers = {
    "x-api-key": API_KEY,
}

# 查询参数
params = {
    "query": ""your_query""
}

# 发送请求
response = requests.get(url, headers=headers, params=params)

# 处理响应
result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))
```

## cURL 示例

```bash
curl -X GET "https://ai4scholar.net/graph/v1/paper/autocomplete" \
  -H "x-api-key: YOUR_API_KEY"
```

## 响应

### 200 包含默认或请求字段的论文批量数据

**响应示例：**

```json
{
  "matches": [
    {
      "id": "649def34f8be52c8b66281af98ae884c09aef38b",
      "title": "SciBERT: A Pretrained Language Model for Scientific Text",
      "authorsYear": "Beltagy et al., 2019"
    }
  ]
}
```

**顶层字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `matches` | array[Autocomplete Paper] |  |

### 400 错误的查询参数

**响应示例：**

```json
{
  "error": "Unrecognized or unsupported fields: [author.creditCardNumber, garbage]"
}
```

**顶层字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `error` | string | 根据具体情况，错误消息可能是以下任一种：  - `"Unrecognized or unsupported fields: [bad1, bad2, etc...]"`（无法识别或不支持的字段） - `"Unacceptable query params: [badK1=badV1, badK2=badV2, etc...}]"`（不可接受的查询参数） - `"Response would exceed maximum size...."`（响应超出最大大小限制）   - 当响应超过 10 MB 时会出现此错误。将提供将请求拆分为较小批次或使用 limit 和 offset 功能的建议。 - 自定义消息字符串 |

## 数据模型

以下是响应中使用的数据模型详细说明：

### PaperAutocomplete

**示例：**

```json
{
  "matches": [
    {
      "id": "649def34f8be52c8b66281af98ae884c09aef38b",
      "title": "SciBERT: A Pretrained Language Model for Scientific Text",
      "authorsYear": "Beltagy et al., 2019"
    }
  ]
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `matches` | array[Autocomplete Paper] |  |

### Autocomplete Paper

**示例：**

```json
{
  "id": "649def34f8be52c8b66281af98ae884c09aef38b",
  "title": "SciBERT: A Pretrained Language Model for Scientific Text",
  "authorsYear": "Beltagy et al., 2019"
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | string | 论文的主要唯一标识符 |
| `title` | string | 论文标题 |
| `authorsYear` | string | 论文作者和发表年份的摘要 |

### Error400

**示例：**

```json
{
  "error": "Unrecognized or unsupported fields: [author.creditCardNumber, garbage]"
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `error` | string | 根据具体情况，错误消息可能是以下任一种：  - `"Unrecognized or unsupported fields: [bad1, bad2, etc...]"`（无法识别或不支持的字段） - `"Unacceptable query params: [badK1=badV1, badK2=badV2, etc...}]"`（不可接受的查询参数） - `"Response would exceed maximum size...."`（响应超出最大大小限制）   - 当响应超过 10 MB 时会出现此错误。将提供将请求拆分为较小批次或使用 limit 和 offset 功能的建议。 - 自定义消息字符串 |

