import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from module.conf import settings
from module.database import Database
from module.manager import TorrentManager
from module.models import APIResponse, Bangumi, BangumiUpdate
from module.parser.analyser.offset_detector import (
    OffsetSuggestion as DetectorSuggestion,
)
from module.parser.analyser.offset_detector import detect_offset_mismatch
from module.parser.analyser.openai import OpenAIParser
from module.parser.analyser.tmdb_parser import tmdb_parser
from module.security.api import UNAUTHORIZED, get_current_user

from .response import u_response

# Late import to avoid circular dependency with ai_offset
from .ai_offset import AIDetectOffsetRequest, build_ai_offset_message, build_ai_offset_prompt

logger = logging.getLogger(__name__)


class OffsetSuggestion(BaseModel):
    """Legacy offset suggestion model."""
    suggested_offset: int
    reason: str


class TMDBSummary(BaseModel):
    """Summary of TMDB data for display."""
    title: str
    total_seasons: int
    season_episode_counts: dict[int, int]
    status: Optional[str]
    virtual_season_starts: Optional[dict[int, list[int]]] = None  # {1: [1, 29], ...}


class OffsetSuggestionDetail(BaseModel):
    """Detailed offset suggestion from detector."""
    season_offset: int
    episode_offset: int = 0
    reason: str
    confidence: Literal["high", "medium", "low"]


class SetWeekdayRequest(BaseModel):
    weekday: Optional[int] = None  # 0-6 for Mon-Sun, None to reset


class DetectOffsetRequest(BaseModel):
    """Request body for detect-offset endpoint."""
    title: str
    parsed_season: int
    parsed_episode: int


class DetectOffsetResponse(BaseModel):
    """Response for detect-offset endpoint."""
    has_mismatch: bool
    suggestion: Optional[OffsetSuggestionDetail]
    tmdb_info: Optional[TMDBSummary]


class AIOffsetResult(BaseModel):
    """Structured output from LLM for AI offset detection."""
    has_mismatch: bool
    season_offset: int = 0
    episode_offset: int = 0
    reason: str = ""
    confidence: Literal["high", "medium", "low"] = "medium"


class AIDetectOffsetResponse(BaseModel):
    """Response for AI detect-offset endpoint."""
    has_mismatch: bool
    suggestion: Optional[OffsetSuggestionDetail] = None
    ai_analysis: Optional[str] = None
    tmdb_info: Optional[TMDBSummary] = None
    error: Optional[str] = None


router = APIRouter(prefix="/bangumi", tags=["bangumi"])


def str_to_list(data: Bangumi):
    data.filter = data.filter.split(",")
    data.rss_link = data.rss_link.split(",")
    return data


@router.get(
    "/get/all", response_model=list[Bangumi], dependencies=[Depends(get_current_user)]
)
async def get_all_data():
    with TorrentManager() as manager:
        return manager.bangumi.search_all()


@router.get(
    "/get/{bangumi_id}",
    response_model=Bangumi,
    dependencies=[Depends(get_current_user)],
)
async def get_data(bangumi_id: str):
    with TorrentManager() as manager:
        resp = manager.search_one(bangumi_id)
    return resp


@router.patch(
    "/update/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def update_rule(
    bangumi_id: int,
    data: BangumiUpdate,
):
    with TorrentManager() as manager:
        resp = await manager.update_rule(bangumi_id, data)
    return u_response(resp)


@router.delete(
    path="/delete/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_rule(bangumi_id: str, file: bool = False):
    with TorrentManager() as manager:
        resp = await manager.delete_rule(bangumi_id, file)
    return u_response(resp)


@router.delete(
    path="/delete/many/",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_many_rule(bangumi_id: list, file: bool = False):
    with TorrentManager() as manager:
        for i in bangumi_id:
            resp = await manager.delete_rule(i, file)
    return u_response(resp)


@router.delete(
    path="/disable/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def disable_rule(bangumi_id: str, file: bool = False):
    with TorrentManager() as manager:
        resp = await manager.disable_rule(bangumi_id, file)
    return u_response(resp)


@router.delete(
    path="/disable/many/",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def disable_many_rule(bangumi_id: list, file: bool = False):
    with TorrentManager() as manager:
        for i in bangumi_id:
            resp = await manager.disable_rule(i, file)
    return u_response(resp)


@router.get(
    path="/enable/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def enable_rule(bangumi_id: str):
    with TorrentManager() as manager:
        resp = manager.enable_rule(bangumi_id)
    return u_response(resp)


@router.get(
    path="/refresh/poster/all",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_poster_all():
    with TorrentManager() as manager:
        resp = await manager.refresh_poster()
    return u_response(resp)

@router.get(
    path="/refresh/poster/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_poster_one(bangumi_id: int):
    with TorrentManager() as manager:
        resp = await manager.refind_poster(bangumi_id)
    return u_response(resp)


@router.get(
    path="/refresh/calendar",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_calendar():
    with TorrentManager() as manager:
        resp = await manager.refresh_calendar()
    return u_response(resp)


@router.get(
    "/reset/all", response_model=APIResponse, dependencies=[Depends(get_current_user)]
)
async def reset_all():
    with TorrentManager() as manager:
        manager.bangumi.delete_all()
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Reset all rules successfully.", "msg_zh": "重置所有规则成功。"},
        )


@router.patch(
    path="/archive/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def archive_rule(bangumi_id: int):
    """Archive a bangumi."""
    with TorrentManager() as manager:
        resp = manager.archive_rule(bangumi_id)
    return u_response(resp)


@router.patch(
    path="/unarchive/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def unarchive_rule(bangumi_id: int):
    """Unarchive a bangumi."""
    with TorrentManager() as manager:
        resp = manager.unarchive_rule(bangumi_id)
    return u_response(resp)


@router.get(
    path="/refresh/metadata",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_metadata():
    """Refresh TMDB metadata and auto-archive ended series."""
    with TorrentManager() as manager:
        resp = await manager.refresh_metadata()
    return u_response(resp)


@router.get(
    path="/suggest-offset/{bangumi_id}",
    response_model=OffsetSuggestion,
    dependencies=[Depends(get_current_user)],
)
async def suggest_offset(bangumi_id: int):
    """Suggest offset based on TMDB episode counts."""
    with TorrentManager() as manager:
        resp = await manager.suggest_offset(bangumi_id)
    return resp


@router.post(
    path="/detect-offset",
    response_model=DetectOffsetResponse,
    dependencies=[Depends(get_current_user)],
)
async def detect_offset(request: DetectOffsetRequest):
    """Detect season/episode mismatch with TMDB data.

    Called by frontend before adding/subscribing to check if offsets are needed.
    """
    language = settings.rss_parser.language
    tmdb_info = await tmdb_parser(request.title, language)

    if not tmdb_info:
        return DetectOffsetResponse(
            has_mismatch=False,
            suggestion=None,
            tmdb_info=None,
        )

    # Detect mismatch
    suggestion = detect_offset_mismatch(
        parsed_season=request.parsed_season,
        parsed_episode=request.parsed_episode,
        tmdb_info=tmdb_info,
    )

    # Build TMDB summary
    tmdb_summary = TMDBSummary(
        title=tmdb_info.title,
        total_seasons=tmdb_info.last_season,
        season_episode_counts=tmdb_info.season_episode_counts or {},
        status=tmdb_info.series_status,
        virtual_season_starts=tmdb_info.virtual_season_starts,
    )

    if suggestion:
        return DetectOffsetResponse(
            has_mismatch=True,
            suggestion=OffsetSuggestionDetail(
                season_offset=suggestion.season_offset,
                episode_offset=suggestion.episode_offset or 0,
                reason=suggestion.reason,
                confidence=suggestion.confidence,
            ),
            tmdb_info=tmdb_summary,
        )

    return DetectOffsetResponse(
        has_mismatch=False,
        suggestion=None,
        tmdb_info=tmdb_summary,
    )


@router.post(
    path="/detect-offset/ai",
    response_model=AIDetectOffsetResponse,
    dependencies=[Depends(get_current_user)],
)
async def detect_offset_ai(request: AIDetectOffsetRequest):
    """Detect season/episode mismatch using AI/LLM with TMDB data.

    Queries TMDB for series metadata, then uses the configured
    OpenAI-compatible model to analyze the title and parsed
    season/episode against the TMDB data for potential offsets.
    """
    # Check if AI is enabled
    openai_config = settings.experimental_openai
    if not openai_config.enable:
        return AIDetectOffsetResponse(
            has_mismatch=False,
            error="AI detection is not enabled",
        )

    if not openai_config.api_key:
        return AIDetectOffsetResponse(
            has_mismatch=False,
            error="API key not configured",
        )

    # Query TMDB
    language = settings.rss_parser.language
    tmdb_info = await tmdb_parser(request.title, language)

    if not tmdb_info:
        return AIDetectOffsetResponse(
            has_mismatch=False,
            suggestion=None,
            tmdb_info=None,
            error="No TMDB data found for this title",
        )

    # Build TMDB summary (consistent with auto-detect endpoint)
    tmdb_summary = TMDBSummary(
        title=tmdb_info.title,
        total_seasons=tmdb_info.last_season,
        season_episode_counts=tmdb_info.season_episode_counts or {},
        status=tmdb_info.series_status,
        virtual_season_starts=tmdb_info.virtual_season_starts,
    )

    # Build prompt with TMDB data
    prompt = build_ai_offset_prompt()
    user_message = build_ai_offset_message(request, tmdb_info)

    try:
        parser = OpenAIParser(
            api_key=openai_config.api_key,
            api_base=openai_config.api_base,
            model=openai_config.model,
            api_type=openai_config.api_type,
            api_version=openai_config.api_version,
            deployment_id=openai_config.deployment_id,
        )

        result = await parser.parse(
            text=user_message,
            prompt=prompt,
            asdict=True,
        )

        if not isinstance(result, dict):
            return AIDetectOffsetResponse(
                has_mismatch=False,
                tmdb_info=tmdb_summary,
                error="Failed to parse AI response",
            )

        ai_result = AIOffsetResult.model_validate(result)

        response = AIDetectOffsetResponse(
            has_mismatch=ai_result.has_mismatch,
            ai_analysis=ai_result.reason,
            tmdb_info=tmdb_summary,
        )

        if ai_result.has_mismatch:
            response.suggestion = OffsetSuggestionDetail(
                season_offset=ai_result.season_offset,
                episode_offset=ai_result.episode_offset,
                reason=ai_result.reason,
                confidence=ai_result.confidence,
            )

        return response

    except Exception as e:
        logger.error(f"AI offset detection failed: {e}")
        return AIDetectOffsetResponse(
            has_mismatch=False,
            tmdb_info=tmdb_summary,
            error=str(e),
        )


@router.post(
    path="/dismiss-review/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def dismiss_review(bangumi_id: int):
    """Clear the needs_review flag for a bangumi after user reviews."""
    with Database() as db:
        success = db.bangumi.clear_needs_review(bangumi_id)

    if success:
        return JSONResponse(
            status_code=200,
            content={
                "status": True,
                "msg_en": "Review dismissed.",
                "msg_zh": "已取消检查标记。",
            },
        )
    else:
        return JSONResponse(
            status_code=404,
            content={
                "status": False,
                "msg_en": f"Bangumi {bangumi_id} not found.",
                "msg_zh": f"未找到番剧 {bangumi_id}。",
            },
        )


@router.get(
    path="/needs-review",
    response_model=list[Bangumi],
    dependencies=[Depends(get_current_user)],
)
async def get_needs_review():
    """Get all bangumi that need review for offset mismatch."""
    with Database() as db:
        return db.bangumi.get_needs_review()


@router.patch(
    path="/{bangumi_id}/weekday",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def set_weekday(bangumi_id: int, request: SetWeekdayRequest):
    """Manually set the broadcast weekday for a bangumi."""
    if request.weekday is not None and not (0 <= request.weekday <= 6):
        return JSONResponse(
            status_code=400,
            content={
                "status": False,
                "msg_en": "Weekday must be 0-6 (Mon-Sun) or null.",
                "msg_zh": "星期必须是 0-6（周一至周日）或空。",
            },
        )
    with Database() as db:
        success = db.bangumi.set_weekday(bangumi_id, request.weekday)
    if success:
        action = f"weekday {request.weekday}" if request.weekday is not None else "unknown"
        return JSONResponse(
            status_code=200,
            content={
                "status": True,
                "msg_en": f"Set bangumi to {action}.",
                "msg_zh": f"已设置放送日为 {action}。",
            },
        )
    return JSONResponse(
        status_code=404,
        content={
            "status": False,
            "msg_en": f"Bangumi {bangumi_id} not found.",
            "msg_zh": f"未找到番剧 {bangumi_id}。",
        },
    )
