# 可用发布版本列表

**接口路径：** `GET https://ai4scholar.net/datasets/v1/release/`

## 接口信息

| 属性 | 值 |
|------|----|
| 接口路径 | `GET https://ai4scholar.net/datasets/v1/release/` |
| 所属分类 | 发布数据 |
| Base URL | `https://ai4scholar.net` |

## 描述

发布版本通过日期戳标识，例如 "2023-08-01"。每个发布版本包含每个数据集的完整数据。

## Python 示例

```python
import requests
import json

# 设置 API Key
API_KEY = "YOUR_API_KEY"

url = "https://ai4scholar.net/datasets/v1/release/"
headers = {
    "x-api-key": API_KEY,
}

# 发送请求
response = requests.get(url, headers=headers)

# 处理响应
result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))
```

## cURL 示例

```bash
curl -X GET "https://ai4scholar.net/datasets/v1/release/" \
  -H "x-api-key: YOUR_API_KEY"
```

## 响应

### 200 可用发布版本列表

**响应示例：**

```json
[
  "2022-01-17"
]
```

