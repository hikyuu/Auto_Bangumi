"""AI-powered offset detection prompt builder and request model.

Extracted from bangumi.py to keep the AI prompt logic separate from
the API routing layer.
"""

from pydantic import BaseModel


class AIDetectOffsetRequest(BaseModel):
    """Request body for AI detect-offset endpoint.

    Only title and the first RSS episode title are needed — the LLM
    extracts season and episode from the full title internally.
    """
    title: str
    first_title: str | None = None


def build_ai_offset_prompt() -> str:
    """Build the system prompt for AI offset detection."""
    return """\
你是一个番剧偏移量检测助手。根据提供的 RSS 首集标题和 TMDB 官方元数据，判断是否需要偏移修正。

你需要从 RSS 标题中自行提取季号和集号，然后结合 TMDB 数据判断。

常见场景：
- 字幕组可能将一个季度（cour）标为独立一季，TMDB 则视为同一季的一部分
- 集号可能是跨季累加的绝对编号，也可能是每季重置的相对编号
- virtual_season_starts 表示因长时间停播（>6个月）产生的虚季分界点，集号可能在此处重置

判断规则：
1. 若从标题解析的季号 > TMDB 总季数，偏移到最后一季
2. 若季号合法但集号超出该季集数，结合 virtual_season_starts 计算 episode_offset
3. 仅在 TMDB 数据明确支持时给出偏移，不确定时默认无偏移（has_mismatch=false）
4. season_offset 为负表示实际季号比解析值小

输出 JSON 字段：
- has_mismatch: bool
- season_offset: int
- episode_offset: int
- reason: string（中文解释）
- confidence: "high"|"medium"|"low"

你必须只输出一个 JSON 对象，不要输出其他任何内容。"""


def build_ai_offset_message(
    request: AIDetectOffsetRequest, tmdb_info
) -> str:
    """Build the user message for AI offset detection with TMDB data."""
    parts = [
        f"Title: {request.title}",
    ]
    if request.first_title:
        parts.append(f"First RSS episode title: {request.first_title}")
    parts.extend([
        "",
        "=== TMDB Metadata ===",
        f"Official title: {tmdb_info.title}",
        f"Total seasons: {tmdb_info.last_season}",
        f"Series status: {tmdb_info.series_status or 'unknown'}",
    ])

    if tmdb_info.season_episode_counts:
        parts.append("Season episode counts:")
        for season, count in sorted(tmdb_info.season_episode_counts.items()):
            parts.append(f"  Season {season}: {count} episodes")

    if tmdb_info.virtual_season_starts:
        parts.append("Virtual season start episodes:")
        for season, starts in sorted(tmdb_info.virtual_season_starts.items()):
            parts.append(f"  Season {season}: starts at episodes {starts}")

    parts.append("")
    parts.append("Based on TMDB data, determine if an offset is needed.")
    return "\n".join(parts)
