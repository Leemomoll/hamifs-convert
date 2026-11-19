"""hamifs-convert 的 AI（RAG）模块。

职责边界：
- 本模块只做"计算"：文本提取 -> 切块 -> 向量化 -> Chroma 检索 -> LLM 生成（SSE 流式）
- 无状态：对话历史、引用记录由 Java 主后端落 MySQL（ai_conversation / ai_message）
- 文档生命周期联动由 Java 负责：上传成功后调 POST /ai/index/{id}，删除时调 DELETE /ai/index/{id}
"""
