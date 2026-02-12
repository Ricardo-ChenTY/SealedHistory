# 关于论文的详细信息

**接口路径：** `GET https://ai4scholar.net/graph/v1/paper/{paper_id}`

## 接口信息

| 属性 | 值 |
|------|----|
| 接口路径 | `GET https://ai4scholar.net/graph/v1/paper/{paper_id}` |
| 所属分类 | 论文数据 |
| Base URL | `https://ai4scholar.net` |

## 描述

示例：

• `https://ai4scholar.net/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b`

• 返回论文的 paperId 和 title。

• `https://ai4scholar.net/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b?fields=url,year,authors`

• 返回论文的 paperId、url、year 和作者列表。
• 每个作者包含 authorId 和 name。

• `https://ai4scholar.net/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b?fields=citations.authors`

• 返回论文的 paperId 和引用列表。
• 每条引用包含 paperId 和作者列表。
• 每个作者包含 authorId 和 name。


限制：

• 一次最多返回 10 MB 数据。



## 路径参数

| 参数名 | 类型 | 必填 |
|--------|------|------|
| [`paper_id`](#paper_id) | string | 是 |

### 参数详细说明

#### `paper_id`

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


## 查询参数

| 参数名 | 类型 | 必填 | 默认值 |
|--------|------|------|--------|
| [`fields`](#fields) | string | 否 | - |

### 参数详细说明

#### `fields`

以逗号分隔的返回字段列表。请参阅下方响应架构的内容，了解所有可返回的字段。
`paperId` 字段始终返回。如果省略 fields 参数，则仅返回 `paperId` 和 `title`。
使用点号（"."）表示有版本号或子字段的字段，如 `embedding`、`authors`、`citations` 和 `references` 字段：

• 请求 `authors` 时，默认返回 `authorId` 和 `name` 子字段。要请求其他子字段，请使用格式 `author.url,author.paperCount` 等。
• 请求 `citations` 和 `references` 时，默认返回 `paperId` 和 `title` 子字段。要请求其他子字段，请使用格式 `citations.title,citations.abstract` 等。
• 请求 `embedding` 时，默认 Specter 嵌入版本为 v1。指定 `embedding.specter_v2` 以选择 v2 嵌入。

示例：

• `fields=title,url`
• `fields=title,embedding.specter_v2`
• `fields=title,authors,citations.title,citations.abstract`


## Python 示例

```python
import requests
import json

# 设置 API Key
API_KEY = "YOUR_API_KEY"

url = "https://ai4scholar.net/graph/v1/paper/{paper_id}"
headers = {
    "x-api-key": API_KEY,
}

# 查询参数
params = {
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
curl -X GET "https://ai4scholar.net/graph/v1/paper/{paper_id}" \
  -H "x-api-key: YOUR_API_KEY"
```

## 响应

### 200 包含默认或请求字段的论文

**响应示例：**

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
      "externalIds": {
        "DBLP": [
          123
        ]
      },
      "url": "https://www.semanticscholar.org/author/1741101",
      "name": "Oren Etzioni",
      "affiliations": [
        "Allen Institute for AI"
      ],
      "homepage": "https://allenai.org/",
      "paperCount": 10,
      "citationCount": 50,
      "hIndex": 5
    }
  ],
  "citations": [
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
      "authors": "..."
    }
  ],
  "references": [
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
      ]
    }
  ],
  "embedding": {
    "model": "specter@v0.1.1",
    "vector": [
      -8.82082748413086,
      -2.6610865592956543
    ]
  },
  "tldr": {
    "model": "tldr@v2.0.0",
    "text": "This paper reduces literature graph construction into familiar NLP tasks, point out research challenges due to differences from standard formulations of these tasks, and report empirical results for each task."
  }
}
```

**顶层字段说明：**

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
| `authors` | array[Author] |  |
| `citations` | array[BasePaper] |  |
| `references` | array[BasePaper] |  |
| `embedding` | Embedding |  |
| `tldr` | Tldr |  |

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

### FullPaper

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
      "externalIds": {
        "DBLP": [
          123
        ]
      },
      "url": "https://www.semanticscholar.org/author/1741101",
      "name": "Oren Etzioni",
      "affiliations": [
        "Allen Institute for AI"
      ],
      "homepage": "https://allenai.org/",
      "paperCount": 10,
      "citationCount": 50,
      "hIndex": 5
    }
  ],
  "citations": [
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
      ]
    }
  ],
  "references": [
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
      ]
    }
  ],
  "embedding": {
    "model": "specter@v0.1.1",
    "vector": [
      -8.82082748413086,
      -2.6610865592956543
    ]
  },
  "tldr": {
    "model": "tldr@v2.0.0",
    "text": "This paper reduces literature graph construction into familiar NLP tasks, point out research challenges due to differences from standard formulations of these tasks, and report empirical results for each task."
  }
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
| `authors` | array[Author] |  |
| `citations` | array[BasePaper] |  |
| `references` | array[BasePaper] |  |
| `embedding` | Embedding |  |
| `tldr` | Tldr |  |

### Author

**示例：**

```json
{
  "authorId": "1741101",
  "externalIds": {
    "DBLP": [
      123
    ]
  },
  "url": "https://www.semanticscholar.org/author/1741101",
  "name": "Oren Etzioni",
  "affiliations": [
    "Allen Institute for AI"
  ],
  "homepage": "https://allenai.org/",
  "paperCount": 10,
  "citationCount": 50,
  "hIndex": 5
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `authorId` | string | Semantic Scholar 作者的唯一 ID |
| `externalIds` | object | 包含作者的 ORCID/DBLP ID 的对象（如已知） |
| `url` | string | 作者在 Semantic Scholar 网站上的 URL |
| `name` | string | 作者姓名 |
| `affiliations` | array[string] | 作者的组织机构隶属关系数组 |
| `homepage` | string | 作者主页 |
| `paperCount` | string | 作者的总发表数量 |
| `citationCount` | string | 作者的总引用次数 |
| `hIndex` | string | 作者的 h 指数，用于衡量作者论文的产出量和引用影响力：https://www.semanticscholar.org/faq#h-index |

### BasePaper

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
  ]
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `paperId` | string | Semantic Scholar 论文的主要唯一标识符 |
| `corpusId` | integer | Semantic Scholar 论文的次要唯一标识符 |
| `externalIds` | object | 包含论文在外部来源中唯一标识符的对象。外部来源包括：ArXiv、MAG、ACL、PubMed、Medline、PubMedCentral、DBLP 和 DOI。 |
| `url` | string | 论文在 Semantic Scholar 网站上的 URL。 |
| `title` | string | 论文标题 |
| `abstract` | string | 论文摘要。注意：由于法律原因，即使网站上显示了摘要，此字段也可能为空。 |
| `venue` | string | 论文发表的期刊或会议名称 |
| `publicationVenue` | object | 包含论文发表的期刊或会议信息的对象，包括：id（场所的唯一ID）、name（场所名称）、type（场所类型）、alternate_names（场所的备用名称数组）和 url（场所网站）。 |
| `year` | integer | 论文发表年份。 |
| `referenceCount` | integer | 该论文引用的论文总数。 |
| `citationCount` | integer | 引用该论文的论文总数。 |
| `influentialCitationCount` | integer | 引用次数的子集，其中被引论文对引用论文有重大影响。由 Semantic Scholar 算法确定：https://www.semanticscholar.org/faq#influential-citations |
| `isOpenAccess` | boolean | 论文是否为开放获取。更多信息：https://www.openaccess.nl/en/what-is-open-access。 |
| `openAccessPdf` | object | 包含以下参数的对象：url（论文 PDF 链接）、status（开放获取类型 https://en.wikipedia.org/wiki/Open_access#Colour_naming_system）、论文许可证和法律免责声明。 |
| `fieldsOfStudy` | array[string] | 论文来自外部来源的高级学术分类列表。可能的字段包括：Computer Science（计算机科学）、Medicine（医学）、Chemistry（化学）、Biology（生物学）、Materials Science（材料科学）、Physics（物理学）、Geology（地质学）、Psychology（心理学）、Art（艺术）、History（历史）、Geography（地理）、Sociology（社会学）、Business（商业）、Political Science（政治学）、Economics（经济学）、Philosophy（哲学）、Mathematics（数学）、Engineering（工程学）、Environmental Science（环境科学）、Agricultural and Food Sciences（农业与食品科学）、Education（教育）、Law（法律）和 Linguistics（语言学）。 |
| `s2FieldsOfStudy` | array[object] | 对象数组。每个对象包含以下参数：category（研究领域，可能的字段与 fieldsOfStudy 相同）和 source（指定类别是由 Semantic Scholar 还是外部来源分类的。关于 Semantic Scholar 如何分类论文的更多信息：https://blog.allenai.org/announcing-s2fos-an-open-source-academic-field-of-study-classifier-9d2f641949e5） |
| `publicationTypes` | array[string] | 此出版物的类型。 |
| `publicationDate` | string | 论文发表日期，格式为 YYYY-MM-DD。 |
| `journal` | object | 包含以下参数的对象（如有）：name（期刊名称）、volume（期刊卷号）和 pages（页码范围） |
| `citationStyles` | object | 论文的 BibTeX 书目引用格式。 |
| `authors` | array[AuthorInfo] | 论文作者的详细信息 |

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

### Embedding

**示例：**

```json
{
  "model": "specter@v0.1.1",
  "vector": [
    -8.82082748413086,
    -2.6610865592956543
  ]
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `model` | string | Spector 向量嵌入模型版本：https://github.com/allenai/specter |
| `vector` | object | 数值嵌入向量 |

### Tldr

**示例：**

```json
{
  "model": "tldr@v2.0.0",
  "text": "This paper reduces literature graph construction into familiar NLP tasks, point out research challenges due to differences from standard formulations of these tasks, and report empirical results for each task."
}
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `model` | string | TLDR 模型版本号：https://github.com/allenai/scitldr |
| `text` | string | 论文的 TLDR 摘要 |

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

