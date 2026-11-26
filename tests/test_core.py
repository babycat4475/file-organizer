"""Tests for the GUI-free core: classification, conflict naming, organize modes."""
from __future__ import annotations

from pathlib import Path

import pytest

from file_organizer.core import DEFAULT_RULES, OTHER, FileOrganizer


def make_files(tmp_path: Path, names: list[str]) -> None:
    for n in names:
        (tmp_path / n).write_text("x")


def test_rule_count_at_least_60():
    assert sum(len(v) for v in DEFAULT_RULES.values()) >= 60


def test_classification():
    org = FileOrganizer()
    assert org.category_of(Path("a.PDF")) == "文档"
    assert org.category_of(Path("b.jpg")) == "图片"
    assert org.category_of(Path("c.unknown")) == OTHER


def test_custom_rule():
    org = FileOrganizer()
    org.add_rule("epub", "书籍")
    assert org.category_of(Path("book.epub")) == "书籍"
    org.add_rule(".MOBI", "书籍")
    assert org.category_of(Path("book.mobi")) == "书籍"


def test_invalid_mode():
    with pytest.raises(ValueError):
        FileOrganizer(mode="delete")


def test_conflict_rename(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    p = FileOrganizer.resolve_conflict(tmp_path / "a.txt")
    assert p.name == "a (1).txt"
    p.write_text("x")
    assert FileOrganizer.resolve_conflict(tmp_path / "a.txt").name == "a (2).txt"


def test_organize_move(tmp_path):
    make_files(tmp_path, ["x.pdf", "y.jpg", "z.py", "w.xyz"])
    r = FileOrganizer(mode="move").organize(tmp_path)
    assert len(r.moved) == 4
    assert (tmp_path / "文档" / "x.pdf").exists()
    assert (tmp_path / "图片" / "y.jpg").exists()
    assert (tmp_path / "代码" / "z.py").exists()
    assert (tmp_path / OTHER / "w.xyz").exists()
    assert not (tmp_path / "x.pdf").exists()


def test_organize_copy_keeps_original(tmp_path):
    make_files(tmp_path, ["x.pdf"])
    FileOrganizer(mode="copy").organize(tmp_path)
    assert (tmp_path / "x.pdf").exists()
    assert (tmp_path / "文档" / "x.pdf").exists()


def test_dry_run_touches_nothing(tmp_path):
    make_files(tmp_path, ["x.pdf"])
    r = FileOrganizer(mode="move").organize(tmp_path, dry_run=True)
    assert len(r.moved) == 1
    assert (tmp_path / "x.pdf").exists()
    assert not (tmp_path / "文档").exists()


def test_never_overwrites_existing(tmp_path):
    make_files(tmp_path, ["x.pdf"])
    dest_dir = tmp_path / "文档"
    dest_dir.mkdir()
    (dest_dir / "x.pdf").write_text("OLD")
    FileOrganizer(mode="move").organize(tmp_path)
    assert (dest_dir / "x.pdf").read_text() == "OLD"
    assert (dest_dir / "x (1).pdf").read_text() == "x"


def test_skips_dirs_and_hidden(tmp_path):
    make_files(tmp_path, [".hidden", "x.pdf"])
    (tmp_path / "sub").mkdir()
    r = FileOrganizer(mode="move").organize(tmp_path)
    assert len(r.moved) == 1
    assert len(r.skipped) == 2
    assert (tmp_path / "sub").is_dir()


def test_idempotent_second_run(tmp_path):
    make_files(tmp_path, ["x.pdf"])
    org = FileOrganizer(mode="move")
    org.organize(tmp_path)
    r2 = org.organize(tmp_path)
    assert len(r2.moved) == 0  # only category dirs remain, all skipped


def test_bad_source_raises(tmp_path):
    with pytest.raises(NotADirectoryError):
        FileOrganizer().organize(tmp_path / "nope")
