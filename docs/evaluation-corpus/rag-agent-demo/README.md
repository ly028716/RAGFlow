# rag-agent-demo-v1 评测语料

`manifest.json` 是稳定映射：数据集里的逻辑文档 ID（文件名）对应本目录中的 Markdown 文件和 `expected_source_identifier`。数据库 `Document.id` 为运行时自增值，不能写死在 Git 中。

创建 `rag-agent-demo` 知识库、获取访问令牌后，在仓库根目录运行：

```powershell
$env:RAG_EVAL_ACCESS_TOKEN = "<token>"
python backend/scripts/import_rag_evaluation_corpus.py --knowledge-base-id <ID>
```

脚本会写出 `runtime-document-map.local.json`。它包含每个逻辑 ID 的真实 `runtime_document_id`，可直接用于按 `document_id` 返回的检索结果评分。该文件是环境产物，已被 Git 忽略；`runtime-document-map.example.json` 仅说明其格式。
