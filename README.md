# cli-anything-ai-novelgenerator

`AI_NovelGenerator` 的独立命令行版本，面向自动化、无界面工作流、批量生成、提示词检查、工作区编辑和回归测试。

这个仓库已经是一个可单独发布的 CLI 仓库，不再依赖旁边必须存在的 GUI 项目源码目录。

## 仓库定位

这个仓库提供的是：

- 可安装的 Python CLI 包
- 对原小说生成流程的命令行封装
- 适合脚本调用、Agent 调用和批处理调用的工作流接口

这个仓库不提供：

- GUI 界面
- `pdf`、`epub`、`docx` 这类成品出版导出
- 极简依赖体积的轻量包

当前导出能力为 `bundle`，即把项目控制文件和工作区内容打成 ZIP 包。

## 目录结构

```text
AI_NovelGenerator-CLI/
├── cli_anything/ai_novelgenerator/
│   ├── ai_novelgenerator_cli.py      # CLI 入口
│   ├── core/                         # 命令层工作流逻辑
│   ├── backend/source_root/          # 已 vendoring 的运行时后端
│   ├── tests/                        # 单测与端到端测试
│   └── README.md                     # 包级详细说明
├── .github/workflows/ci.yml          # CI 工作流
├── pyproject.toml                    # 打包与依赖配置
├── setup.py                          # setuptools 兼容入口
├── LICENSE
└── README.md
```

## 安装

可编辑安装：

```bash
pip install -e .
```

安装并带上测试依赖：

```bash
pip install .[test]
```

安装后命令名为：

```bash
cli-anything-ai-novelgenerator
```

## 快速开始

先创建一个项目控制文件和工作区：

```bash
cli-anything-ai-novelgenerator project new -o demo.json --workspace ./demo-work --config ./config.json --topic "记忆之城" --genre "科幻" --chapters 3 --words 1200
```

然后执行基本生成流程：

```bash
cli-anything-ai-novelgenerator --project demo.json generate architecture
cli-anything-ai-novelgenerator --project demo.json generate blueprint
cli-anything-ai-novelgenerator --project demo.json chapter generate 1
cli-anything-ai-novelgenerator --project demo.json chapter finalize 1
cli-anything-ai-novelgenerator --project demo.json export bundle ./demo.zip --overwrite
```

如果你希望输出更适合脚本处理的 JSON：

```bash
cli-anything-ai-novelgenerator --json --project demo.json project status
```

如果你想进入交互式 REPL：

```bash
cli-anything-ai-novelgenerator
```

## 主要命令分组

- `project`：创建、打开、更新项目，查看整体状态与下一步建议
- `config`：查看配置，管理 LLM / Embedding profiles，切换绑定关系
- `generate`：生成设定架构与章节蓝图，查看可恢复的架构状态
- `workspace`：读取或覆盖核心工作区文本文件
- `role`：管理角色库分类和角色条目，导入角色文本，分析角色状态
- `chapter`：检查提示词、查看章节状态、生成草稿、批量生成、续跑、定稿、扩写、手工改稿
- `knowledge`：导入知识库内容，清空向量库
- `review`：执行一致性审校，查看剧情要点上下文
- `export`：导出 ZIP bundle
- `session`：记录当前项目指针，支持 undo / redo

## 典型输出内容

CLI 运行时通常会产生两类内容：

1. 项目控制文件，例如 `demo.json`
2. 工作区目录，例如 `demo-work/`

工作区里通常会包含：

- `Novel_architecture.txt`
- `Novel_directory.txt`
- `character_state.txt`
- `global_summary.txt`
- `partial_architecture.json`
- `chapter_states.json`
- `plot_arcs.txt`
- `chapters/`
- `vectorstore/`
- `角色库/`

这些运行产物已经加入 `.gitignore`，默认不会污染仓库。

## 适用场景

- 希望把小说生成流程接进脚本或自动化流水线
- 希望批量生成多章并支持断点续跑
- 希望在生成前查看 prompt、章节状态和项目进度
- 希望对工作区文本进行命令行读写，而不是手工打开 GUI
- 希望在没有外部 API 的情况下跑确定性测试

## 测试

运行完整测试：

```bash
python -m pytest
```

如果你想强制子进程测试走已安装的控制台命令，而不是模块 fallback：

```bash
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest
```

测试默认使用 `HarnessMock`，因此可以在不访问真实外部模型接口的情况下验证整条工作流。

## 发布前需要改的地方

正式发布到 GitHub 之前，建议检查并更新：

- `pyproject.toml` 里的 `Homepage`
- `pyproject.toml` 里的 `Repository`
- `pyproject.toml` 里的 `Issues`
- 作者信息与版本号策略

## 当前限制

- 默认测试不会覆盖真实在线模型服务
- 当前导出只支持 ZIP bundle
- 该 CLI 重点是工作流控制与自动化，不追求 GUI 使用体验一致性

## 更多说明

更详细的命令示例和包级说明见：

- `cli_anything/ai_novelgenerator/README.md`
