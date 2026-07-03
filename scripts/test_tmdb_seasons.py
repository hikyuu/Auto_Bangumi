"""测试脚本：查询 TMDB 中《关于我转生变成史莱姆这档事》的分季数据。

使用方法：在 backend 目录下运行
    cd backend
    pip install httpx
    python ../scripts/test_tmdb_seasons.py
"""

import asyncio
import datetime
import json

import httpx

TMDB_API = "32b19d6a05b512190a056fa4e747cbbc"
TMDB_URL = "https://api.themoviedb.org"
LANGUAGE = {"zh": "zh-CN", "jp": "ja-JP", "en": "en-US"}


# ─── 复制项目中的虚拟分季检测逻辑 ─────────────────────────────

def detect_virtual_seasons(episodes: list[dict], gap_months: int = 6) -> list[int]:
    """检测播出间隔 > gap_months 的虚拟分季点。"""
    if len(episodes) < 2:
        return [1] if episodes else []

    virtual_season_starts = [1]
    gap_days = gap_months * 30

    for i in range(1, len(episodes)):
        prev = episodes[i - 1]
        curr = episodes[i]
        days_diff = (curr["air_date"] - prev["air_date"]).days
        if days_diff > gap_days:
            virtual_season_starts.append(curr["episode_number"])
            print(f"    ⚡ 虚拟分季点: EP{prev['episode_number']} → EP{curr['episode_number']} "
                  f"间隔 {days_diff} 天 （>{gap_days} 天）")

    return virtual_season_starts


# ─── 查询 TMDB ───────────────────────────────────────────────

async def main():
    title = "关于我转生变成史莱姆这档事"
    print(f"🔍 搜索: {title}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. 搜索番剧
        search_url = f"{TMDB_URL}/3/search/tv"
        r = await client.get(search_url, params={
            "api_key": TMDB_API, "query": title,
            "language": "zh-CN", "include_adult": "false"
        })
        results = r.json().get("results", [])
        if not results:
            print("❌ 未找到")
            return

        tv_id = results[0]["id"]
        print(f"✅ 匹配: {results[0]['name']} (TMDB ID: {tv_id})")
        print(f"   原名: {results[0]['original_name']}")
        print(f"   首播: {results[0]['first_air_date']}")
        print()

        # 2. 获取番剧详情（含所有季信息）
        info_url = f"{TMDB_URL}/3/tv/{tv_id}"
        r = await client.get(info_url, params={
            "api_key": TMDB_API, "language": "zh-CN"
        })
        info = r.json()

        total_seasons = info["number_of_seasons"]
        total_episodes = info["number_of_episodes"]
        status = info["status"]
        seasons = info["seasons"]

        print(f"{'='*60}")
        print(f"📺 番剧概况")
        print(f"{'='*60}")
        print(f"  总季数: {total_seasons} 季")
        print(f"  总集数: {total_episodes} 集")
        print(f"  状态:   {status}")
        print()

        # 按 season_number 排序
        seasons_sorted = sorted(seasons, key=lambda s: s["season_number"])

        print(f"{'='*60}")
        print(f"📋 TMDB 各季数据")
        print(f"{'='*60}")

        for s in seasons_sorted:
            sn = s["season_number"]
            label = " (特别篇/OVA)" if sn == 0 else ""
            print(f"\n  S{sn}{label}: {s['name']}")
            print(f"    集数: {s['episode_count']}")
            print(f"    上线: {s.get('air_date', 'N/A')}")

        # 3. 查询每季的逐集播出日期，检测虚拟分季
        print(f"\n{'='*60}")
        print(f"🔬 虚拟分季检测（播出间隔 > 6 个月）")
        print(f"{'='*60}")

        for s in seasons_sorted:
            sn = s["season_number"]
            if sn == 0:
                continue  # 跳过特别篇

            season_url = f"{TMDB_URL}/3/tv/{tv_id}/season/{sn}"
            r = await client.get(season_url, params={
                "api_key": TMDB_API, "language": "zh-CN"
            })
            season_data = r.json()

            episodes = []
            for ep in season_data.get("episodes", []):
                ep_num = ep.get("episode_number")
                air_date_str = ep.get("air_date")
                if ep_num and air_date_str:
                    try:
                        air_date = datetime.date.fromisoformat(air_date_str)
                        episodes.append({
                            "episode_number": ep_num,
                            "air_date": air_date,
                        })
                    except ValueError:
                        pass

            episodes.sort(key=lambda x: x["episode_number"])
            print(f"\n  S{sn} — {len(episodes)} 集有播出日期数据")

            vs_starts = detect_virtual_seasons(episodes)
            if len(vs_starts) > 1:
                print(f"    ✅ 检测到 {len(vs_starts)} 个虚拟分季段")
                for i, start in enumerate(vs_starts):
                    label = f"第{i+1}段"
                    matching_ep = next((e for e in episodes if e["episode_number"] == start), None)
                    date_str = matching_ep["air_date"].isoformat() if matching_ep else "?"
                    print(f"       {label}: 从 EP{start} 开始 ({date_str})")
            else:
                print(f"    ❌ 未检测到虚拟分季（无超过 6 个月的播出间隔）")

        # 4. 总结
        print(f"\n{'='*60}")
        print(f"📊 总结")
        print(f"{'='*60}")
        print(f"  TMDB 官方分季:")

        regular_seasons = [s for s in seasons_sorted if s["season_number"] > 0]
        for s in regular_seasons:
            sn = s["season_number"]
            ep_count = s["episode_count"]
            air_date = s.get("air_date", "?")
            print(f"    S{sn}: {ep_count} 集  ({air_date})")

        print(f"\n  对于 Auto_Bangumi 偏移计算:")
        print(f"    get_season() 返回 last_season = {len(regular_seasons)}")
        for i, s in enumerate(regular_seasons):
            sn = s["season_number"]
            cumulative = sum(s2["episode_count"] for s2 in regular_seasons[:i])
            print(f"    get_offset_for_season({sn}) = -{cumulative}")


if __name__ == "__main__":
    asyncio.run(main())
