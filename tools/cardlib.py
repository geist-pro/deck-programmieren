"""Shared helpers for the deck: loading YAML cards, markdown->HTML, Java highlighting."""
from __future__ import annotations

import hashlib
import html
import re
from pathlib import Path

import yaml
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "cards"
FIGS = ROOT / "figures"
FONTS_DIR = ROOT / "fonts"

# Course keys, deck names and tags are fixed: Anki derives deck ids from the names,
# so renaming one would create a second deck for everyone who already imported it.
ALL_COURSES = {
    "gdp": {"root": "Grundlagen der Programmierung WS26/27", "lang": "de", "tag": "GdP"},
    "coopsys": {"root": "Cooperation Systems WS26/27", "lang": "en", "tag": "CoopSys"},
    # English translation of the GdP deck: cards/gdp-en/<same file>.yaml holds only translated text
    # fields keyed by the German card id; code, run, answers and figures come from cards/gdp/.
    "gdp-en": {"root": "Programming Fundamentals (GdP) WS26/27 · English", "lang": "en", "tag": "GdP-EN",
               "base": "gdp"},
}
COURSES = {k: v for k, v in ALL_COURSES.items() if (CARDS / k).is_dir()}

TEXT_FIELDS = ("front", "back", "extra", "text", "prompt", "answer", "explanation", "label", "source")


# ---------------------------------------------------------------- loading
def load_lectures(course: str | None = None):
    """Yield (course, path, data) for every lecture YAML, sorted by filename.
    For overlay courses (with "base"), the base lecture is merged with the translation file;
    untranslated cards are left out and listed in data["_missing"].
    Cards with `hold: <reason>` are parked: checked, but left out of the built deck."""
    for c in ([course] if course else COURSES):
        base = COURSES[c].get("base")
        if not base:
            for p in sorted((CARDS / c).glob("*.yaml")):
                yield c, p, yaml.safe_load(p.read_text(encoding="utf-8"))
            continue
        for p in sorted((CARDS / c).glob("*.yaml")):
            yield c, p, merge_overlay(c, base, p)


def merge_overlay(course: str, base: str, path: Path) -> dict:
    import copy
    ov = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    bpath = CARDS / base / path.name
    bdata = yaml.safe_load(bpath.read_text(encoding="utf-8"))
    lec = dict(bdata["lecture"])
    lec.update(ov.get("lecture") or {})
    old_id = bdata["lecture"]["id"]
    new_id = old_id.replace(base + "-", course + "-", 1)
    lec["id"] = new_id
    lec["lang"] = COURSES[course]["lang"]
    by_id = {c["id"]: c for c in ov.get("cards") or []}
    cards, missing = [], []
    for bc in bdata.get("cards") or []:
        tr = by_id.get(bc["id"])
        if not tr:
            missing.append(bc["id"])
            continue
        c = copy.deepcopy(bc)
        for k, v in tr.items():
            if k != "id":
                c[k] = v
        c["id"] = bc["id"].replace(old_id + "-", new_id + "-", 1)
        c["_base_code"] = "code" not in tr and "run" not in tr
        cards.append(c)
    extra = set(by_id) - {bc["id"] for bc in bdata.get("cards") or []}
    return {"lecture": lec, "cards": cards, "flags": ov.get("flags", []), "_missing": missing,
            "_orphans": sorted(extra), "_base": str(bpath)}


def stable_id(text: str, lo: int = 1 << 30, hi: int = 1 << 31) -> int:
    h = int(hashlib.sha1(text.encode()).hexdigest()[:12], 16)
    return lo + h % (hi - lo)


# ---------------------------------------------------------------- markdown
_CLOZE = re.compile(r"\{\{c(\d+)::(.*?)(?:::(.*?))?\}\}", re.S)


def md(text: str | None) -> str:
    """Tiny markdown: **bold**, *italic*, `code`, '- ' bullets, blank-line paragraphs.
    Cloze markers {{cN::...}} pass through untouched (their content is converted too)."""
    if not text:
        return ""
    text = str(text).strip()
    out_blocks = []
    for block in re.split(r"\n\s*\n", text):
        lines = block.split("\n")
        if all(l.lstrip().startswith(("- ", "• ")) for l in lines if l.strip()):
            items = "".join(f"<li>{_inline(l.lstrip()[2:])}</li>" for l in lines if l.strip())
            out_blocks.append(f"<ul>{items}</ul>")
        else:
            out_blocks.append("<br>".join(_inline(l) for l in lines))
    if len(out_blocks) == 1:
        return out_blocks[0]
    return "".join(f"<p>{b}</p>" if not b.startswith("<ul>") else b for b in out_blocks)


def _inline(s: str) -> str:
    # protect code spans first
    codes: list[str] = []

    def keep(m):
        codes.append(m.group(1))
        return f"\x00{len(codes)-1}\x00"

    s = re.sub(r"`([^`]+)`", keep, s)
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = s.replace("-&gt;", "→").replace("&lt;-", "←")

    def put(m):
        return f"<code>{html.escape(codes[int(m.group(1))], quote=False)}</code>"

    return re.sub(r"\x00(\d+)\x00", put, s)


def plain(text: str | None) -> str:
    """Rendered text without tags (for length checks)."""
    return re.sub(r"<[^>]+>", "", md(text))


# ---------------------------------------------------------------- code
_LEXERS = {}


def code_html(src: str, lang: str = "java", linenos: bool = False) -> str:
    """Highlight code; cloze markers inside the code survive as real Anki clozes."""
    src = src.rstrip("\n")
    clozes: list[tuple[str, str, str | None]] = []

    def ph(m):
        clozes.append((m.group(1), m.group(2), m.group(3)))
        return f"CLZPH{len(clozes)-1}X"

    src2 = _CLOZE.sub(ph, src)
    lexer = _LEXERS.setdefault(lang, get_lexer_by_name(lang))
    out = highlight(src2, lexer, HtmlFormatter(nowrap=True))

    def back(m):
        n, ans, hint = clozes[int(m.group(1))]
        a = html.escape(ans, quote=False)
        return f"{{{{c{n}::{a}::{html.escape(hint, quote=False)}}}}}" if hint else f"{{{{c{n}::{a}}}}}"

    out = re.sub(r"CLZPH(\d+)X", back, out)
    if linenos:
        lines = out.rstrip("\n").split("\n")
        w = len(str(len(lines)))
        out = "\n".join(f'<span class="ln">{i:>{w}}</span>{l}' for i, l in enumerate(lines, 1))
    return f'<pre class="code">{out}</pre>'


def output_html(text: str, lang: str = "de") -> str:
    label = "Konsole" if lang == "de" else "Console"
    return f'<pre class="out" data-label="{label}">{html.escape(str(text).rstrip(), quote=False)}</pre>'


# ---------------------------------------------------------------- figures
def figures(card: dict) -> tuple[str | None, str | None]:
    """(front, back) image file names in figures/. `figure` shows on the question side (and on the
    answer side unless `figure_back` replaces it, e.g. the same diagram with the label revealed)."""
    return card.get("figure"), card.get("figure_back")


def media_path(name: str) -> Path:
    for d in (FIGS, FONTS_DIR):
        if (d / name).exists():
            return d / name
    raise FileNotFoundError(name)
