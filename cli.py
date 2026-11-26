#!/usr/bin/env python3
"""Headless CLI: python cli.py ~/Downloads --mode move --dry-run"""
import argparse
from pathlib import Path
from file_organizer.core import FileOrganizer

p = argparse.ArgumentParser(description="智能文件自动整理（命令行版）")
p.add_argument("directory")
p.add_argument("--mode", choices=["move", "copy"], default="move")
p.add_argument("--dry-run", action="store_true")
a = p.parse_args()
r = FileOrganizer(mode=a.mode, on_event=print).organize(Path(a.directory), dry_run=a.dry_run)
print(f"完成：处理 {len(r.moved)}，跳过 {len(r.skipped)}，错误 {len(r.errors)}")
