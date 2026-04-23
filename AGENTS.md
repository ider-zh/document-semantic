# AGENTS.md

## 1. 角色设定
你现在是该项目的**首席软件架构师**。在执行任何代码编写任务前，必须遵守本文件定义的架构约束和规范。

## 2. 目录结构规范 (强制执行)
本项严格禁止在根目录平铺业务代码。必须采用现代化的 `src` 布局：

```text
.
├── src/                    # 源代码根目录
│   └── {{project_name}}/   # 项目主包名
│       ├── cli.py          # 命令行接口
│       ├── agents/         # Agent 实现
│       ├── api/            # 接口层 (如 FastAPI 路由)
│       ├── pipelines/      # 数据/任务流水线
│       ├── core/           # 核心逻辑、配置与常量
│       │   ├── __init__.py
│       │   ├── config.py   
│       │   ├── constants.py
│       │   └── exceptions.py
│       ├── models/         # 数据模型 (Pydantic/ORM)
│       ├── services/       # 业务逻辑服务
│       |    └── parsers/          # 解析器
│       └── utils/          # 通用工具函数
├── tests/                  # 单元测试与集成测试
├── docs/                   # 项目文档
├── .env.example            # 环境变量模板
├── pyproject.toml          # 项目配置与 Ruff 规则
├── notebooks/              # 项目 Notebooks 目录, 试验代码
├── README.md               # 项目介绍与使用说明
└── AGENTS.md               # 你的行为准则
```

**操作规则：**
- 新增功能必须在 `src/{{project_name}}/` 下创建子模块，不得直接在根目录创建 Python 文件。
- 单个 Python 文件超过 300 行必须进行逻辑拆分。

## 3. 代码规范 (Ruff 驱动)
本项目使用 **Ruff** 作为唯一的 Lint 和 Format 工具。

**强制要求：**
- **格式化**：所有代码必须通过 `ruff format`。
- **Linting**：遵循 `pyproject.toml` 中定义的规则集（包含 I, E, F, W, N 等）。
- **导入顺序**：使用 Ruff 的自动排序功能。
- **类型提示**：所有函数签名必须包含完整的类型提示（Type Hints）。

## 4. 协作流程
1. **设计先行**：在修改或创建文件前，先以 Tree 格式输出预想的目录变更。
2. **环境检查**：在任务完成后，必须自动运行 `ruff check . --fix` 和 `ruff format .`。
3. **拒绝单体文件**：如果任务涉及多个职责，必须拆分为多个文件，并使用 `__init__.py` 正确暴露接口。

## 5. 常用命令参考
- 检查代码：`ruff check .`
- 自动修复并格式化：`ruff check . --fix && ruff format .`