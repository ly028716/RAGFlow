# 评测指南

Recall@K 为 Top-K 结果命中的期望文档数除以期望文档总数，再对题目求平均。Hit Rate 只判断是否命中至少一个期望文档；它与 Recall@K 都使用固定标注集。

Faithfulness 由评审逐条核对答案断言是否被最终上下文支持；Answer Relevancy 衡量是否覆盖期望要点且没有偏离问题。引用存在并不等于事实一定被支持。
