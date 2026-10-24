"""ffmpeg helpers: pull the audio track and a small set of distinct frames from a video."""

import shutil
import subprocess
from pathlib import Path

MAX_FRAMES = 16
MIN_SCENE_FRAMES = 4
SCENE_THRESHOLD = 0.3


class MediaError(RuntimeError):
    pass


def _ffmpeg(*args: str) -> None:
    if not shutil.which("ffmpeg"):
        raise MediaError("ffmpeg is not installed (brew install ffmpeg)")
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise MediaError(proc.stderr.strip() or f"ffmpeg exited with {proc.returncode}")


def has_audio(video: Path) -> bool:
    if not shutil.which("ffprobe"):
        return True
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(video)],
        capture_output=True,
        text=True,
    )
    return bool(proc.stdout.strip())


def extract_audio(video: Path, out_dir: Path) -> Path | None:
    """16 kHz mono WAV, the format every Whisper backend accepts. None if the video is silent."""
    if not has_audio(video):
        return None
    audio = out_dir / "audio.wav"
    _ffmpeg("-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(audio))
    return audio


def _even_subset(paths: list[Path], limit: int) -> list[Path]:
    if len(paths) <= limit:
        return paths
    step = (len(paths) - 1) / (limit - 1)
    return [paths[round(i * step)] for i in range(limit)]


def extract_frames(video: Path, out_dir: Path, max_frames: int = MAX_FRAMES) -> list[Path]:
    """Keyframes at scene changes; falls back to ~1 fps with duplicates dropped for static reels.

    Reels are mostly near-identical frames, so this usually yields 5–20 images
    instead of the ~900 a 30-second reel actually has.
    """
    frames_dir = out_dir / "frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)

    _ffmpeg(
        "-i", str(video),
        "-vf", f"select='eq(n,0)+gt(scene,{SCENE_THRESHOLD})',scale=720:-2",
        "-fps_mode", "vfr", "-q:v", "3",
        str(frames_dir / "scene_%03d.jpg"),
    )
    frames = sorted(frames_dir.glob("scene_*.jpg"))

    if len(frames) < MIN_SCENE_FRAMES:
        # Talking-head reels with text overlays barely change scene; sample by time instead.
        _ffmpeg(
            "-i", str(video),
            "-vf", "fps=1,mpdecimate,scale=720:-2",
            "-fps_mode", "vfr", "-q:v", "3",
            str(frames_dir / "time_%03d.jpg"),
        )
        frames = sorted(frames_dir.glob("*.jpg"))

    keep = _even_subset(frames, max_frames)
    for frame in set(frames) - set(keep):
        frame.unlink()
    return keep
