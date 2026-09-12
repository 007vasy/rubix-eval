"""Repo and package data paths."""

from __future__ import annotations

from pathlib import Path


def package_dir() -> Path:
    return Path(__file__).resolve().parent


def repo_root() -> Path:
    here = package_dir()
    for candidate in (here.parent.parent, here.parent, Path.cwd()):
        if (candidate / "web" / "index.html").exists():
            return candidate
    return Path.cwd()


def web_dir() -> Path:
    bundled = package_dir() / "web"
    if (bundled / "index.html").exists():
        return bundled
    return repo_root() / "web"
