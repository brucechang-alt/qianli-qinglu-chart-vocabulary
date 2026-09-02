#!/usr/bin/env python3
"""Extract reusable SVG charts and brand assets from the standalone poster."""

from __future__ import annotations

import base64
import io
import json
import re
from copy import deepcopy
from pathlib import Path

from lxml import etree, html
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "qianli-qinglu-chart-vocabulary.html"

FAMILY_DIRS = [
    "change",
    "ranking",
    "deviation",
    "magnitude",
    "distribution",
    "correlation",
    "part-to-whole",
    "flow-and-relationship",
    "spatial",
]

SVG_STYLE = """
:root{--paper:#faf2d9;--ink:#1c211d;--muted:#625c4d;--rule:#cdbd8f;--cinnabar:#e14b32;--stone-blue:#007ea7;--stone-green:#259b62;--ochre:#d99a16}
text{font-family:"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif;fill:var(--ink)}
.label,.value,.value-light,.big-value,.note,.tick,.axis-title{font-size:12px}
.value,.big-value{font-weight:700;font-variant-numeric:tabular-nums}.big-value{font-size:18px}
.value-light{font-weight:700;fill:var(--paper)}.tick,.axis-title{fill:var(--muted)}
.axis{stroke:var(--rule);stroke-width:1}.grid{stroke:var(--rule);stroke-width:1;stroke-dasharray:3 4;opacity:.72}
.red{stroke:var(--cinnabar);stroke-width:2.5}.blue{stroke:var(--stone-blue);stroke-width:2.5}.green{stroke:var(--stone-green);stroke-width:2.5}.gold{stroke:var(--ochre);stroke-width:2.5}
""".strip()


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_logo(source_text: str) -> None:
    match = re.search(r"background-image:url\(data:image/png;base64,([A-Za-z0-9+/=]+)\)", source_text)
    if not match:
        raise RuntimeError("AI记者 logo data URL not found")
    image = Image.open(io.BytesIO(base64.b64decode(match.group(1)))).convert("RGB")
    # The poster source stores the logo on a large canvas. Keep only the signed
    # mark and publish a compact derivative; the logo remains brand-reserved.
    logo = image.crop((200, 300, 1340, 720)).resize((570, 210), Image.Resampling.LANCZOS)
    logo.save(ROOT / "assets" / "ai-reporter-logo.png", optimize=True)


def add_svg_style(svg: etree._Element) -> None:
    svg.set("xmlns", "http://www.w3.org/2000/svg")
    if "viewbox" in svg.attrib:
        svg.set("viewBox", svg.attrib.pop("viewbox"))
    svg.set("width", "360")
    svg.set("height", "190")
    style = etree.Element("style")
    style.text = SVG_STYLE
    first_graphic = next(iter(svg), None)
    if first_graphic is None:
        svg.append(style)
    else:
        first_graphic.addprevious(style)


def main() -> None:
    source_text = SOURCE.read_text(encoding="utf-8")
    extract_logo(source_text)
    tree = html.parse(str(SOURCE))
    families = tree.xpath('//section[contains(concat(" ", normalize-space(@class), " "), " family-panel ")]')
    if len(families) != 9:
        raise RuntimeError(f"Expected 9 families, found {len(families)}")

    manifest: dict[str, object] = {
        "project": "Qianli Qinglu Chart Vocabulary",
        "version": "2.0.0",
        "chart_count": 0,
        "families": [],
    }
    absolute_index = 0
    for family_index, (family, directory_name) in enumerate(zip(families, FAMILY_DIRS), start=1):
        family_name = clean_text(family.xpath("string(.//h2)"))
        family_question = clean_text(family.xpath("string(.//header[contains(@class,'family-head')]//p)"))
        target_dir = ROOT / "charts" / directory_name
        target_dir.mkdir(parents=True, exist_ok=True)
        cards = family.xpath(".//article")
        family_record = {
            "id": family_index,
            "name": family_name,
            "question": family_question,
            "directory": directory_name,
            "charts": [],
        }
        for chart_index, card in enumerate(cards, start=1):
            absolute_index += 1
            title = clean_text(card.xpath("string(.//h3)"))
            question = clean_text(card.xpath("string(.//header[contains(@class,'mini-head')]//p)"))
            svgs = card.xpath(".//div[contains(@class,'chart-shell')]/svg")
            if len(svgs) != 1:
                raise RuntimeError(f"{family_name}/{title}: expected one SVG, found {len(svgs)}")
            svg = deepcopy(svgs[0])
            add_svg_style(svg)
            filename = f"{family_index:02d}-{chart_index:02d}.svg"
            output_path = target_dir / filename
            output_path.write_bytes(
                etree.tostring(svg, encoding="utf-8", xml_declaration=True, pretty_print=True)
            )
            family_record["charts"].append(
                {
                    "id": absolute_index,
                    "name": title,
                    "question": question,
                    "file": f"charts/{directory_name}/{filename}",
                }
            )
        manifest["families"].append(family_record)

    manifest["chart_count"] = absolute_index
    if absolute_index != 67:
        raise RuntimeError(f"Expected 67 charts, found {absolute_index}")
    (ROOT / "charts" / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Built {len(families)} families and {absolute_index} SVG charts")


if __name__ == "__main__":
    main()
