# 车载 Android / 座舱 RAG Agent Demo 运行说明

## 范围

本 Demo 使用自编 `vehicle-agent-demo-v1` 语料，演示车载接口查询、Android 日志诊断、V1/V2 差异、知识库范围拒答和来源追溯。它不连接真车、不发送 CAN 报文、不包含 OEM 保密资料。

## 前置条件

- 后端可访问 MySQL、Redis 和 Chroma 持久化目录。
- 后端已配置真实 `DASHSCOPE_API_KEY`；不能用开发 Mock Embedding 作为求职评测结果。
- 后端服务运行在可访问的 API 地址，默认 `http://localhost:8000/api/v1`。
- 已登录用户拥有目标知识库的 Editor 权限，评测 Token 对该知识库拥有 Viewer 权限。
- Python 环境安装了 [backend/requirements.txt](../backend/requirements.txt) 中的依赖。

## 1. 启动服务并创建知识库

按照现有部署方式启动 MySQL、Redis 和后端。创建名称为 `vehicle-agent-demo` 的知识库，记录数字 ID；登录后将 access token 放入环境变量。

```powershell
$env:RAG_EVAL_ACCESS_TOKEN = "<access-token>"
```

## 2. 导入自编语料

```powershell
python backend/scripts/import_rag_evaluation_corpus.py `
  --knowledge-base-id <KB_ID> `
  --corpus-root docs/evaluation-corpus/vehicle-agent-demo
```

在知识库页面或文档 API 确认 15 份文档都为 `completed`。导入产生的 `runtime-document-map.local.json` 是本次环境的真实 ID 映射，不能复用到其他数据库。

## 3. 执行真实 Agent 评测

以下参数必须与后端实际配置一致，脚本会将它们原样写入结果元数据。

```powershell
python backend/scripts/run_rag_evaluation.py `
  --mode agent `
  --knowledge-base-id <KB_ID> `
  --runtime-map docs/evaluation-corpus/vehicle-agent-demo/runtime-document-map.local.json `
  --llm-model qwen-plus `
  --embedding-model text-embedding-v3 `
  --top-k 5 `
  --similarity-threshold 0.7 `
  --chunk-size 1000 `
  --chunk-overlap 200
```

`--mode both` 会分别调用 Agent SSE 和普通 RAG SSE；普通 RAG 不具备 Agent 引用校验，报告会将其引用有效率标记为 `—`。

结果写入 `docs/evaluation-results/vehicle-agent-demo-v1/<UTC 时间>-<mode>/`，包括原始 SSE、逐题评分、运行元数据、Markdown 报告和人工复核模板。没有 API Key、服务未启动、Token 无权限或文档未完成时，脚本会保留错误证据并以非零状态退出，不会编造指标。

## 4. 人工复核

`manual-review.jsonl` 为每道可回答题保留 Faithfulness 与 Answer Relevancy 的两位评审字段。两位评审独立填写；没有完成复核时，报告不得将这些字段写为分数。
