# 发布版本中的数据集列表

**接口路径：** `GET https://ai4scholar.net/datasets/v1/release/{release_id}`

## 接口信息

| 属性 | 值 |
|------|----|
| 接口路径 | `GET https://ai4scholar.net/datasets/v1/release/{release_id}` |
| 所属分类 | 发布数据 |
| Base URL | `https://ai4scholar.net` |

## 描述

描述特定发布版本的元数据，包括可用数据集列表

## 路径参数

| 参数名 | 类型 | 必填 |
|--------|------|------|
| [`release_id`](#release_id) | string | 是 |

### 参数详细说明

#### `release_id`

发布版本的 ID

## Python 示例

```python
import requests
import json

# 设置 API Key
API_KEY = "YOUR_API_KEY"

url = "https://ai4scholar.net/datasets/v1/release/{release_id}"
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
curl -X GET "https://ai4scholar.net/datasets/v1/release/{release_id}" \
  -H "x-api-key: YOUR_API_KEY"
```

## 响应

### 200 给定 ID 的发布版本内容

**响应示例：**

```json
{
  "release_id": "2022-01-17",
  "README": "Subject to the following terms ...",
  "datasets": [
    {
      "name": "papers",
      "description": "Core paper metadata",
      "README": "This dataset contains ..."
    }
  ]
}
```

**顶层字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `release_id` | string |  |
| `README` | string | 许可证和使用说明 |
| `datasets` | array[Dataset Summary] | 数据集元数据 |

## 数据模型

以下是响应中使用的数据模型详细说明：

### Release Metadata

**示例：**

```json
{
  "release_id": "2022-01-17",
  "README": "Subject to the following terms ...",
  "datasets": [
    {
      "name": "papers",
      "description": "Core paper metadata",
      "README": "This dataset contains ..."
    }
  ]
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `release_id` | string |  |
| `README` | string | 许可证和使用说明 |
| `datasets` | array[Dataset Summary] | 数据集元数据 |

### Dataset Summary

**示例：**

```json
{
  "name": "papers",
  "description": "Core paper metadata",
  "README": "This dataset contains ..."
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `name` | string | 数据集名称 |
| `description` | string | 数据集中数据的描述 |
| `README` | string | 数据集的文档和归属信息 |

