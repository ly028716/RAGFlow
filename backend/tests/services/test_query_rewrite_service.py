from app.services.rag.query_rewrite_service import QueryRewriteService


def test_rewrite_returns_original_question_when_no_rewrite_is_needed():
    question = "RAG 的相似度阈值如何配置？"

    assert QueryRewriteService().rewrite(question) == question


def test_rewrite_removes_polite_query_prefix_without_changing_intent():
    assert QueryRewriteService().rewrite("请帮我查询 RAG 的部署流程") == "RAG 的部署流程"
