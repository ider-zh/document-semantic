# 1
我现在要构建一个文档语义化处理 pipeline
docx -文档解析(处理器可替换, pandoc, python-docx)-> md 数据[图片附件等] -语义化识别(re or llm)->  自定义的语义化的结构数据, 比如行数据(title. head1, head2,head3,text abstract, reference 等), 行内数据(通用的加粗, 斜体, 删除线, 公式, 代码片段, 等有样式的内容)
现在请把流程框架搭建好, 要支持以下扩展能力
0. 使用 python 开发
1. 文档解析可替换用不同的工具实现
2. 语义化识别也可替换或者根据文档条件路由
3. 语义化的结构数据可以进行升级或者根据文档类型进行路由
4. 当前开发阶段需要频繁试错, 每一步都要能输出可观测的结果, 打印可控的警告信息, 使用 loguru
5. 设计好测试框架

# 2
我要为
src/document_semantic/services/parsers/pandoc_parser.py
处理的md结果增加一个转用的, recognizer, 进行段落级别的语义识别
(可以用的测试样例: tests/docx/output/test_2_pandoc_regex/output.md)
以下是我发现的问题需要处理:
1. pandocx 生成的md文件, 大量是以 "> " 开头的段落, 你可以根据文档中r"$> "的占比, 判断"> "就是错误的使用, 进行去除
2. "> * *" 这样的段落, 只有语义没有内容, 类似的也应该去除
3. 连续空行, 应只保留一个空行
4. 文档的第一行文字, 即使没有样式, 也应该理解为 title
处理建议:
1. 定义一个内部的块结构, 用来记录段落和图片, 可以参考 python-docx 的结构, 需要有语义化的字段, 选项可以是 title,author, keyword, head1, head2, head3, text, abstract_head, abstract, conclusion_head, conclusion, reference_head, reference, formula, code, image, table, list 等等
2. 段落语义识别处理方法, 先通过 re 预处理 image 和 table(table是多行的, 合并成一个块数据),
剩余部分使用 strands-agents 构建 agent, + Structured Output 来识别段落的语义, demo:
```
from pydantic import BaseModel, Field
from strands import Agent

# 1) Define the Pydantic model
class PersonInfo(BaseModel):
    """Model that contains information about a Person"""
    name: str = Field(description="Name of the person")
    age: int = Field(description="Age of the person")
    occupation: str = Field(description="Occupation of the person")

# 2) Pass the model to the agent
agent = Agent()
result = agent(
    "John Smith is a 30 year-old software engineer",
    structured_output_model=PersonInfo
)

# 3) Access the `structured_output` from the result
person_info: PersonInfo = result.structured_output
print(f"Name: {person_info.name}")      # "John Smith"
print(f"Age: {person_info.age}")        # 30
print(f"Job: {person_info.occupation}") # "software engineer"
```
特别建议, 不应该让 agent 直接输出段落内容, 让 agent 输出段落 ID 和对于语义进行处理, 如果是连续的 formula, code, list, 应该合并成一个块数据. 
agent 识别段落语义的过程中, 如果段落很长, 也不需要全部放到上下文, 控制一个最大长度, 中间采取省略的方式进行输入.
你先根据我的描述指定一个包含细节的 plan,我进行确认

# 3
pandoc_recognizer.py debug
当前分析的数据.
tests/docx/output/test_1.docx_pandoc_pandoc_agent/pandoc_agent_output.json
1. "id": "8ab4946d-5483-4a01-a595-597d2186656f", "content": "**摘要**\n\n所罗门诺夫在... 被识别为 head1 ,应该是 abstract
2.       "id": "54b52a4a-fc8b-41ab-a5af-12469e8d68b0",
      "type": "text",
      "content": "2.  **历史：蔡廷与随机性**",
      "inline_elements": []
      应该为 head1
3.     {
      "id": "f9bfa311-309c-49e3-a4ed-08ba35d50a0c",
      "type": "text",
      这一条把 image 也混入了

# 4
tests/docx/output/test_1.docx_pandoc_pandoc_agent/pandoc_agent_output.json
## 下列的内容, 应该能够通过 re 预检测识别为 image, 后面的 "{width=\..." 样式可以不保留
    {
      "id": "e5cfb97f-be8c-4433-9a56-b020683728f9",
      "type": "text",
      "content": "![](/tmp/tmpeg0ujohl/media/media/image1.jpg){width=\"4.600339020122485in\" height=\"3.4502548118985126in\"}",
      "inline_elements": []
    },

## image 下的文字要检测其是否是是图片的描述, 在 _STYLE_HINT_MAP 增加描述的样式, 例如: "image_description" 和 table_description

# 5
我们回到 mineru_parser.py 开发上
zip 中的 content_list_v2.json 文件是我们的处理重心
当前存在的问题
1. 段落识别问题
    + 分页极大可能拆分段落
    + work 渲染的分行也可能会拆分段落
2. 来个单词被换行, mineru_parser 后可能会练成一个单词
处理建议:
1. 使用 python-docx 读取文档, 按段落分组标记 (需要normalize, 去除容易被ocr出错的空格等符号,标点全部统一为英文标点),生成一个带段落id的段落列表
content_list_v2.json 中只处理 "type": "paragraph" 的类型, normalize 之后去上面的数据中搜索, 获取段落id, 如果连续的paragraph都是相同的段落id, 则合并为一个paragraph处理

2, 单词换行问题, 也需要使用 python-docx 读取文档的数据恢复, 你帮我设计一个方案解决这个问题

# 6
我非常看好 mineru 分支路线, 决定在作为主路线开发
原来的多 parser 约数, 现在可以打破
intermediate_result.json 作为前一版本的输出结果, 相比 content_list_v2.json 少了很多信息, 我决定输出的格式参考content_list_v2.json, 但是不需要其中的 bbox 信息, mineru ocr 带来的问题通过刚才 docx 对齐工具解决, 输出一个修复后的 content_list_v2.json 文件和资源文件


# 7
content_list_v2.json 的结构是什么? 需要定义一个数据class表示, 后续不同的业务开发需要扩展内容

以下是计划开发的模块:
1. 语言映射模块, 提供  
将 title, abstract, conclusion, reference 等从 content_list_v2 中的 head1 中提取出来