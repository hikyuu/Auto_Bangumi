"""集成测试：qBittorrent 重命名功能真机测试。

使用步骤：
    cd backend
    python ../scripts/test_rename_integration.py

测试流程：
    1. 连接 qBittorrent (192.168.31.66:8080)
    2. 从 Mikan RSS 获取第一集种子
    3. 添加种子到 X:\test，打上 ab:99999 标签
    4. 等待种子文件条目出现
    5. 立即调用 torrents_rename_file 进行重命名
    6. 验证重命名结果
"""

import asyncio
import logging
import re
import sys
import time
from pathlib import Path
from unittest.mock import patch

# ── 设置基本日志 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("rename_test")

# ── 依赖检查 ──────────────────────────────────────────────────
try:
    import httpx
    from bs4 import BeautifulSoup
except ImportError:
    print("需要安装 httpx 和 beautifulsoup4: pip install httpx beautifulsoup4")
    sys.exit(1)

# ── 配置 ──────────────────────────────────────────────────────
QB_HOST = "192.168.31.66:8080"
QB_USER = "hikyuu"
QB_PASS = "coffee2008"
QB_SSL = False
SAVE_DIR = r"X:\test"
RSS_URL = "https://mikanani.me/RSS/Bangumi?bangumiId=3969&subgroupid=583"

# ── 项目路径 ──────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from module.downloader.client.qb_downloader import QbDownloader


# ── RSS 解析（简化版，不依赖项目完整依赖链） ────────────────────

async def fetch_rss_torrents(rss_url: str, limit: int = 1) -> list[dict]:
    """从 Mikan RSS 获取前 N 个种子条目。"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(rss_url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "xml")
    items = soup.find_all("item")

    torrents = []
    for item in items:
        title = item.find("title").text.strip()
        enclosure = item.find("enclosure")
        torrent_url = enclosure["url"] if enclosure else ""
        link_tag = item.find("link")
        homepage = link_tag.text.strip() if link_tag else ""

        torrents.append({
            "name": title,
            "url": torrent_url,
            "homepage": homepage,
        })

        if len(torrents) >= limit:
            break

    return torrents


# ── 重命名测试核心 ────────────────────────────────────────────

async def main():
    logger.info("=" * 60)
    logger.info("qBittorrent 重命名集成测试")
    logger.info("=" * 60)

    # 1. 连接 qBittorrent
    logger.info("连接 qBittorrent: %s ...", QB_HOST)
    qb = QbDownloader(host=QB_HOST, username=QB_USER, password=QB_PASS, ssl=QB_SSL)
    auth_ok = await qb.auth()
    if not auth_ok:
        logger.error("❌ qBittorrent 认证失败！")
        logger.error("   请检查: IP/端口是否正确, 用户名密码是否正确, qBittorrent 是否在运行")
        return
    logger.info("✅ 认证成功")

    # 2. 获取 RSS 种子
    logger.info("获取 RSS: %s", RSS_URL)
    try:
        torrents = await fetch_rss_torrents(RSS_URL, limit=1)
    except Exception as e:
        logger.error("❌ RSS 获取失败: %s", e)
        await qb.logout()
        return

    if not torrents:
        logger.error("❌ RSS 中没有找到种子")
        await qb.logout()
        return

    t = torrents[0]
    logger.info("📥 种子: %s", t["name"])

    # 3. 解析种子标题，预览重命名
    ep_match = re.search(r"(\d{1,3}(?:\.\d)?)", t["name"])
    season_match = re.search(r"[Ss](\d{1,2})|第(\d+)季|[第\s](\d+)[季期]", t["name"])
    episode_num = int(ep_match.group(1)) if ep_match else 0
    season_num = 1
    if season_match:
        for g in season_match.groups():
            if g:
                season_num = int(g)
                break

    logger.info("  解析: Season=%d, Episode=%d", season_num, episode_num)

    # 4. 确认操作
    logger.info("-" * 60)
    logger.info("即将执行:")
    logger.info("  1. 添加种子到 qBittorrent, 保存到 %s", SAVE_DIR)
    logger.info("  2. 自动开始下载")
    logger.info("  3. 文件条目一出现就立即重命名并验证结果")

    # 5. 添加种子
    logger.info("-" * 60)
    logger.info("添加种子到 qBittorrent ...")

    try:
        added = await qb.add_torrents(
            torrent_urls=t["url"],
            torrent_files=None,
            save_path=SAVE_DIR,
            category="Bangumi",
            tags="ab:99999",
        )
    except Exception as e:
        logger.error("❌ 添加种子失败: %s", e)
        await qb.logout()
        return

    if not added:
        logger.warning("种子可能已存在（返回非 Ok.），继续尝试测试...")
    else:
        logger.info("✅ 种子已添加，开始下载")

    # 6. 等待文件条目出现，立即重命名
    logger.info("-" * 60)
    logger.info("等待种子文件条目出现 (最多等待 10 分钟)...")

    await asyncio.sleep(5)  # 给 qBittorrent 一点时间注册种子
    torrent_hash = None
    old_path = None
    max_wait = 600
    poll_interval = 5
    waited = 0
    rename_done = False

    while waited < max_wait:
        try:
            info_list = await qb.torrents_info(
                status_filter=None, category="Bangumi"
            )
        except Exception:
            await asyncio.sleep(poll_interval)
            waited += poll_interval
            continue

        # 找到目标种子
        target_info = None
        for info in info_list:
            if info.get("tags", "").find("ab:99999") >= 0:
                target_info = info
                torrent_hash = info["hash"]
                break

        if target_info is None:
            logger.info("  [%s] 等待种子出现...", waited)
            await asyncio.sleep(poll_interval)
            waited += poll_interval
            continue

        torrent_name = target_info.get("name", "?")
        state = target_info.get("state", "unknown")

        # 尝试获取文件列表
        try:
            files = await qb.torrents_files(torrent_hash)
        except Exception:
            files = None

        if files:
            media_files = [
                f["name"] for f in files
                if f["name"].lower().endswith((".mp4", ".mkv"))
            ]
            logger.info(
                "  [%s] %s (state: %s)  files: %s",
                waited, torrent_name[:50], state,
                media_files or f"(共 {len(files)} 个文件)"
            )

            if media_files:
                # ── 文件出现 → 立即重命名 ──
                old_path = media_files[0]
                ep_str = f"0{episode_num}" if episode_num < 10 else str(episode_num)
                ss_str = f"0{season_num}" if season_num < 10 else str(season_num)
                new_path = f"Test Anime S{ss_str}E{ep_str}{Path(old_path).suffix}"

                logger.info("-" * 60)
                logger.info("🔄 文件已出现! 立即执行重命名（state: %s）", state)
                logger.info("  old: %s", old_path)
                logger.info("  new: %s", new_path)

                result = await qb.torrents_rename_file(
                    torrent_hash=torrent_hash,
                    old_path=old_path,
                    new_path=new_path,
                    verify=True,
                )
                if result:
                    logger.info("✅ 重命名成功")

                    # 验证：重新拉取文件列表确认
                    files_after = await qb.torrents_files(torrent_hash)
                    names_after = [f["name"] for f in files_after] if files_after else []
                    if new_path in names_after:
                        logger.info("✅ 验证通过: 文件已重命名为 '%s'", new_path)
                    elif old_path not in names_after:
                        logger.info("⚠️ 旧文件名已消失但新文件名未出现")
                    else:
                        logger.warning("⚠️ 文件名未变: '%s'", old_path)
                else:
                    logger.error("❌ 重命名失败")
                break  # 无论成功与否，结束测试
        else:
            logger.info(
                "  [%s] %s (state: %s)  等待文件条目...",
                waited, torrent_name[:50], state
            )

        await asyncio.sleep(poll_interval)
        waited += poll_interval
    else:
        logger.error("❌ 等待超时")
        await qb.logout()
        return

    if not torrent_hash:
        logger.error("❌ 未找到种子 hash")
        await qb.logout()
        return

    # 7. 清理
    logger.info("-" * 60)
    logger.info("完成。种子 hash: %s (保留在 qBittorrent 中，请手动管理)", torrent_hash)
    await qb.logout()


if __name__ == "__main__":
    asyncio.run(main())
