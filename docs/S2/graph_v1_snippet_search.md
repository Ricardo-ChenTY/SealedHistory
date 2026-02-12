# 文本片段搜索

**接口路径：** `GET https://ai4scholar.net/graph/v1/snippet/search`

## 接口信息

| 属性 | 值 |
|------|----|
| 接口路径 | `GET https://ai4scholar.net/graph/v1/snippet/search` |
| 所属分类 | 文本片段 |
| Base URL | `https://ai4scholar.net` |

## 描述

返回与查询最匹配的文本片段。文本片段是约 500 词的摘录，来自论文的标题、摘要和正文，但不包括图表标题和参考文献。
将首先返回排名最高的片段，以及关于该片段所在论文的一些基本数据。
示例：

• `https://ai4scholar.net/graph/v1/snippet/search?query=The literature graph is a property graph with directed edges&limit=1`

• 返回排名最高的单个匹配片段。
• 每个片段包含 text、snippetKind、section、注释数据和 score。以及来源论文的以下数据：corpusId、title、authors 和 openAccessInfo。



限制：

• 必须包含查询参数。
• 如果不设置 limit，将自动返回 10 条结果。
• 允许的最大 limit 为 1000。



## 查询参数

| 参数名 | 类型 | 必填 | 默认值 |
|--------|------|------|--------|
| [`fields`](#fields) | string | 否 | - |
| [`paperIds`](#paperIds) | string | 否 | - |
| [`authors`](#authors) | string | 否 | - |
| [`minCitationCount`](#minCitationCount) | string | 否 | - |
| [`insertedBefore`](#insertedBefore) | string | 否 | - |
| [`publicationDateOrYear`](#publicationDateOrYear) | string | 否 | - |
| [`year`](#year) | string | 否 | - |
| [`venue`](#venue) | string | 否 | - |
| [`fieldsOfStudy`](#fieldsOfStudy) | string | 否 | - |
| [`query`](#query) | string | 是 | - |
| [`limit`](#limit) | integer | 否 | `10` |

### 参数详细说明

#### `fields`

以逗号分隔的字段列表，用于指定每个片段元素返回的字段。

论文信息和分数始终返回。使用此 `fields` 参数可以指定在 snippet 部分（参见响应架构）中返回哪些字段。

示例：

• `fields=snippet.text`：只返回 snippet 部分的 `text` 字段
• `fields=snippet.text,snippet.snippetKind`：只返回 snippet 部分的 `text` 和 `snippetKind` 字段
• `fields=snippet.annotations.sentences`：只返回 snippet 部分的句子注释


通常，可以使用点号标识嵌套字段（如上例所示）。

但并非响应架构中的所有字段都可以使用此 `fields` 参数标识。
例如，无法选择 `snippet.snippetOffset` 中的具体字段 - 只能获取包含所有字段的完整 snippet offset，或完全不获取。
也无法提供 `paper` 或 `score` 或 `paper` 下的任何内容，因为这些始终提供。

如果尝试标识不支持的字段，将收到包含相关字段名的错误。例如：

`Unrecognized or unsupported fields: [paper]`

如果不指定 fields 参数，将获得 snippet 部分的默认字段集。默认字段包括：
- `snippet.text`
- `snippet.snippetKind`
- `snippet.section`
- `snippet.snippetOffset`（包含嵌套的 `start` 和 `end`）
- `snippet.annotations.refMentions`（每个元素包含嵌套的 `start`、`end` 和 `matchedPaperCorpusId`）
- `snippet.annotations.sentences`（每个元素包含嵌套的 `start` 和 `end`）

#### `paperIds`

限制结果为来自特定论文的片段。要指定论文，请提供逗号分隔的 ID 列表。最多可提供约 100 个 ID。

支持以下类型的 ID：

• `<sha>` - Semantic Scholar ID，例如 `649def34f8be52c8b66281af98ae884c09aef38b`
• `CorpusId:<id>` - Semantic Scholar 数字 ID，例如 `CorpusId:215416146`
• `DOI:<doi>` - 数字对象标识符，例如 `DOI:10.18653/v1/N18-3011`
• `ARXIV:<id>` - arXiv，例如 `ARXIV:2106.15928`
• `MAG:<id>` - Microsoft Academic Graph，例如 `MAG:112218234`
• `ACL:<id>` - Association for Computational Linguistics，例如 `ACL:W12-3903`
• `PMID:<id>` - PubMed/Medline，例如 `PMID:19872477`
• `PMCID:<id>` - PubMed Central，例如 `PMCID:2323736`
• `URL:<url>` - 以下网站的 URL，例如 `URL:https://arxiv.org/abs/2106.15928v1`


可识别以下网站的 URL：

• semanticscholar.org
• arxiv.org
• aclweb.org
• acm.org
• biorxiv.org


#### `authors`

限制结果为具有匹配作者姓名的论文，格式为逗号分隔的列表（`...?authors=name1,name2,...`）。
搜索条件是「模糊」的，因此接近的匹配也会返回结果。


示例：`galileo,kepler` 将返回同时包含与 galileo 相似的作者和与 kepler 相似的作者作为共同作者的论文。
此查询还会匹配模糊变体，如 keppler 和 Kepler（默认最大编辑距离为 2）。

重要：多个作者姓名使用 AND 逻辑组合，意味着结果必须包含所有指定的作者。
添加更多作者会缩小结果范围，而不是扩大。
要搜索任一作者的论文（OR 逻辑），请为每个作者姓名执行单独搜索。
作者筛选器的最大数量默认为 `10`，如果提供超过 10 个将返回 HTTP 400（错误请求）。

#### `minCitationCount`

限制结果仅包含引用数不低于指定值的论文。


示例：
`minCitationCount=200`

#### `insertedBefore`

限制结果为在指定日期之前插入索引的论文片段（不包括在指定日期插入的内容）。

可接受的格式：YYYY-MM-DD、YYYY-MM、YYYY

#### `publicationDateOrYear`

限制结果为指定的发表日期或年份范围（包含边界）。接受格式 `<起始日期>:<结束日期>`，每个日期为 `YYYY-MM-DD` 格式。


每个日期都是可选的，支持特定日期、固定范围或开放范围。此外，还支持前缀简写，如 `2020-06` 匹配 2020 年 6 月的所有日期。


并非所有论文都有具体日期，因此使用此筛选器返回的某些记录的 `publicationDate` 可能为 `null`。但 `year` 始终存在。
对于没有具体发表日期的记录，将被视为在其发表年份的 1 月 1 日发表。


示例：

• `2019-03-05` 2019年3月5日
• `2019-03` 2019年3月期间
• `2019` 2019年期间
• `2016-03-05:2020-06-06` 2016年3月5日至2020年6月6日之间
• `1981-08-25:` 1981年8月25日及之后
• `:2015-01` 2015年1月31日及之前
• `2015:2020` 2015年1月1日至2020年12月31日之间


#### `year`

限制结果为指定的发表年份或年份范围（包含边界）。


示例：

• `2019` 2019年
• `2016-2020` 2016年至2020年
• `2010-` 2010年及之后
• `-2015` 2015年及之前


#### `venue`

限制结果为在指定期刊/会议发表的论文，格式为逗号分隔的列表。
输入也可以是 ISO4 缩写。
示例包括：

• Nature
• New England Journal of Medicine
• Radiology
• N. Engl. J. Med.


示例：`Nature,Radiology` 将返回来自 Nature 和/或 Radiology 的论文。

#### `fieldsOfStudy`

限制结果为指定研究领域的论文，格式为逗号分隔的列表：

• Computer Science（计算机科学）
• Medicine（医学）
• Chemistry（化学）
• Biology（生物学）
• Materials Science（材料科学）
• Physics（物理学）
• Geology（地质学）
• Psychology（心理学）
• Art（艺术）
• History（历史）
• Geography（地理）
• Sociology（社会学）
• Business（商业）
• Political Science（政治学）
• Economics（经济学）
• Philosophy（哲学）
• Mathematics（数学）
• Engineering（工程学）
• Environmental Science（环境科学）
• Agricultural and Food Sciences（农业与食品科学）
• Education（教育）
• Law（法律）
• Linguistics（语言学）


示例：`Physics,Mathematics` 将返回研究领域包含 Physics 或 Mathematics 的论文。

#### `query`

纯文本搜索查询字符串。
* 不支持特殊查询语法。

#### `limit`

返回结果的最大数量。
必须 <= 1000

## Python 示例

```python
import requests
import json

# 设置 API Key
API_KEY = "YOUR_API_KEY"

url = "https://ai4scholar.net/graph/v1/snippet/search"
headers = {
    "x-api-key": API_KEY,
}

# 查询参数
params = {
    "fields": ""your_fields"",
    "paperIds": ""your_paperIds"",
    "authors": ""your_authors"",
    "minCitationCount": ""your_minCitationCount"",
    "insertedBefore": ""your_insertedBefore""
}

# 发送请求
response = requests.get(url, headers=headers, params=params)

# 处理响应
result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))
```

## cURL 示例

```bash
curl -X GET "https://ai4scholar.net/graph/v1/snippet/search" \
  -H "x-api-key: YOUR_API_KEY"
```

## 响应

### 200 最佳片段匹配（包含默认字段）

**响应示例：**

```json
{
  "data": [
    {
      "snippet": "...",
      "score": 0.561970777028496,
      "paper": "..."
    }
  ],
  "retrievalVersion": "string"
}
```

**顶层字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `data` | array[Snippet Match] |  |
| `retrievalVersion` | string | 我们用于获取结果的检索方法的粗略表示。如果我们更改获取结果的方式，通常会更新此值。注意：相同的 retrievalVersion 值不能保证在不同时间对相同查询获得相同结果，不同的 retrievalVersion 值也不一定意味着会获得不同结果。 |

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

### SnippetMatch

**示例：**

```json
{
  "data": [
    {
      "snippet": "...",
      "score": 0.561970777028496,
      "paper": "..."
    }
  ],
  "retrievalVersion": "string"
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `data` | array[Snippet Match] |  |
| `retrievalVersion` | string | 我们用于获取结果的检索方法的粗略表示。如果我们更改获取结果的方式，通常会更新此值。注意：相同的 retrievalVersion 值不能保证在不同时间对相同查询获得相同结果，不同的 retrievalVersion 值也不一定意味着会获得不同结果。 |

### Snippet Match

**示例：**

```json
{
  "snippet": {
    "text": "In this paper, we discuss the construction of a graph, providing a symbolic representation of the scientific literature. We describe deployed models for identifying authors, references and entities in the paper text, and provide experimental results to evaluate the performance of each model. \n\nThree research directions follow from this work and other similar projects, e.g., Hahn-Powell et al. (2017); Wu et al. (2014): i) improving quality and enriching content of the literature graph (e.g., ontology matching and knowledge base population). ii) aggregating domain-specific extractions across many papers to enable a better understanding of the literature as a whole (e.g., identifying demographic biases in clinical trial participants and summarizing empirical results on important tasks). iii) exploring the literature via natural language interfaces. \n\nIn order to help future research efforts, we make the following resources publicly available: metadata for over 20 million papers,10 meaningful citations dataset,11 models for figure and table extraction,12 models for predicting citations in a paper draft 13 and models for extracting paper metadata,14 among other resources.",
    "snippetKind": "body",
    "section": "Conclusion and Future Work",
    "snippetOffset": {
      "start": 24506,
      "end": 25694
    },
    "annotations": {
      "sentences": "...",
      "refMentions": "..."
    }
  },
  "score": 0.561970777028496,
  "paper": {
    "corpusId": "19170988",
    "title": "Construction of the Literature Graph in Semantic Scholar",
    "authors": [
      [
        "Bridger Waleed Ammar",
        "Dirk Groeneveld",
        "Chandra Bhagavatula",
        "Iz Beltagy",
        "Miles Crawford",
        "Doug Downey",
        "Jason Dunkelberger",
        "Ahmed Elgohary",
        "Sergey Feldman",
        "Vu A. Ha",
        "Rodney Michael Kinney",
        "Sebastian Kohlmeier",
        "Kyle Lo",
        "Tyler C. Murray",
        "Hsu-Han Ooi",
        "Matthew E. Peters",
        "Joanna L. Power",
        "Sam Skjonsberg",
        "Lucy Lu Wang",
        "Christopher Wilhelm",
        "Zheng Yuan",
        "Madeleine van Zuylen",
        "Oren Etzioni"
      ]
    ],
    "openAccessInfo": {
      "license": "CCBY",
      "status": "HYBRID",
      "disclaimer": "Notice: This snippet is extracted from the open access paper or abstract available at https://arxiv.org/abs/1805.02262, which is subject to the license by the author or copyright owner provided with this content. Please go to the source to verify the license and copyright information for your use."
    }
  }
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `snippet` | snippet |  |
| `score` | number |  |
| `paper` | paper |  |

### snippet

**示例：**

```json
{
  "text": "In this paper, we discuss the construction of a graph, providing a symbolic representation of the scientific literature. We describe deployed models for identifying authors, references and entities in the paper text, and provide experimental results to evaluate the performance of each model. \n\nThree research directions follow from this work and other similar projects, e.g., Hahn-Powell et al. (2017); Wu et al. (2014): i) improving quality and enriching content of the literature graph (e.g., ontology matching and knowledge base population). ii) aggregating domain-specific extractions across many papers to enable a better understanding of the literature as a whole (e.g., identifying demographic biases in clinical trial participants and summarizing empirical results on important tasks). iii) exploring the literature via natural language interfaces. \n\nIn order to help future research efforts, we make the following resources publicly available: metadata for over 20 million papers,10 meaningful citations dataset,11 models for figure and table extraction,12 models for predicting citations in a paper draft 13 and models for extracting paper metadata,14 among other resources.",
  "snippetKind": "body",
  "section": "Conclusion and Future Work",
  "snippetOffset": {
    "start": 24506,
    "end": 25694
  },
  "annotations": {
    "sentences": [
      "..."
    ],
    "refMentions": [
      "..."
    ]
  }
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `text` | string | 与查询相关的论文直接引用或片段 |
| `snippetKind` | string | 片段所在位置，选项有：标题、摘要或正文 |
| `section` | string | 仅适用于正文片段，指片段所在论文章节 |
| `snippetOffset` | object | 片段在论文中的位置 |
| `annotations` | annotations |  |

### annotations

**示例：**

```json
{
  "sentences": [
    {
      "start": 0,
      "end": 120
    }
  ],
  "refMentions": [
    {
      "start": 377,
      "end": 402,
      "matchedPaperCorpusId": "7377848"
    }
  ]
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `sentences` | array[sentence] |  |
| `refMentions` | array[refMention] |  |

### sentence

**示例：**

```json
{
  "start": 0,
  "end": 120
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `start` | integer |  |
| `end` | integer |  |

### refMention

**示例：**

```json
{
  "start": 377,
  "end": 402,
  "matchedPaperCorpusId": "7377848"
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `start` | integer |  |
| `end` | integer |  |
| `matchedPaperCorpusId` | string |  |

### paper

**示例：**

```json
{
  "corpusId": "19170988",
  "title": "Construction of the Literature Graph in Semantic Scholar",
  "authors": [
    [
      "Bridger Waleed Ammar",
      "Dirk Groeneveld",
      "Chandra Bhagavatula",
      "Iz Beltagy",
      "Miles Crawford",
      "Doug Downey",
      "Jason Dunkelberger",
      "Ahmed Elgohary",
      "Sergey Feldman",
      "Vu A. Ha",
      "Rodney Michael Kinney",
      "Sebastian Kohlmeier",
      "Kyle Lo",
      "Tyler C. Murray",
      "Hsu-Han Ooi",
      "Matthew E. Peters",
      "Joanna L. Power",
      "Sam Skjonsberg",
      "Lucy Lu Wang",
      "Christopher Wilhelm",
      "Zheng Yuan",
      "Madeleine van Zuylen",
      "Oren Etzioni"
    ]
  ],
  "openAccessInfo": {
    "license": "CCBY",
    "status": "HYBRID",
    "disclaimer": "Notice: This snippet is extracted from the open access paper or abstract available at https://arxiv.org/abs/1805.02262, which is subject to the license by the author or copyright owner provided with this content. Please go to the source to verify the license and copyright information for your use."
  }
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `corpusId` | string | Semantic Scholar 论文的次要唯一标识符 |
| `title` | string | 论文标题 |
| `authors` | array[string] |  |
| `openAccessInfo` | openAccessInfo |  |

### openAccessInfo

**示例：**

```json
{
  "license": "CCBY",
  "status": "HYBRID",
  "disclaimer": "Notice: This snippet is extracted from the open access paper or abstract available at https://arxiv.org/abs/1805.02262, which is subject to the license by the author or copyright owner provided with this content. Please go to the source to verify the license and copyright information for your use."
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `license` | string | 论文的许可证 |
| `status` | string | 论文状态（开放获取类型 https://en.wikipedia.org/wiki/Open_access#Colour_naming_system） |
| `disclaimer` | string | 关于本论文开放获取使用的免责声明 |

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

