# vehicle-agent-demo-v1 评测语料

本目录是用于求职演示的自编、非保密车载 Android / 座舱 RAG 语料。接口、错误码、协议行为和车型均为虚构示例，不得将其解释为任何 OEM 或供应商的生产资料。

`manifest.json` 中的逻辑文档 ID 用于题集标注；导入后由数据库生成真实 `Document.id`。不要把运行时数字 ID 写回 manifest。

导入示例：

```powershell
$env:RAG_EVAL_ACCESS_TOKEN = "<已登录用户的 access token>"
python backend/scripts/import_rag_evaluation_corpus.py `
  --knowledge-base-id <vehicle-agent-demo 知识库 ID> `
  --corpus-root docs/evaluation-corpus/vehicle-agent-demo
```

脚本会生成 `runtime-document-map.local.json`。确认全部文档状态为 `completed` 后，才能使用该映射运行真实评测。
