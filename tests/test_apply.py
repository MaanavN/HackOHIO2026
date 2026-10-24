"""Unit tests for the parts that don't need Hermes, Instagram or an LLM.

    venv/bin/python -m pytest tests
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import instaloader
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apply import commands, hooks, profile, tools, tracker  # noqa: E402
from apply.reel import download, media  # noqa: E402


class _FakePost:
    video_url = "https://scontent.example/v.mp4"
    is_video = True
    typename = "GraphVideo"
    comments = 0
    caption = "comment LINK"
    title = None
    owner_username = "creator"
    video_duration = 12.0
    likes = 5
    date_utc = None

    class owner_profile:
        biography = "bio"
        external_url = "https://creator.example"
        full_name = "Creator"


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("APPLY_DATA_DIR", str(tmp_path))
    return tmp_path


def test_reel_url_detection():
    text = "check this https://www.instagram.com/reel/DAbc123_-x/?igsh=xyz and https://example.com"
    assert download.find_reel_urls(text) == ["https://www.instagram.com/reel/DAbc123_-x/?igsh=xyz"]
    assert download.reel_id("https://instagram.com/p/XYZ789/") == "XYZ789"
    assert download.reel_id("https://www.instagram.com/someuser/reel/QQQ111/") == "QQQ111"
    assert download.reel_id("https://youtube.com/shorts/abc") is None


def test_loader_writes_into_absolute_out_dir(tmp_path):
    """Instaloader sanitises "/" in substituted patterns, so an absolute {target} used
    to become a relative "∕tmp∕…" directory in the cwd and the download was lost."""
    out_dir = tmp_path / "reels" / "ABC123"
    loader, note = download._loader(None, None, out_dir)
    assert note and "anonymously" in note
    assert loader.dirname_pattern == str(out_dir)
    assert "{target}" not in loader.dirname_pattern


class _FakeResponse:
    def __init__(self, chunks, status_code=200):
        self._chunks = chunks
        self.status_code = status_code

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_content(self, chunk_size):
        return iter(self._chunks)


def test_download_streams_the_post_video_url(tmp_path, monkeypatch):
    """The reel video comes from post.video_url, streamed to <id>/reel.mp4."""
    requested = {}

    def fake_get(url, stream=False, timeout=None):
        requested["url"] = url
        assert stream is True
        return _FakeResponse([b"video", b"", b"bytes"])

    monkeypatch.setattr(download.requests, "get", fake_get)
    monkeypatch.setattr(instaloader.Post, "from_shortcode", classmethod(lambda cls, ctx, rid: _FakePost()))

    meta = download.download("https://www.instagram.com/reel/ABC123/", tmp_path / "reels")
    video = tmp_path / "reels" / "ABC123" / "reel.mp4"
    assert requested["url"] == _FakePost.video_url
    assert video.read_bytes() == b"videobytes"
    assert meta["video_path"] == str(video)
    assert meta["caption"] == "comment LINK"
    assert json.loads((video.parent / "info.json").read_text())["id"] == "ABC123"


def test_download_reports_a_failed_video_fetch(tmp_path, monkeypatch):
    monkeypatch.setattr(download.requests, "get", lambda *a, **k: _FakeResponse([b""], status_code=403))
    monkeypatch.setattr(instaloader.Post, "from_shortcode", classmethod(lambda cls, ctx, rid: _FakePost()))

    with pytest.raises(download.DownloadError) as err:
        download.download("https://www.instagram.com/reel/ABC123/", tmp_path / "reels")
    assert "403" in str(err.value)


def test_reel_cleanup_removes_workdir(data_dir):
    reel_dir = data_dir / "reels" / "ABC123"
    reel_dir.mkdir(parents=True)
    (reel_dir / "video.mp4").write_bytes(b"video")
    (reel_dir / "analysis.json").write_text("{}")

    result = json.loads(tools.reel_cleanup({"url": "https://www.instagram.com/reel/ABC123/"}))
    assert result["removed"] is True
    assert not reel_dir.exists()

    again = json.loads(tools.reel_cleanup({"url": "https://www.instagram.com/reel/ABC123/"}))
    assert again["removed"] is False

    invalid = json.loads(tools.reel_cleanup({"url": "https://example.com/video"}))
    assert "error" in invalid


def test_tracker_save_dedupes_and_updates():
    a = tracker.save("Google", role="STEP Intern", apply_url="https://careers.google.com/x", status="found")
    b = tracker.save("Google", apply_url="https://careers.google.com/x", deadline="2026-11-01")
    assert a["id"] == b["id"]
    assert b["deadline"] == "2026-11-01" and b["role"] == "STEP Intern"

    updated = tracker.update(a["id"], status="applied")
    assert updated["status"] == "applied"
    assert [x["id"] for x in tracker.list_all("applied")] == [a["id"]]
    assert tracker.find("goog")[0]["id"] == a["id"]

    with pytest.raises(ValueError):
        tracker.update(a["id"], status="maybe")


def test_tracker_find_by_reel():
    tracker.save("Meta", reel_url="https://www.instagram.com/reel/ABC123/")
    assert len(tracker.find_by_reel("ABC123")) == 1
    assert tracker.find_by_reel("ABC") == []


def test_profile_merge_and_missing():
    profile.merge({"contact": {"name": "Sam"}, "skills": ["Python"]})
    merged = profile.merge({"contact": {"email": "s@x.com"}, "skills": ["Python", "SQL"]})
    assert merged["contact"] == {"name": "Sam", "email": "s@x.com"}
    assert merged["skills"] == ["Python", "SQL"]

    missing = profile.missing_fields()
    assert "contact.name" not in missing["required"]
    assert "contact.phone" in missing["required"]

    replaced = profile.merge({"skills": ["Go"]}, replace=True)
    assert replaced["skills"] == ["Go"]


def test_commands():
    assert "No applications" in commands.jobs("")
    app = tracker.save("Stripe", role="SWE Intern")
    assert "Stripe" in commands.jobs("")
    assert "applied" in commands.update(f"{app['id']} applied")
    assert "Unknown status" in commands.update("Stripe maybe")
    assert "Stripe" in commands.status("stripe")
    assert "import" in commands.show_profile("").lower()


def test_router_hook():
    ctx = hooks.route(user_message="https://www.instagram.com/reel/AAA111/", is_first_turn=True)
    assert "reel-to-application" in ctx["context"]
    assert "no candidate profile" in ctx["context"]

    profile.merge({"contact": {"name": "Sam"}})
    ctx = hooks.route(user_message="hi", is_first_turn=True)
    assert "Name: Sam" in ctx["context"]
    assert hooks.route(user_message="hi", is_first_turn=False) is None


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_frame_sampling(tmp_path):
    video = tmp_path / "v.mp4"
    # 6 s test video: three 2-second solid colour scenes plus a tone
    subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=red:s=320x240:d=2",
            "-f", "lavfi", "-i", "color=green:s=320x240:d=2",
            "-f", "lavfi", "-i", "color=blue:s=320x240:d=2",
            "-f", "lavfi", "-i", "sine=d=6",
            "-filter_complex", "[0][1][2]concat=n=3:v=1:a=0[v]",
            "-map", "[v]", "-map", "3", "-pix_fmt", "yuv420p", str(video),
        ],
        check=True,
    )
    frames = media.extract_frames(video, tmp_path)
    assert 3 <= len(frames) <= media.MAX_FRAMES
    assert media.extract_audio(video, tmp_path).exists()
