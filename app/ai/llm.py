"""LLM 客户端：OpenAI 兼容 + SSE 流式输出。

演示期：DeepSeek（https://api.deepseek.com/v1，deepseek-chat）
本地化：换 vLLM / Ollama 等，只改 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL。
LLM 只"读原文"，与向量库无关 —— 换 LLM 不需要重建索引。
"""
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.config import get_settings


def _client() -> AsyncOpenAI:
    s = get_settings()
    if not s.LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY 未配置（.env 或环境变量），无法调用对话模型")
    return AsyncOpenAI(base_url=s.LLM_BASE_URL, api_key=s.LLM_API_KEY)


def build_context_prompt(question: str, contexts: list[dict]) -> list[dict]:
    """把检索命中的原文拼进 system 提示词，要求回答带引用标记。"""
    blocks = []
    for i, c in enumerate(contexts, 1):
        blocks.append(f"[资料{i}]（来自 {c['documentName']}）\n{c['text']}")
    system = (
        "你是 hamifs 个人文档系统的 AI 助手，仅根据下面提供的资料回答用户问题。\n"
        "回答要求：\n"
        "1. 只依据资料内容，资料不足以回答时明确说明；\n"
        "2. 引用资料时在句末标注出处，形如 [资料1]；\n"
        "3. 用简体中文、Markdown 格式回答。\n\n"
        + ("\n\n".join(blocks) if blocks else "（资料库中暂无相关内容）")
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]


async def chat_once(messages: list[dict], max_tokens: int = 500) -> str:
    """非流式单轮生成（自动打标签等结构化小任务用）。"""
    s = get_settings()
    client = _client()
    resp = await client.chat.completions.create(
        model=s.LLM_MODEL,
        messages=messages,  # type: ignore[arg-type]
        temperature=0.2,
        max_tokens=max_tokens,
        stream=False,
    )
    return resp.choices[0].message.content or ""


async def stream_chat(messages: list[dict]) -> AsyncIterator[str]:
    """流式生成回答，逐段 yield 文本增量。"""
    s = get_settings()
    client = _client()
    stream = await client.chat.completions.create(
        model=s.LLM_MODEL,
        messages=messages,  # type: ignore[arg-type]
        temperature=s.LLM_TEMPERATURE,
        stream=True,
    )
    async for event in stream:
        if event.choices and event.choices[0].delta and event.choices[0].delta.content:
            yield event.choices[0].delta.content
