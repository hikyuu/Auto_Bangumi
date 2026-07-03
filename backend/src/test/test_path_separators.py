"""Tests for path separator normalization in TorrentPath methods.

These tests verify that Windows-style paths (backslash separators) are
correctly handled regardless of the host OS. On Linux/Unix, pathlib
treats backslashes as literal filename characters, so we normalize
``\\``→``/`` before calling ``Path()``.
"""

import pytest
from unittest.mock import patch

from module.downloader.path import TorrentPath
from module.models import Bangumi

from test.factories import make_bangumi


# ---------------------------------------------------------------------------
# _path_to_bangumi — path separator normalization
# ---------------------------------------------------------------------------


class TestPathToBangumiSeparators:
    """``_path_to_bangumi`` should normalize ``\\``→``/`` before pathlib parsing."""

    def test_windows_backslash_path(self):
        """Windows path with backslashes extracts correct name and season."""
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            tp = TorrentPath()
            name, season = tp._path_to_bangumi(
                r"X:\video\anime\My Anime\Season 4"
            )

        assert name == "My Anime"
        assert season == 4

    def test_mixed_separators(self):
        """Mixed ``/`` and ``\\`` in save_path are handled correctly."""
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            tp = TorrentPath()
            name, season = tp._path_to_bangumi(
                r"X:/video\anime/My Anime\Season 4"
            )

        assert name == "My Anime"
        assert season == 4

    def test_windows_s_prefix_season(self):
        """S01-style season folder with Windows backslashes."""
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            tp = TorrentPath()
            name, season = tp._path_to_bangumi(
                r"X:\video\anime\Anime\S03"
            )

        assert season == 3

    def test_no_season_folder_defaults_to_1_windows(self):
        """When path has no Season folder, defaults to 1 (Windows-style path)."""
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            tp = TorrentPath()
            name, season = tp._path_to_bangumi(
                r"X:\video\anime\My Anime (2024)"
            )

        assert name == "My Anime (2024)"
        assert season == 1

    def test_windows_download_path(self):
        """When settings.downloader.path itself uses backslashes."""
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = r"X:\video\anime"
            tp = TorrentPath()
            name, season = tp._path_to_bangumi(
                r"X:\video\anime\Slime\Season 4"
            )

        assert name == "Slime"
        assert season == 4

    def test_bangumi_with_chinese_characters_windows(self):
        """Chinese folder names with Windows backslash separators."""
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            tp = TorrentPath()
            name, season = tp._path_to_bangumi(
                r"X:\video\anime\关于我转生变成史莱姆这档事\Season 4"
            )

        assert name == "关于我转生变成史莱姆这档事"
        assert season == 4

    def test_unix_path_still_works(self):
        """Unix-style paths (forward slashes) still work as before."""
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            tp = TorrentPath()
            name, season = tp._path_to_bangumi(
                "/downloads/Bangumi/My Anime (2024)/Season 2"
            )

        assert name == "My Anime (2024)"
        assert season == 2


# ---------------------------------------------------------------------------
# _file_depth — path separator normalization
# ---------------------------------------------------------------------------


class TestFileDepthSeparators:
    """``_file_depth`` should normalize ``\\``→``/`` before counting parts."""

    def test_windows_path_depth(self):
        """Windows backslash path has correct depth."""
        tp = TorrentPath()
        depth = tp._file_depth(r"Season 4\episode.mkv")
        assert depth == 2

    def test_mixed_separators_depth(self):
        """Mixed separators in path produce correct depth."""
        tp = TorrentPath()
        depth = tp._file_depth(r"a/b\c/file.mkv")
        assert depth == 4

    def test_windows_single_component(self):
        """Single filename on Windows is depth 1."""
        tp = TorrentPath()
        depth = tp._file_depth(r"episode.mkv")
        assert depth == 1

    def test_unix_path_depth_still_works(self):
        """Unix path depth still correct."""
        tp = TorrentPath()
        depth = tp._file_depth("a/b/c/file.mkv")
        assert depth == 4


# ---------------------------------------------------------------------------
# is_ep — path separator normalization (via _file_depth)
# ---------------------------------------------------------------------------


class TestIsEpSeparators:
    """``is_ep`` should work with Windows backslash paths."""

    def test_windows_shallow_file(self):
        """Single file with Windows path is still an episode."""
        tp = TorrentPath()
        assert tp.is_ep(r"episode.mkv") is True

    def test_windows_one_folder_deep(self):
        """One folder deep with Windows path is still an episode."""
        tp = TorrentPath()
        assert tp.is_ep(r"Season 4\episode.mkv") is True

    def test_windows_too_deep(self):
        """Too deep Windows path is NOT an episode."""
        tp = TorrentPath()
        assert tp.is_ep(r"a\b\c\episode.mkv") is False


# ---------------------------------------------------------------------------
# _gen_save_path — path separator normalization
# ---------------------------------------------------------------------------


class TestGenSavePathSeparators:
    """``_gen_save_path`` should normalize download path separators."""

    def test_windows_download_path(self):
        """When downloader.path uses backslashes, output uses forward slashes."""
        bangumi = make_bangumi(official_title="My Anime", year="2024", season=2)
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = r"X:\video\anime"
            result = TorrentPath._gen_save_path(bangumi)

        normalized = result.replace("\\", "/")
        assert normalized.startswith("X:/video/anime")
        assert "My Anime (2024)" in normalized
        assert "Season 2" in normalized

    def test_mixed_download_path(self):
        """Mixed separators in downloader.path produce consistent output."""
        bangumi = make_bangumi(official_title="Test", season=1)
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = r"X:/video\anime"
            result = TorrentPath._gen_save_path(bangumi)

        normalized = result.replace("\\", "/")
        assert normalized.startswith("X:/video/anime")

    def test_unix_download_path_still_works(self):
        """Unix downloader.path still works as before."""
        bangumi = make_bangumi(official_title="Test", year="2025", season=3)
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/mnt/media/Bangumi"
            result = TorrentPath._gen_save_path(bangumi)

        normalized = result.replace("\\", "/")
        assert normalized.startswith("/mnt/media/Bangumi")
