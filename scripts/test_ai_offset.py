"""测试脚本：测试 AI 偏移量检测

用法: python scripts/test_ai_offset.py

流程:
1. 尝试调用 /rss/analysis 解析 RSS（失败则用硬编码标题）
2. 调用 POST /api/v1/bangumi/detect-offset/ai 测试 AI 检测
"""

import sys

import requests

BASE = "http://localhost:7892/api/v1"
RSS_URL = "https://mikanani.me/RSS/Bangumi?bangumiId=3952&subgroupid=583"

# 硬编码测试数据，确保 /rss/analysis 不可用时也能测试
FALLBACK_TITLE = "关于我转生变成史莱姆这档事"
FALLBACK_SEASON = 4
FALLBACK_EPISODE = 84


def analyse_rss():
    """尝试调用 /rss/analysis，失败则用硬编码数据"""
    print(f"[1/2] 解析 RSS: {RSS_URL}")
    try:
        resp = requests.post(
            f"{BASE}/rss/analysis",
            json={"url": RSS_URL, "name": "test", "parser": "mikan"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        title = data.get("official_title", "")
        season = data.get("season", 1)
        print(f"  official_title: {title}")
        print(f"  season: {season}")
        return title, season
    except Exception as e:
        print(f"  /rss/analysis 不可用 ({e})")
        print(f"  使用硬编码: {FALLBACK_TITLE} S{FALLBACK_SEASON}E{FALLBACK_EPISODE}")
        return FALLBACK_TITLE, FALLBACK_SEASON


def test_ai_detect(title: str, season: int):
    """调用 /detect-offset/ai"""
    print(f"\n[2/2] AI 偏移量检测")
    print(f"  title={title}, season={season}, episode={FALLBACK_EPISODE}")
    resp = requests.post(
        f"{BASE}/bangumi/detect-offset/ai",
        json={
            "title": title,
            "parsed_season": season,
            "parsed_episode": FALLBACK_EPISODE,
        },
        timeout=120,
    )
    resp.raise_for_status()
    result = resp.json()

    print(f"  has_mismatch: {result.get('has_mismatch')}")
    if result.get("error"):
        print(f"  error: {result['error']}")
    if result.get("suggestion"):
        s = result["suggestion"]
        print(f"  season_offset: {s['season_offset']}")
        print(f"  episode_offset: {s['episode_offset']}")
        print(f"  confidence: {s['confidence']}")
        print(f"  reason: {s['reason']}")
    if result.get("tmdb_info"):
        t = result["tmdb_info"]
        print(f"  TMDB: {t['title']} ({t['total_seasons']} seasons, status={t.get('status')})")
        for sn, cnt in sorted((t.get("season_episode_counts") or {}).items()):
            print(f"    S{sn}: {cnt} episodes")
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("Auto_Bangumi AI 偏移量检测测试")
    print("=" * 60)

    try:
        title, season = analyse_rss()
        test_ai_detect(title, season)
        print("\n✅ 测试完成")
    except requests.exceptions.ConnectionError:
        print("\n✗ 无法连接服务器 (http://localhost:7892)")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
