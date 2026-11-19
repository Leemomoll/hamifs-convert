"""文本切块：按 Markdown 标题 / 空行段落切分，合并到目标长度。

设计要点（对齐《个人智能文档与知识库系统-方案设计》）：
- 每块 CHUNK_SIZE 字左右（默认 600），相邻块带 CHUNK_OVERLAP 重叠，避免语义被切断
- 切块质量决定 RAG 效果上限，参数全部走配置，便于真实语料上迭代调优
"""
from app.config import get_settings


def _split_paragraphs(text: str) -> list[str]:
    """优先按标题行切，再按空行切，得到尽量语义完整的碎片。"""
    lines = text.replace("\r\n", "\n").split("\n")
    blocks: list[str] = []
    buf: list[str] = []

    def flush():
        if buf:
            blocks.append("\n".join(buf).strip())
            buf.clear()

    for line in lines:
        stripped = line.strip()
        # Markdown 标题 / 编号列表开头视为新语义单元的边界
        if stripped and (stripped.startswith("#") or stripped.startswith("- ") or stripped[0].isdigit()):
            flush()
        buf.append(line)
        if not stripped:  # 空行 = 段落结束
            flush()
    flush()
    return [b for b in blocks if b]


def _hard_cut(block: str, size: int) -> list[str]:
    """超长段落硬切（按句子边界优先）。"""
    pieces: list[str] = []
    while len(block) > size:
        cut = block.rfind("。", 0, size)
        cut = cut if cut > size // 2 else size
        pieces.append(block[: cut + 1].strip())
        block = block[cut + 1:].strip()
    if block:
        pieces.append(block)
    return pieces


def chunk_text(text: str) -> list[str]:
    """入口：把整篇文本切成带重叠的块列表。"""
    s = get_settings()
    size = max(200, s.CHUNK_SIZE)
    overlap = min(s.CHUNK_OVERLAP, size // 2)

    chunks: list[str] = []
    cur = ""
    for block in _split_paragraphs(text):
        if len(block) > size:
            # 当前累积的先收口，再对超长块硬切
            if cur:
                chunks.append(cur)
                cur = ""
            pieces = _hard_cut(block, size)
            for p in pieces:
                chunks.append(p)
            continue
        if cur and len(cur) + len(block) + 1 > size:
            chunks.append(cur)
            # 带重叠：取上一块尾部作为下一块开头
            cur = cur[-overlap:] + "\n" + block if overlap else block
        else:
            cur = (cur + "\n" + block).strip() if cur else block
    if cur:
        chunks.append(cur)
    return chunks
