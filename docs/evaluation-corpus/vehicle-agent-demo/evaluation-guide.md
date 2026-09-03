# 车载 RAG 评测说明

固定题集包含单文档、多文档、版本差异、日志诊断和无答案问题。Recall@K、Hit Rate、MRR 只对可回答题按运行时 document_id 计算；无答案题单独计算拒答率。

评测器必须保存原始 SSE、模型与分块参数、语料版本、Git commit 和运行时 ID 映射。Faithfulness 与 Answer Relevancy 由两位评审独立复核，未复核不得填写数值。
