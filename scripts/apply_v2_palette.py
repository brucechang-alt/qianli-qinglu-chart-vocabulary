#!/usr/bin/env python3
"""Apply the Qianli Qinglu 2.0 colour-purification palette to authored sources."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "src" / "qianli-qinglu-chart-vocabulary.html",
    ROOT / "styles.css",
    ROOT / "index.html",
]

REPLACEMENTS = {
    "#f3e6c6": "#faf2d9",
    "#e2cfa1": "#ead49a",
    "#28231b": "#1c211d",
    "#594a35": "#4b4a3d",
    "#736249": "#625c4d",
    "#c4a971": "#cdbd8f",
    "#006f91": "#007ea7",
    "#55b9c1": "#4ec6d0",
    "#c7e9d8": "#d5f2e6",
    "#2f8456": "#259b62",
    "#b97a12": "#d99a16",
    "#c44530": "#e14b32",
    "#e48f75": "#f09a78",
    "#704c99": "#8351b2",
    "#4f8da4": "#42a7c2",
    "#b9d2dc": "#a9e0e5",
    "#f8efd9": "#fff8e5",
    "rgba(243,230,198": "rgba(250,242,217",
    "rgba(40,35,27": "rgba(28,33,29",
}


def replace_case_insensitive(source: str, old: str, new: str) -> str:
    return re.sub(re.escape(old), new, source, flags=re.IGNORECASE)


def main() -> None:
    for path in TARGETS:
        source = path.read_text(encoding="utf-8")
        for old, new in REPLACEMENTS.items():
            source = replace_case_insensitive(source, old, new)
        source = source.replace("QIANLI QINGLÜ CHART VOCABULARY · V1.0", "QIANLI QINGLÜ CHART VOCABULARY · V2.0")
        if path.name == "qianli-qinglu-chart-vocabulary.html":
            source = source.replace("宋朝艳丽版", "色彩提纯版 2.0")
        if path.name == "styles.css" and "--blue-text" not in source:
            source = source.replace(
                "--blue:#007ea7;",
                "--blue:#007ea7;--blue-text:#006184;",
            ).replace(
                "--green:#259b62;",
                "--green:#259b62;--green-text:#26744b;",
            ).replace(
                "--gold:#d99a16;",
                "--gold:#d99a16;--gold-text:#8b5b00;",
            ).replace(
                "--red:#e14b32;",
                "--red:#e14b32;--red-text:#b93d2b;--purple-text:#65417f;",
            )
            source = source.replace("color:var(--red);font-size:13px", "color:var(--red-text);font-size:13px")
            source = source.replace("color:var(--blue)}.chart-copy h3", "color:var(--blue-text)}.chart-copy h3")
            source = source.replace("color:var(--red)}.license-grid", "color:var(--red-text)}.license-grid")
            source = source.replace("color:var(--blue)}footer", "color:var(--blue-text)}footer")
        path.write_text(source, encoding="utf-8")
    print(f"Applied Qianli Qinglu 2.0 palette to {len(TARGETS)} authored source files")


if __name__ == "__main__":
    main()
