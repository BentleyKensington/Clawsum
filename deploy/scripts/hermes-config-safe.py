#!/usr/bin/env python3
"""Validate / snapshot / restore Hermes config.yaml without clobbering a good file."""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

DEFAULT = Path("/docker/clawsum/paperclip-data/.hermes/config.yaml")


def _load_yaml(text: str):
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None
    if yaml is not None:
        return yaml.safe_load(text)
    # Minimal fallback: accept if required headings exist and YAML-ish.
    if "model:" not in text or "plugins:" not in text:
        raise ValueError("missing model/plugins headings")
    return {"model": True, "plugins": True}


def validate(text: str) -> str | None:
    if not text or not text.strip():
        return "empty"
    # Jul 29 signature: orphan model keys mixed under display/skin
    if "display:" in text and "\n  default:" in text.split("display:", 1)[-1]:
        return "orphan keys under display (corrupt merge)"
    try:
        data = _load_yaml(text)
    except Exception as exc:
        return f"yaml: {exc}"
    if not isinstance(data, dict):
        return "root is not a mapping"
    if "model" not in data:
        return "missing model"
    if "plugins" not in data:
        return "missing plugins"
    return None


def snapshot(path: Path) -> None:
    ok = path.with_name("config.yaml.ok")
    stamp = path.with_name("config.yaml.ok." + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(path, ok)
    shutil.copy2(path, stamp)
    old = sorted(path.parent.glob("config.yaml.ok.*"), reverse=True)
    for extra in old[8:]:
        extra.unlink(missing_ok=True)


def restore(path: Path) -> Path | None:
    candidates = []
    ok = path.with_name("config.yaml.ok")
    if ok.is_file():
        candidates.append(ok)
    candidates.extend(sorted(path.parent.glob("config.yaml.ok.*"), reverse=True))
    for src in candidates:
        err = validate(src.read_text(encoding="utf-8", errors="replace"))
        if err:
            continue
        bak = path.with_name(
            "config.yaml.corrupt." + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S") + ".bak"
        )
        if path.exists():
            shutil.copy2(path, bak)
        shutil.copy2(src, path)
        return src
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", type=Path, default=DEFAULT)
    ap.add_argument("--repair", action="store_true")
    args = ap.parse_args()
    path: Path = args.path
    if not path.exists():
        print(f"MISSING {path}")
        return 2
    text = path.read_text(encoding="utf-8", errors="replace")
    err = validate(text)
    if err is None:
        snapshot(path)
        print(f"OK {path}")
        return 0
    print(f"INVALID {path}: {err}")
    if not args.repair:
        return 1
    src = restore(path)
    if src is None:
        print("RESTORE_FAILED no valid snapshot")
        return 1
    print(f"RESTORED from {src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
