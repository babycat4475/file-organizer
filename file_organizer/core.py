"""FileOrganizer — core business logic, zero third-party dependencies.

Deliberately GUI-free: importable, unit-testable, reusable from CLI or any UI.
"""
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("file_organizer")

# 60+ extension rules across 9 categories
DEFAULT_RULES: dict[str, tuple[str, ...]] = {
    "图片": (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".heic", ".tiff", ".ico", ".raw"),
    "文档": (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md", ".rtf", ".odt", ".csv"),
    "压缩包": (".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"),
    "视频": (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"),
    "音频": (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"),
    "代码": (".py", ".java", ".c", ".cpp", ".h", ".js", ".ts", ".html", ".css", ".json", ".sh", ".go", ".rs", ".sql"),
    "安装包": (".dmg", ".pkg", ".exe", ".msi", ".apk", ".deb", ".rpm", ".appimage"),
    "字体": (".ttf", ".otf", ".woff", ".woff2"),
    "其他": (),
}

OTHER = "其他"


@dataclass
class OrganizeReport:
    moved: list[tuple[Path, Path]] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.moved) + len(self.skipped) + len(self.errors)


class FileOrganizer:
    """Classify files by extension and move/copy them into category folders.

    Safety guarantees:
    - never overwrites: conflicts get "name (1).ext", "name (2).ext", ...
    - never touches subdirectories or hidden files
    - dry_run mode reports the plan without touching the filesystem
    """

    def __init__(
        self,
        rules: Optional[dict[str, tuple[str, ...]]] = None,
        mode: str = "move",
        on_event: Optional[Callable[[str], None]] = None,
    ):
        if mode not in ("move", "copy"):
            raise ValueError(f"mode must be 'move' or 'copy', got {mode!r}")
        self.mode = mode
        self.on_event = on_event or (lambda msg: logger.info(msg))
        self._ext_map: dict[str, str] = {}
        for category, exts in (rules or DEFAULT_RULES).items():
            for ext in exts:
                self._ext_map[ext.lower()] = category

    # ---- classification ----
    def category_of(self, path: Path) -> str:
        return self._ext_map.get(path.suffix.lower(), OTHER)

    def add_rule(self, ext: str, category: str) -> None:
        ext = ext.lower()
        if not ext.startswith("."):
            ext = "." + ext
        self._ext_map[ext] = category

    # ---- conflict-safe naming ----
    @staticmethod
    def resolve_conflict(dest: Path) -> Path:
        """Return a non-existing path: file.ext -> file (1).ext -> file (2).ext ..."""
        if not dest.exists():
            return dest
        stem, suffix, parent = dest.stem, dest.suffix, dest.parent
        n = 1
        while True:
            candidate = parent / f"{stem} ({n}){suffix}"
            if not candidate.exists():
                return candidate
            n += 1

    # ---- main operation ----
    def organize(self, source_dir: Path, dry_run: bool = False) -> OrganizeReport:
        source_dir = Path(source_dir)
        if not source_dir.is_dir():
            raise NotADirectoryError(f"not a directory: {source_dir}")
        report = OrganizeReport()
        category_names = set(self._ext_map.values()) | {OTHER}

        for item in sorted(source_dir.iterdir()):
            if item.is_dir() or item.name.startswith("."):
                report.skipped.append(item)
                continue
            # don't re-organize files already inside our category folders
            category = self.category_of(item)
            dest_dir = source_dir / category
            dest = self.resolve_conflict(dest_dir / item.name)
            if dry_run:
                report.moved.append((item, dest))
                self.on_event(f"[计划] {item.name} -> {category}/")
                continue
            try:
                dest_dir.mkdir(exist_ok=True)
                if self.mode == "move":
                    shutil.move(str(item), str(dest))
                else:
                    shutil.copy2(str(item), str(dest))
                report.moved.append((item, dest))
                self.on_event(f"[{self.mode}] {item.name} -> {dest.relative_to(source_dir)}")
            except OSError as e:
                report.errors.append((item, str(e)))
                self.on_event(f"[错误] {item.name}: {e}")
        return report
