# 作者论文详细信息

**接口路径：** `GET https://ai4scholar.net/graph/v1/author/{author_id}/papers`

## 接口信息

| 属性 | 值 |
|------|----|
| 接口路径 | `GET https://ai4scholar.net/graph/v1/author/{author_id}/papers` |
| 所属分类 | 作者数据 |
| Base URL | `https://ai4scholar.net` |

## 描述

分批获取作者的论文。
仅检索批次中论文的最近 10,000 条引用/参考文献。
要获取论文的完整引用集，请使用 /paper/{paper_id}/citations 接口。

示例：

• `https://ai4scholar.net/graph/v1/author/1741101/papers`

• 返回 offset=0，data 是前 100 篇论文的列表。
• 每篇论文包含 paperId 和 title。

• `https://ai4scholar.net/graph/v1/author/1741101/papers?fields=url,year,authors&limit=2`

• 返回 offset=0, next=2，data 是 2 篇论文的列表。
• 每篇论文包含 paperId、url、year 和作者列表。
• 每个作者包含 authorId 和 name。

• `https://ai4scholar.net/graph/v1/author/1741101/papers?fields=citations.authors&offset=260`

• 返回 offset=260，data 是最后 4 篇论文的列表。
• 每篇论文包含 paperId 和引用列表。
• 每条引用包含 paperId 和作者列表。
• 每个作者包含 authorId 和 name。



## 路径参数

| 参数名 | 类型 | 必填 |
|--------|------|------|
| [`author_id`](#author_id) | string | 是 |

## 查询参数

| 参数名 | 类型 | 必填 | 默认值 |
|--------|------|------|--------|
| [`publicationDateOrYear`](#publicationDateOrYear) | string | 否 | - |
| [`offset`](#offset) | integer | 否 | `0` |
| [`limit`](#limit) | integer | 否 | `100` |
| [`fields`](#fields) | string | 否 | - |

### 参数详细说明

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


#### `offset`

用于分页。返回结果列表时，从列表中此位置的元素开始。

#### `limit`

返回结果的最大数量。
必须 <= 1000

#### `fields`

以逗号分隔的返回字段列表。请参阅下方响应架构中 `data` 数组的内容，了解所有可返回的字段。
`paperId` 字段始终返回。如果省略 fields 参数，则仅返回 `paperId` 和 `title`。要获取更多引用或参考文献，请使用 `limit=` 减少批次中的论文数量。
使用点号（"."）表示 `citations` 和 `references` 的子字段。
示例：

• `fields=title,fieldsOfStudy,references`
• `fields=abstract,citations.url,citations.venue`


## Python 示例

```python
import requests
import json

# 设置 API Key
API_KEY = "YOUR_API_KEY"

url = "https://ai4scholar.net/graph/v1/author/{author_id}/papers"
headers = {
    "x-api-key": API_KEY,
}

# 查询参数
params = {
    "publicationDateOrYear": ""your_publicationDateOrYear"",
    "offset": ""your_offset"",
    "limit": 100,
    "fields": ""your_fields""
}

# 发送请求
response = requests.get(url, headers=headers, params=params)

# 处理响应
result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))
```

## cURL 示例

```bash
curl -X GET "https://ai4scholar.net/graph/v1/author/{author_id}/papers" \
  -H "x-api-key: YOUR_API_KEY"
```

## 响应

### 200 包含默认或请求字段的论文列表

**响应示例：**

```json
{
  "offset": 0,
  "next": 0,
  "data": [
    {
      "paperId": "5c5751d45e298cea054f32b392c12c61027d2fe7",
      "corpusId": 215416146,
      "externalIds": {
        "MAG": "3015453090",
        "DBLP": "conf/acl/LoWNKW20",
        "ACL": "2020.acl-main.447",
        "DOI": "10.18653/V1/2020.ACL-MAIN.447",
        "CorpusId": 215416146
      },
      "url": "https://www.semanticscholar.org/paper/5c5751d45e298cea054f32b392c12c61027d2fe7",
      "title": "Construction of the Literature Graph in Semantic Scholar",
      "abstract": "We describe a deployed scalable system for organizing published scientific literature into a heterogeneous graph to facilitate algorithmic manipulation and discovery.",
      "venue": "Annual Meeting of the Association for Computational Linguistics",
      "publicationVenue": {
        "id": "1e33b3be-b2ab-46e9-96e8-d4eb4bad6e44",
        "name": "Annual Meeting of the Association for Computational Linguistics",
        "type": "conference",
        "alternate_names": [
          "Annu Meet Assoc Comput Linguistics",
          "Meeting of the Association for Computational Linguistics",
          "ACL",
          "Meet Assoc Comput Linguistics"
        ],
        "url": "https://www.aclweb.org/anthology/venues/acl/"
      },
      "year": 1997,
      "referenceCount": 59,
      "citationCount": 453,
      "influentialCitationCount": 90,
      "isOpenAccess": true,
      "openAccessPdf": {
        "url": "https://www.aclweb.org/anthology/2020.acl-main.447.pdf",
        "status": "HYBRID",
        "license": "CCBY",
        "disclaimer": "Notice: This snippet is extracted from the open access paper or abstract available at https://aclanthology.org/2020.acl-main.447, which is subject to the license by the author or copyright owner provided with this content. Please go to the source to verify the license and copyright information for your use."
      },
      "fieldsOfStudy": [
        "Computer Science"
      ],
      "s2FieldsOfStudy": [
        {
          "category": "Computer Science",
          "source": "external"
        },
        {
          "category": "Computer Science",
          "source": "s2-fos-model"
        },
        {
          "category": "Mathematics",
          "source": "s2-fos-model"
        }
      ],
      "publicationTypes": [
        "Journal Article",
        "Review"
      ],
      "publicationDate": "2024-04-29",
      "journal": {
        "volume": "40",
        "pages": "116 - 135",
        "name": "IETE Technical Review"
      },
      "citationStyles": {
        "bibtex": "@['JournalArticle', 'Conference']{Ammar2018ConstructionOT,\n author = {Waleed Ammar and Dirk Groeneveld and Chandra Bhagavatula and Iz Beltagy and Miles Crawford and Doug Downey and Jason Dunkelberger and Ahmed Elgohary and Sergey Feldman and Vu A. Ha and Rodney Michael Kinney and Sebastian Kohlmeier and Kyle Lo and Tyler C. Murray and Hsu-Han Ooi and Matthew E. Peters and Joanna L. Power and Sam Skjonsberg and Lucy Lu Wang and Christopher Wilhelm and Zheng Yuan and Madeleine van Zuylen and Oren Etzioni},\n booktitle = {NAACL},\n pages = {84-91},\n title = {Construction of the Literature Graph in Semantic Scholar},\n year = {2018}\n}\n"
      },
      "authors": [
        "..."
      ],
      "citations": [
        "..."
      ],
      "references": []
    }
  ]
}
```

**顶层字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `offset` | integer | 此批次的起始位置 |
| `next` | integer | 下一批次的起始位置。如果没有更多数据则不存在此字段。 |
| `data` | array[PaperWithLinks] |  |

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

### 404 无效的论文 ID

**响应示例：**

```json
{
  "error": "Requested object not found"
}
```

**顶层字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `error` | string | 根据具体情况，错误消息可能是以下任一种：  - `"Paper/Author/Object not found"` - `"Paper/Author/Object with id ### not found"` |

## 数据模型

以下是响应中使用的数据模型详细说明：

### AuthorPaperBatch

**示例：**

```json
{
  "offset": 0,
  "next": 0,
  "data": [
    {
      "paperId": "5c5751d45e298cea054f32b392c12c61027d2fe7",
      "corpusId": 215416146,
      "externalIds": {
        "MAG": "3015453090",
        "DBLP": "conf/acl/LoWNKW20",
        "ACL": "2020.acl-main.447",
        "DOI": "10.18653/V1/2020.ACL-MAIN.447",
        "CorpusId": 215416146
      },
      "url": "https://www.semanticscholar.org/paper/5c5751d45e298cea054f32b392c12c61027d2fe7",
      "title": "Construction of the Literature Graph in Semantic Scholar",
      "abstract": "We describe a deployed scalable system for organizing published scientific literature into a heterogeneous graph to facilitate algorithmic manipulation and discovery.",
      "venue": "Annual Meeting of the Association for Computational Linguistics",
      "publicationVenue": {
        "id": "1e33b3be-b2ab-46e9-96e8-d4eb4bad6e44",
        "name": "Annual Meeting of the Association for Computational Linguistics",
        "type": "conference",
        "alternate_names": [
          "Annu Meet Assoc Comput Linguistics",
          "Meeting of the Association for Computational Linguistics",
          "ACL",
          "Meet Assoc Comput Linguistics"
        ],
        "url": "https://www.aclweb.org/anthology/venues/acl/"
      },
      "year": 1997,
      "referenceCount": 59,
      "citationCount": 453,
      "influentialCitationCount": 90,
      "isOpenAccess": true,
      "openAccessPdf": {
        "url": "https://www.aclweb.org/anthology/2020.acl-main.447.pdf",
        "status": "HYBRID",
        "license": "CCBY",
        "disclaimer": "Notice: This snippet is extracted from the open access paper or abstract available at https://aclanthology.org/2020.acl-main.447, which is subject to the license by the author or copyright owner provided with this content. Please go to the source to verify the license and copyright information for your use."
      },
      "fieldsOfStudy": [
        "Computer Science"
      ],
      "s2FieldsOfStudy": [
        {
          "category": "Computer Science",
          "source": "external"
        },
        {
          "category": "Computer Science",
          "source": "s2-fos-model"
        },
        {
          "category": "Mathematics",
          "source": "s2-fos-model"
        }
      ],
      "publicationTypes": [
        "Journal Article",
        "Review"
      ],
      "publicationDate": "2024-04-29",
      "journal": {
        "volume": "40",
        "pages": "116 - 135",
        "name": "IETE Technical Review"
      },
      "citationStyles": {
        "bibtex": "@['JournalArticle', 'Conference']{Ammar2018ConstructionOT,\n author = {Waleed Ammar and Dirk Groeneveld and Chandra Bhagavatula and Iz Beltagy and Miles Crawford and Doug Downey and Jason Dunkelberger and Ahmed Elgohary and Sergey Feldman and Vu A. Ha and Rodney Michael Kinney and Sebastian Kohlmeier and Kyle Lo and Tyler C. Murray and Hsu-Han Ooi and Matthew E. Peters and Joanna L. Power and Sam Skjonsberg and Lucy Lu Wang and Christopher Wilhelm and Zheng Yuan and Madeleine van Zuylen and Oren Etzioni},\n booktitle = {NAACL},\n pages = {84-91},\n title = {Construction of the Literature Graph in Semantic Scholar},\n year = {2018}\n}\n"
      },
      "authors": [
        "..."
      ],
      "citations": [
        "..."
      ],
      "references": [
        {
          "paperId": "5c5751d45e298cea054f32b392c12c61027d2fe7",
          "corpusId": 215416146,
          "url": "https://www.semanticscholar.org/paper/5c5751d45e298cea054f32b392c12c61027d2fe7",
          "title": "Construction of the Literature Graph in Semantic Scholar",
          "venue": "Annual Meeting of the Association for Computational Linguistics",
          "publicationVenue": {
            "id": "1e33b3be-b2ab-46e9-96e8-d4eb4bad6e44",
            "name": "Annual Meeting of the Association for Computational Linguistics",
            "type": "conference",
            "alternate_names": [
              "Annu Meet Assoc Comput Linguistics",
              "Meeting of the Association for Computational Linguistics",
              "ACL",
              "Meet Assoc Comput Linguistics"
            ],
            "url": "https://www.aclweb.org/anthology/venues/acl/"
          },
          "year": 1997,
          "authors": "..."
        }
      ]
    }
  ]
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `offset` | integer | 此批次的起始位置 |
| `next` | integer | 下一批次的起始位置。如果没有更多数据则不存在此字段。 |
| `data` | array[PaperWithLinks] |  |

### PaperWithLinks

**示例：**

```json
{
  "paperId": "5c5751d45e298cea054f32b392c12c61027d2fe7",
  "corpusId": 215416146,
  "externalIds": {
    "MAG": "3015453090",
    "DBLP": "conf/acl/LoWNKW20",
    "ACL": "2020.acl-main.447",
    "DOI": "10.18653/V1/2020.ACL-MAIN.447",
    "CorpusId": 215416146
  },
  "url": "https://www.semanticscholar.org/paper/5c5751d45e298cea054f32b392c12c61027d2fe7",
  "title": "Construction of the Literature Graph in Semantic Scholar",
  "abstract": "We describe a deployed scalable system for organizing published scientific literature into a heterogeneous graph to facilitate algorithmic manipulation and discovery.",
  "venue": "Annual Meeting of the Association for Computational Linguistics",
  "publicationVenue": {
    "id": "1e33b3be-b2ab-46e9-96e8-d4eb4bad6e44",
    "name": "Annual Meeting of the Association for Computational Linguistics",
    "type": "conference",
    "alternate_names": [
      "Annu Meet Assoc Comput Linguistics",
      "Meeting of the Association for Computational Linguistics",
      "ACL",
      "Meet Assoc Comput Linguistics"
    ],
    "url": "https://www.aclweb.org/anthology/venues/acl/"
  },
  "year": 1997,
  "referenceCount": 59,
  "citationCount": 453,
  "influentialCitationCount": 90,
  "isOpenAccess": true,
  "openAccessPdf": {
    "url": "https://www.aclweb.org/anthology/2020.acl-main.447.pdf",
    "status": "HYBRID",
    "license": "CCBY",
    "disclaimer": "Notice: This snippet is extracted from the open access paper or abstract available at https://aclanthology.org/2020.acl-main.447, which is subject to the license by the author or copyright owner provided with this content. Please go to the source to verify the license and copyright information for your use."
  },
  "fieldsOfStudy": [
    "Computer Science"
  ],
  "s2FieldsOfStudy": [
    {
      "category": "Computer Science",
      "source": "external"
    },
    {
      "category": "Computer Science",
      "source": "s2-fos-model"
    },
    {
      "category": "Mathematics",
      "source": "s2-fos-model"
    }
  ],
  "publicationTypes": [
    "Journal Article",
    "Review"
  ],
  "publicationDate": "2024-04-29",
  "journal": {
    "volume": "40",
    "pages": "116 - 135",
    "name": "IETE Technical Review"
  },
  "citationStyles": {
    "bibtex": "@['JournalArticle', 'Conference']{Ammar2018ConstructionOT,\n author = {Waleed Ammar and Dirk Groeneveld and Chandra Bhagavatula and Iz Beltagy and Miles Crawford and Doug Downey and Jason Dunkelberger and Ahmed Elgohary and Sergey Feldman and Vu A. Ha and Rodney Michael Kinney and Sebastian Kohlmeier and Kyle Lo and Tyler C. Murray and Hsu-Han Ooi and Matthew E. Peters and Joanna L. Power and Sam Skjonsberg and Lucy Lu Wang and Christopher Wilhelm and Zheng Yuan and Madeleine van Zuylen and Oren Etzioni},\n booktitle = {NAACL},\n pages = {84-91},\n title = {Construction of the Literature Graph in Semantic Scholar},\n year = {2018}\n}\n"
  },
  "authors": [
    {
      "authorId": "1741101",
      "name": "Oren Etzioni"
    }
  ],
  "citations": [
    {
      "paperId": "5c5751d45e298cea054f32b392c12c61027d2fe7",
      "corpusId": 215416146,
      "url": "https://www.semanticscholar.org/paper/5c5751d45e298cea054f32b392c12c61027d2fe7",
      "title": "Construction of the Literature Graph in Semantic Scholar",
      "venue": "Annual Meeting of the Association for Computational Linguistics",
      "publicationVenue": {
        "id": "1e33b3be-b2ab-46e9-96e8-d4eb4bad6e44",
        "name": "Annual Meeting of the Association for Computational Linguistics",
        "type": "conference",
        "alternate_names": [
          "Annu Meet Assoc Comput Linguistics",
          "Meeting of the Association for Computational Linguistics",
          "ACL",
          "Meet Assoc Comput Linguistics"
        ],
        "url": "https://www.aclweb.org/anthology/venues/acl/"
      },
      "year": 1997,
      "authors": [
        "..."
      ]
    }
  ],
  "references": [
    {
      "paperId": "5c5751d45e298cea054f32b392c12c61027d2fe7",
      "corpusId": 215416146,
      "url": "https://www.semanticscholar.org/paper/5c5751d45e298cea054f32b392c12c61027d2fe7",
      "title": "Construction of the Literature Graph in Semantic Scholar",
      "venue": "Annual Meeting of the Association for Computational Linguistics",
      "publicationVenue": {
        "id": "1e33b3be-b2ab-46e9-96e8-d4eb4bad6e44",
        "name": "Annual Meeting of the Association for Computational Linguistics",
        "type": "conference",
        "alternate_names": [
          "Annu Meet Assoc Comput Linguistics",
          "Meeting of the Association for Computational Linguistics",
          "ACL",
          "Meet Assoc Comput Linguistics"
        ],
        "url": "https://www.aclweb.org/anthology/venues/acl/"
      },
      "year": 1997,
      "authors": [
        "..."
      ]
    }
  ]
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `paperId` | string | Semantic Scholar 论文的主要唯一标识符 |
| `corpusId` | integer | Semantic Scholar 论文的次要唯一标识符 |
| `externalIds` | object | 包含论文在外部来源中唯一标识符的对象。外部来源包括：ArXiv、MAG、ACL、PubMed、Medline、PubMedCentral、DBLP 和 DOI。 |
| `url` | string | 论文在 Semantic Scholar 网站上的 URL |
| `title` | string | 论文标题 |
| `abstract` | string | 论文摘要。注意：由于法律原因，即使网站上显示了摘要，此字段也可能为空。 |
| `venue` | string | 论文发表的期刊或会议名称 |
| `publicationVenue` | object | 包含论文发表的期刊或会议信息的对象，包括：id（场所的唯一ID）、name（场所名称）、type（场所类型）、alternate_names（场所的备用名称数组）和 url（场所网站）。 |
| `year` | integer | 论文发表年份 |
| `referenceCount` | integer | 该论文引用的论文总数 |
| `citationCount` | integer | 引用该论文的论文总数 |
| `influentialCitationCount` | integer | 引用次数的子集，其中被引论文对引用论文有重大影响。由 Semantic Scholar 算法确定。 |
| `isOpenAccess` | boolean | 论文是否为开放获取。更多信息：https://www.openaccess.nl/en/what-is-open-access |
| `openAccessPdf` | object | 包含以下参数的对象：url（论文 PDF 链接）、status（开放获取类型 https://en.wikipedia.org/wiki/Open_access#Colour_naming_system）、论文许可证和法律免责声明。 |
| `fieldsOfStudy` | array[string] | 论文来自外部来源的高级学术分类列表。可能的字段包括：Computer Science（计算机科学）、Medicine（医学）、Chemistry（化学）、Biology（生物学）、Materials Science（材料科学）、Physics（物理学）、Geology（地质学）、Psychology（心理学）、Art（艺术）、History（历史）、Geography（地理）、Sociology（社会学）、Business（商业）、Political Science（政治学）、Economics（经济学）、Philosophy（哲学）、Mathematics（数学）、Engineering（工程学）、Environmental Science（环境科学）、Agricultural and Food Sciences（农业与食品科学）、Education（教育）、Law（法律）和 Linguistics（语言学）。 |
| `s2FieldsOfStudy` | array[object] | 对象数组。每个对象包含以下参数：category（研究领域，可能的字段与 fieldsOfStudy 相同）和 source（指定类别是由 Semantic Scholar 还是外部来源分类的）。 |
| `publicationTypes` | array[string] | 此出版物的类型 |
| `publicationDate` | string | 论文发表日期，格式为 YYYY-MM-DD |
| `journal` | object | 如果可用，包含以下参数的对象：name（期刊名称）、volume（期刊卷号）和 pages（页码范围） |
| `citationStyles` | object | 论文的 BibTeX 书目引用格式 |
| `authors` | array[AuthorInfo] | 关于论文作者的详细信息 |
| `citations` | array[PaperInfo] |  |
| `references` | array[PaperInfo] |  |

### AuthorInfo

**示例：**

```json
{
  "authorId": "1741101",
  "name": "Oren Etzioni"
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `authorId` | string | Semantic Scholar 作者的唯一 ID |
| `name` | string | 作者姓名 |

### PaperInfo

**示例：**

```json
{
  "paperId": "5c5751d45e298cea054f32b392c12c61027d2fe7",
  "corpusId": 215416146,
  "url": "https://www.semanticscholar.org/paper/5c5751d45e298cea054f32b392c12c61027d2fe7",
  "title": "Construction of the Literature Graph in Semantic Scholar",
  "venue": "Annual Meeting of the Association for Computational Linguistics",
  "publicationVenue": {
    "id": "1e33b3be-b2ab-46e9-96e8-d4eb4bad6e44",
    "name": "Annual Meeting of the Association for Computational Linguistics",
    "type": "conference",
    "alternate_names": [
      "Annu Meet Assoc Comput Linguistics",
      "Meeting of the Association for Computational Linguistics",
      "ACL",
      "Meet Assoc Comput Linguistics"
    ],
    "url": "https://www.aclweb.org/anthology/venues/acl/"
  },
  "year": 1997,
  "authors": [
    {
      "authorId": "1741101",
      "name": "Oren Etzioni"
    }
  ]
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `paperId` | string | Semantic Scholar 论文的主要唯一标识符 |
| `corpusId` | integer | Semantic Scholar 论文的次要唯一标识符 |
| `url` | string | 论文在 Semantic Scholar 网站上的 URL |
| `title` | string | 论文标题 |
| `venue` | string | 论文发表的期刊或会议名称 |
| `publicationVenue` | object | 包含论文发表的期刊或会议信息的对象，包括：id（场所的唯一ID）、name（场所名称）、type（场所类型）、alternate_names（场所的备用名称数组）和 url（场所网站）。 |
| `year` | integer | 论文发表年份 |
| `authors` | array[AuthorInfo] | 关于论文作者的详细信息 |

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

### Error404

**示例：**

```json
{
  "error": "Requested object not found"
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `error` | string | 根据具体情况，错误消息可能是以下任一种：  - `"Paper/Author/Object not found"` - `"Paper/Author/Object with id ### not found"` |

