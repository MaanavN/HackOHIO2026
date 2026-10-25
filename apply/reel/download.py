"""Download an Instagram reel and its metadata with instaloader."""

import http.cookiejar
import json
import logging
import re
import shutil
from pathlib import Path

import requests

REEL_URL_RE = re.compile(r"https?://(?:www\.)?instagram\.com/(?:[\w.]+/)?(?:reel|reels|p|tv)/([\w-]+)[^\s]*", re.I)

logger = logging.getLogger(__name__)


class DownloadError(RuntimeError):
    pass


def find_reel_urls(text: str) -> list[str]:
    return [m.group(0) for m in REEL_URL_RE.finditer(text or "")]


def reel_id(url: str) -> str | None:
    match = REEL_URL_RE.search(url or "")
    return match.group(1) if match else None


def discard(url: str, out_dir: Path) -> dict:
    """Delete the working directory for one reel: video, audio, frames and cached analysis."""
    rid = reel_id(url)
    if not rid:
        raise DownloadError(f"not an Instagram reel/post URL: {url}")
    target = Path(out_dir) / rid
    if not target.exists():
        return {"id": rid, "path": str(target), "removed": False}
    if target.is_symlink():
        target.unlink()
    else:
        shutil.rmtree(target)
    return {"id": rid, "path": str(target), "removed": True}


def _cookies_from_file(path: Path) -> dict:
    if not path.is_file():
        raise DownloadError(f"no cookies file at {path}")
    jar = http.cookiejar.MozillaCookieJar(str(path))
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except (http.cookiejar.LoadError, OSError) as e:
        raise DownloadError(f"could not read cookies from {path}: {e}") from e
    cookies = {c.name: c.value for c in jar if c.value and "instagram.com" in (c.domain or "")}
    if not cookies:
        raise DownloadError(f"{path} has no instagram.com cookies")
    return cookies


def _cookies_from_browser(browser: str) -> dict:
    try:
        import browser_cookie3
    except ImportError as e:
        raise DownloadError(
            "cookies_from_browser needs the browser-cookie3 package (pip install browser-cookie3); "
            "or point cookies_file at a Netscape cookies.txt"
        ) from e
    extractor = getattr(browser_cookie3, browser.lower(), None)
    if extractor is None:
        raise DownloadError(f"unknown browser {browser!r}; use chrome, chromium, firefox, edge or safari")
    try:
        jar = extractor(domain_name="instagram.com")
    except Exception as e:
        raise DownloadError(f"could not read {browser} cookies: {e}") from e
    cookies = {c.name: c.value for c in jar if c.value and "instagram.com" in (c.domain or "")}
    if not cookies:
        raise DownloadError(f"no instagram.com cookies found in {browser}")
    return cookies


def _loader(cookies_file: str | None, cookies_browser: str | None, out_dir: Path):
    """An Instaloader writing into out_dir, with the user's (secondary-account) session applied."""
    try:
        from instaloader import Instaloader
    except ImportError as e:
        raise DownloadError("instaloader is not installed (pip install instaloader)") from e

    loader = Instaloader(
        # Instaloader builds the directory from dirname_pattern and sanitises every
        # substituted value, replacing "/" with "∕". With the default "{target}" an
        # absolute target therefore becomes a relative directory named "∕tmp∕…" in
        # the current working directory, and the video silently lands outside out_dir.
        # A literal pattern with no placeholders is used verbatim.
        dirname_pattern=str(out_dir),
        download_pictures=False,
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        post_metadata_txt_pattern="",
        quiet=True,
    )

    if not (cookies_file or cookies_browser):
        return loader, "downloaded anonymously; set cookies_file or cookies_from_browser for private posts"

    cookies = (
        _cookies_from_file(Path(cookies_file).expanduser())
        if cookies_file
        else _cookies_from_browser(cookies_browser)
    )
    loader.context.update_cookies(cookies)
    try:
        username = loader.test_login()
    except Exception:
        logger.exception("could not verify the Instagram session")
        username = None
    if not username:
        return loader, "Instagram rejected the saved session; downloaded anonymously"
    loader.context.username = username
    return loader, None


def _video_url(post) -> str | None:
    """Direct CDN URL for the post's video, including carousels that carry one."""
    if post.video_url:
        return post.video_url
    if post.typename == "GraphSidecar":
        for node in post.get_sidecar_nodes():
            if node.is_video and node.video_url:
                return node.video_url
    return None


def _fetch_video(url: str, dest: Path, chunk_size: int = 64 * 1024) -> None:
    """Stream the video from Instagram's CDN into dest."""
    try:
        response = requests.get(url, stream=True, timeout=30)
    except requests.RequestException as e:
        raise DownloadError(f"could not reach Instagram's video CDN: {e}") from e
    with response:
        if response.status_code != 200:
            raise DownloadError(f"Instagram returned HTTP {response.status_code} for the video")
        with dest.open("wb") as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    file.write(chunk)


def _friendly(error: Exception) -> str:
    message = str(error) or type(error).__name__
    lowered = message.lower()
    if any(word in lowered for word in ("login", "401", "rate", "checkpoint", "cookie")):
        message += (
            " — Instagram wants a logged-in session. Set the plugin's cookies_file or"
            " cookies_from_browser setting (use a secondary Instagram account)."
        )
    return message


def download(url: str, out_dir: Path, cookies_file: str | None = None, cookies_browser: str | None = None) -> dict:
    """Download the reel into out_dir/<id>/ and return its metadata.

    Instagram usually needs a logged-in session: pass a Netscape cookies.txt
    (cookies_file) or a browser name to read cookies from (cookies_browser).
    Use a secondary Instagram account for this, never your main one.
    """
    try:
        from instaloader import Post
        from instaloader.exceptions import InstaloaderException
    except ImportError as e:
        raise DownloadError("instaloader is not installed (pip install instaloader)") from e

    rid = reel_id(url)
    if not rid:
        raise DownloadError(f"not an Instagram reel/post URL: {url}")
    target = Path(out_dir) / rid
    target.mkdir(parents=True, exist_ok=True)

    loader, note = _loader(cookies_file, cookies_browser, target)
    notes = [note] if note else []

    video = target / "reel.mp4"
    try:
        post = Post.from_shortcode(loader.context, rid)
        video_url = _video_url(post)
        if not video_url:
            raise DownloadError("that post has no video; D.S.T.A needs a reel")
        _fetch_video(video_url, video)
    except InstaloaderException as e:
        raise DownloadError(_friendly(e)) from e

    if not video.is_file() or not video.stat().st_size:
        raise DownloadError(
            f"no video file was written to {video} — Instagram usually refuses anonymous downloads."
            " Set the plugin's cookies_file or cookies_from_browser setting (use a secondary Instagram account)."
        )

    owner = post.owner_username
    meta = {
        "id": rid,
        "url": url,
        "dir": str(target),
        "video_path": str(video),
        "caption": post.caption or "",
        "title": post.title,
        "uploader": owner,
        "uploader_id": owner,
        "uploader_full_name": None,
        "uploader_biography": None,
        "uploader_bio_url": None,
        "uploader_profile_url": f"https://www.instagram.com/{owner}/" if owner else None,
        "upload_date": post.date_utc.strftime("%Y%m%d") if post.date_utc else None,
        "duration": post.video_duration,
        "like_count": post.likes,
        "comment_count": 0,
        "comments": [],
        "notes": notes,
    }
    (target / "info.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return meta
