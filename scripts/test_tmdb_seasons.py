"""测试脚本：查询指定番剧的 TMDB 季/集信息

用法:
    python scripts/test_tmdb_seasons.py TMDB_ID [season_number]
    python scripts/test_tmdb_seasons.py TMDB_ID 1 2 3

示例:
    python scripts/test_tmdb_seasons.py 82695           # 查看某番剧全部季数信息
    python scripts/test_tmdb_seasons.py 82695 1 2       # 查看第 1、2 季详情
    python scripts/test_tmdb_seasons.py 205646          # 物语系列 Off Season
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from module.conf import settings


async def main():
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} TMDB_ID [season_number ...]")
        print(f"示例: {sys.argv[0]} 82695")
        print(f"示例: {sys.argv[0]} 82695 1 2")
        sys.exit(1)

    tmdb_id = int(sys.argv[1])
    season_filter = [int(s) for s in sys.argv[2:]] if len(sys.argv) > 2 else None

    api_key = settings.tmdb.api_key
    if not api_key:
        print("❌ 未配置 TMDB API Key")
        print("   请在 config.yaml 中设置 tmdb.api_key")
        sys.exit(1)

    print("=" * 60)
    print(f"TMDB ID: {tmdb_id}")
    print(f"API Key: {api_key[:8]}...")
    if season_filter:
        print(f"过滤季数: {season_filter}")
    print("=" * 60)

    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        # 获取 TV 详情
        url = f"https://api.themoviedb.org/3/tv/{tmdb_id}"
        resp = await client.get(url, params={"api_key": api_key, "language": "zh-CN"})
        resp.raise_for_status()
        tv_data = resp.json()

        print(f"\n📺 {tv_data.get('name', '?')} / {tv_data.get('original_name', '?')}")
        print(f"   类型: {tv_data.get('type', '?')}")
        print(f"   状态: {tv_data.get('status', '?')}")
        print(f"   总季数: {tv_data.get('number_of_seasons', '?')}")
        print(f"   总集数: {tv_data.get('number_of_episodes', '?')}")
        print(f"   TMDB 评分: {tv_data.get('vote_average', '?')}")

        # 获取所有季信息
        seasons = tv_data.get("seasons", [])
        if not seasons:
            print("\n❌ 未找到季信息")
            return

        print(f"\n{'─' * 60}")
        print(f"{'Season':<8} {'集数':<6} {'年份':<8} {'TMDB ID':<10} {'名称'}")
        print(f"{'─' * 60}")

        for s in seasons:
            sn = s.get("season_number", 0)
            if sn == 0:
                continue  # 跳过"特别篇"
            if season_filter and sn not in season_filter:
                continue
            ep_count = s.get("episode_count", "?")
            air_date = (s.get("air_date") or "????")[:4]
            svid = s.get("id", "?")
            sname = s.get("name", "?")
            print(f"S{sn:<6} {ep_count:<6} {air_date:<8} {svid:<10} {sname}")

        # 如果指定了赛季号，获取详细集信息
        target_seasons = season_filter or [s["season_number"] for s in seasons if s.get("season_number", 0) > 0]
        for sn in target_seasons:
            print(f"\n{'─' * 60}")
            print(f"Season {sn} - 详细集信息:")
            url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{sn}"
            resp = await client.get(url, params={"api_key": api_key, "language": "zh-CN"})
            resp.raise_for_status()
            season_data = resp.json()

            episodes = season_data.get("episodes", [])
            print(f"  {'EP':<6} {'名称':<40} {'TMDB 集号 (absolute)'}")
            print(f"  {'─' * 70}")
            for ep in episodes:
                ep_num = ep.get("episode_number", "?")
                ep_name = (ep.get("name") or "?")[:38]
                abs_num = ep.get("show_id", "?")  # maybe not there
                # Find absolute number - TMDB doesn't give it in season endpoint
                print(f"  EP-{ep_num:<4} {ep_name:<40} S{sn}E{ep_num}")

    print(f"\n{'=' * 60}")
    print("TMDB Season Info (for offset calculation)")
    print("season_number -> episode_count mapping:")
    for s in seasons:
        sn = s.get("season_number", 0)
        if sn == 0:
            continue
        ep_count = s.get("episode_count", 0)
        print(f"  Season {sn}: {ep_count} episodes")


if __name__ == "__main__":
    asyncio.run(main())
