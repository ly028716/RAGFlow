# 车载 RAG Agent Baseline 评测运行记录（BLOCKED）

## 结论

本次未产生真实评测结果。没有调用导入 API、Agent SSE、DashScope Embedding 或 DashScope LLM，因此所有质量、引用和延迟指标均为不可用，不能填写。

## 已验证的运行元数据

- 运行日期：2026-08-31
- Git commit：`a21a671a84899c01e7549f156209cbd18982134e`
- 语料版本：`vehicle-agent-demo-v1`
- 评测接口：`POST /api/v1/agent/execute/stream`（未调用）
- LLM 模型：未验证；计划评测参数为 `qwen-plus`
- Embedding 模型：未验证；计划评测参数为 `text-embedding-v3`
- Top-K / 阈值：未验证；计划评测参数为 `5 / 0.7`
- 分块大小 / 重叠：未验证；计划评测参数为 `1000 / 200`
- Faithfulness / Answer Relevancy：待人工复核；本次没有回答可复核

## 已验证的环境状态

| 项目 | 状态 | 证据 |
| --- | --- | --- |
| DashScope Key 环境变量 | 已设置 | 仅检查变量是否存在，未输出其值 |
| MySQL 3306 | 可达 | 本地 TCP 检查通过 |
| Redis 6379 | 可达 | 本地 TCP 检查通过 |
| RAGFlow API 8000 | 不可达 | 本地 TCP 检查失败 |
| Docker | 不可用 | `docker` 命令不存在 |
| 系统 Python | 不可用 | `py` 报告没有已安装 Python |
| Codex Python | 可用但依赖不完整 | Python 3.12；缺 `chromadb`、`dashscope`、`langchain` |

## 阻塞原因

1. 后端 API 没有启动，因此无法创建或确认知识库、登录获取 Token、导入语料和调用 Agent SSE。
2. 可用的 Codex Python 3.12 未预装项目依赖。尝试将 `backend/requirements-dev.txt` 安装到仓库内 `backend/.venv` 时，长时间的 Chroma 依赖构建未完成；最终确认 `chromadb`、`dashscope`、`langchain` 均不可导入。
3. 当前机器没有 Docker，也没有可用的 Python 3.10/3.11 运行时可替代。

## 指标

| Recall@K | Hit Rate | MRR | 引用有效率 | 平均检索 ms | 平均生成 ms | 平均首 Token ms | 拒答率 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| — | — | — | — | — | — | — | — |

## 后续条件

提供一个可持续运行的 Python 3.10/3.11 环境或 Docker，并完成后端依赖安装、数据库迁移、API 启动和有效登录 Token 后，再按 `docs/车载座舱RAG-Demo运行说明.md` 导入语料并运行 `backend/scripts/run_rag_evaluation.py`。届时该脚本才会生成逐题原始 SSE、真实映射和真实指标。
