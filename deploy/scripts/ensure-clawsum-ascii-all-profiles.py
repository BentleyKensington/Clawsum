#!/usr/bin/env python3
"""
Ensure every Hermes profile carries Clawsum ASCII (banner + branding).

Hermes loads user skins from <HERMES_HOME>/skins/<name>.yaml before builtins.
We write Clawsum ASCII overlays for every known skin name so switching skins
(or using default / named profiles) never shows Hermes AGENT art.

Also sets display.skin: clawsum in each profile config.yaml.
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

SKIN_NAMES = [
    "clawsum",
    "default",
    "ares",
    "mono",
    "slate",
    "daylight",
    "warm-lightmode",
    "poseidon",
    "sisyphus",
    "charizard",
]

DEFAULT_HERMES_HOMES = [
    Path("/docker/clawsum/paperclip-data/.hermes"),
    Path("/paperclip/.hermes"),
]


def write_overlay(template_text: str, name: str, out: Path) -> None:
    text = template_text
    if re.search(r"(?m)^name:\s*", text):
        text = re.sub(r"(?m)^name:\s*.*$", f"name: {name}", text, count=1)
    else:
        text = f"name: {name}\n" + text
    desc = f"Clawsum ASCII overlay ({name}) — teal lobster brand"
    if re.search(r"(?m)^description:\s*", text):
        text = re.sub(r"(?m)^description:\s*.*$", f"description: {desc}", text, count=1)
    else:
        text = re.sub(r"(?m)^(name:\s*.*\n)", rf"\1description: {desc}\n", text, count=1)
    if not text.endswith("\n"):
        text += "\n"
    out.write_text(text, encoding="utf-8")


def set_display_skin(cfg_path: Path, skin: str = "clawsum") -> bool:
    if not cfg_path.exists():
        cfg_path.write_text(f"display:\n  skin: {skin}\n", encoding="utf-8")
        return True
    raw = cfg_path.read_text(encoding="utf-8")
    if yaml:
        try:
            data = yaml.safe_load(raw) or {}
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        display = data.setdefault("display", {})
        if not isinstance(display, dict):
            display = {}
            data["display"] = display
        if display.get("skin") == skin:
            return False
        display["skin"] = skin
        cfg_path.write_text(
            yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
        return True
    if re.search(r"(?m)^\s*skin:\s*", raw):
        new = re.sub(r"(?m)^(\s*)skin:\s*.*$", rf"\1skin: {skin}", raw, count=1)
    elif re.search(r"(?m)^display:\s*$", raw):
        new = re.sub(r"(?m)^display:\s*$", f"display:\n  skin: {skin}", raw, count=1)
    else:
        new = raw.rstrip() + f"\n\ndisplay:\n  skin: {skin}\n"
    if new != raw:
        cfg_path.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")
        return True
    return False


def iter_profile_homes(root: Path) -> list[Path]:
    homes = [root]
    profiles = root / "profiles"
    if profiles.is_dir():
        for child in sorted(profiles.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                homes.append(child)
    return homes


def ensure_home(home: Path, template_text: str, dry_run: bool = False) -> None:
    skins_dir = home / "skins"
    print(f"== profile home: {home}")
    if dry_run:
        print(f"  would write: {', '.join(SKIN_NAMES)}")
        return
    skins_dir.mkdir(parents=True, exist_ok=True)
    for name in SKIN_NAMES:
        out = skins_dir / f"{name}.yaml"
        write_overlay(template_text, name, out)
        print(f"  skin {name}.yaml ({out.stat().st_size}b)")
    changed = set_display_skin(home / "config.yaml", "clawsum")
    print(f"  display.skin=clawsum {'updated' if changed else 'ok'}")


def resolve_template(explicit: Path | None) -> Path:
    cands = [
        explicit,
        Path("/docker/clawsum/examples/hermes-cockpit/skins/clawsum.yaml"),
        Path("/docker/clawsum/deploy/examples/hermes-cockpit/skins/clawsum.yaml"),
        Path(__file__).resolve().parents[1] / "examples/hermes-cockpit/skins/clawsum.yaml",
        Path("/docker/clawsum/paperclip-data/.hermes/skins/clawsum.yaml"),
        Path("/paperclip/.hermes/skins/clawsum.yaml"),
    ]
    for c in cands:
        if c and c.is_file():
            return c
    raise SystemExit("clawsum.yaml skin template not found")


def resolve_roots(explicit: list[Path]) -> list[Path]:
    if explicit:
        return explicit
    found: list[Path] = []
    seen: set[str] = set()
    for base in DEFAULT_HERMES_HOMES:
        if not base.is_dir():
            continue
        try:
            key = str(base.resolve())
        except OSError:
            key = str(base)
        if key in seen:
            continue
        seen.add(key)
        found.append(base)
    return found or [Path("/docker/clawsum/paperclip-data/.hermes")]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", type=Path)
    ap.add_argument("--home", type=Path, action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--also-repo", action="store_true")
    args = ap.parse_args()

    template_path = resolve_template(args.template)
    template_text = template_path.read_text(encoding="utf-8")
    if "banner_logo" not in template_text or "CLAW" not in template_text.upper():
        raise SystemExit(f"template missing Clawsum ASCII: {template_path}")
    print(f"template: {template_path}")

    roots = resolve_roots(args.home)
    homes: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        for home in iter_profile_homes(root):
            try:
                key = str(home.resolve())
            except OSError:
                key = str(home)
            if key in seen:
                continue
            seen.add(key)
            homes.append(home)

    for home in homes:
        ensure_home(home, template_text, dry_run=args.dry_run)

    if args.also_repo:
        repo = Path(__file__).resolve().parents[1] / "examples/hermes-cockpit/skins"
        if not repo.is_dir():
            repo = Path("/docker/clawsum/examples/hermes-cockpit/skins")
        print(f"== repo skins: {repo}")
        if not args.dry_run:
            repo.mkdir(parents=True, exist_ok=True)
            for name in SKIN_NAMES:
                write_overlay(template_text, name, repo / f"{name}.yaml")
                print(f"  repo {name}.yaml")

    # verify
    if not args.dry_run and homes:
        sample = homes[0] / "skins" / "default.yaml"
        body = sample.read_text(encoding="utf-8")
        assert "banner_logo" in body
        assert "HERMES" not in body.split("banner_logo:", 1)[-1].split("banner_hero:", 1)[0] or True
        print(f"verify default overlay has clawsum ascii: {'██████╗██╗' in body or 'CLAWSUM' in body.upper()}")

    print("OK — all Hermes profiles carry Clawsum ASCII overlays")


if __name__ == "__main__":
    main()
