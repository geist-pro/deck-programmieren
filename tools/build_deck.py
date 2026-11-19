#!/usr/bin/env python3
"""Build the Anki package(s) (.apkg) and an HTML preview from cards/<course>/*.yaml.

usage: python3 tools/build_deck.py [--course <key>] [--only <lecture-id>,...] [--no-apkg]
Output: out/<course>-ws2627.apkg and preview/index.html
"""
from __future__ import annotations

import argparse
import html
import re
import shutil
from pathlib import Path

import genanki

from cardlib import COURSES, ROOT, code_html, figures, load_lectures, md, media_path, output_html, stable_id

# ---------------------------------------------------------------- fixed IDs (never change)
MODEL_BASIC = 1764031101
MODEL_CLOZE = 1764031102
MODEL_CODE = 1764031103

FONTS = ["_FiraSans-Regular.woff2", "_FiraSans-SemiBold.woff2", "_FiraSans-Bold.woff2",
         "_FiraSans-Italic.woff2", "_FiraMono-Regular.woff2", "_FiraMono-Medium.woff2"]

CSS = r"""
@font-face { font-family: "TUC Fira"; src: url("_FiraSans-Regular.woff2"); font-weight: 400; }
@font-face { font-family: "TUC Fira"; src: url("_FiraSans-Italic.woff2"); font-weight: 400; font-style: italic; }
@font-face { font-family: "TUC Fira"; src: url("_FiraSans-SemiBold.woff2"); font-weight: 600; }
@font-face { font-family: "TUC Fira"; src: url("_FiraSans-Bold.woff2"); font-weight: 700; }
@font-face { font-family: "TUC Mono"; src: url("_FiraMono-Regular.woff2"); font-weight: 400; }
@font-face { font-family: "TUC Mono"; src: url("_FiraMono-Medium.woff2"); font-weight: 600; }

.card {
  --bg: #F4F7F5; --paper: #FFFFFF; --ink: #13201A; --ink2: #33413A; --mute: #5E6E66;
  --line: #CFD9D3; --mist: #EEF3F0; --mint: #E3F1E8; --green: #008C4F; --tgreen: #00693B;
  --ember: #E86A2E; --tember: #B4501A; --emberpanel: #FDF0E9; --cyan: #00708F;
  --codebg: #FAFCFB;
  font-family: "TUC Fira", "Fira Sans", -apple-system, "Segoe UI", sans-serif;
  font-size: 19px; line-height: 1.5; color: var(--ink); background: var(--bg);
  text-align: left; margin: 0; padding: 0;
}
.card.nightMode, .nightMode .card, .card.night_mode, .night_mode .card {
  --bg: #0E1613; --paper: #15201C; --ink: #E6EEE9; --ink2: #C3D0C9; --mute: #8FA199;
  --line: #2C3B34; --mist: #1A2722; --mint: #17302A; --green: #2FB874; --tgreen: #5FD39A;
  --ember: #F08A55; --tember: #F49A68; --emberpanel: #2A1D16; --cyan: #4CC3E0;
  --codebg: #111B17;
}
.wrap {
  max-width: 680px; margin: 14px auto; padding: 18px 22px 22px; background: var(--paper);
  border-radius: 14px; border-top: 5px solid var(--green);
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
}
.chip { display: flex; flex-wrap: wrap; gap: 6px; font-size: 12.5px; font-weight: 600;
  letter-spacing: .02em; margin-bottom: 10px; }
.chip span { background: var(--mint); color: var(--tgreen); border-radius: 999px; padding: 2px 10px; }
.chip span.kind { background: var(--emberpanel); color: var(--tember); }
.q { font-size: 21px; font-weight: 600; line-height: 1.4; }
.q p { margin: 0 0 .5em; }
.q.cl { font-weight: 400; font-size: 20px; }
.q.cl strong { font-weight: 600; }
hr#answer { border: 0; border-top: 2px dashed var(--line); margin: 18px 0 14px; }
.a { font-size: 19px; }
.a strong, .q strong { color: var(--tgreen); }
.extra { margin-top: 14px; padding: 10px 14px; background: var(--mist); border-left: 4px solid var(--green);
  border-radius: 0 8px 8px 0; font-size: 16.5px; color: var(--ink2); }
.extra p { margin: 0 0 .4em; } .extra p:last-child { margin-bottom: 0; }
.src { margin-top: 12px; font-size: 12.5px; color: var(--mute); text-align: right; }
.fig { margin: 12px 0 4px; text-align: center; }
.fig img { max-width: 100%; max-height: 360px; border-radius: 8px; border: 1px solid var(--line); background: #fff; }
ul { margin: .3em 0; padding-left: 1.2em; } li { margin: .15em 0; }
code { font-family: "TUC Mono", "Fira Mono", Menlo, Consolas, monospace; font-size: .88em;
  background: var(--mist); color: var(--ink); padding: 1px 5px; border-radius: 4px; }
pre.code, pre.out { font-family: "TUC Mono", "Fira Mono", Menlo, Consolas, monospace; font-size: 15.5px;
  line-height: 1.45; border-radius: 10px; padding: 12px 14px; overflow-x: auto; margin: 10px 0; white-space: pre; }
pre.code { background: var(--codebg); border: 1px solid var(--line); color: var(--ink); font-weight: 400; }
pre.out { background: #13201A; color: #DDF2E5; border: 1px solid #13201A; }
pre.out::before { content: attr(data-label); display: block; font-family: "TUC Fira", sans-serif; font-size: 11px;
  letter-spacing: .08em; text-transform: uppercase; color: #7FB89A; margin-bottom: 4px; }
.nightMode pre.out { background: #050A08; border-color: var(--line); }
/* cloze */
.cloze { font-weight: 700; color: var(--tember); background: var(--emberpanel); border-radius: 4px; padding: 0 4px; }
pre.code .cloze { font-weight: 600; }
.cloze-inactive { color: inherit; }
/* Java tokens (Pygments short classes) */
pre.code .k, pre.code .kd, pre.code .kt, pre.code .kr, pre.code .kn, pre.code .kc, pre.code .kp { color: var(--tgreen); font-weight: 600; }
pre.code .s, pre.code .s1, pre.code .s2, pre.code .sc, pre.code .se { color: var(--tember); }
pre.code .mi, pre.code .mf, pre.code .m, pre.code .il { color: var(--cyan); }
pre.code .c, pre.code .c1, pre.code .cm, pre.code .cs { color: var(--mute); font-style: italic; }
pre.code .nc, pre.code .nn { color: var(--cyan); font-weight: 600; }
pre.code .nf, pre.code .na { color: var(--ink); font-weight: 600; }
pre.code .err { border: none; }
pre.code .ln { color: var(--mute); opacity: .7; margin-right: 12px; user-select: none; }
.mobile .card, .mobile.card { font-size: 17px; }
.mobile .wrap { margin: 6px; padding: 14px 14px 18px; }
.mobile pre.code, .mobile pre.out { font-size: 13.5px; }
.mobile .q { font-size: 19px; }
"""

CHIP = '<div class="chip">{{Header}}</div>'
FIG_FRONT = '{{#Figure}}<div class="fig">{{Figure}}</div>{{/Figure}}'
FIG_BACK = ('{{#FigureBack}}<div class="fig">{{FigureBack}}</div>{{/FigureBack}}'
            '{{^FigureBack}}' + FIG_FRONT + '{{/FigureBack}}')
TAIL = ('{{#Extra}}<div class="extra">{{Extra}}</div>{{/Extra}}'
        '{{#Source}}<div class="src">{{Source}}</div>{{/Source}}')

BASIC = genanki.Model(
    MODEL_BASIC, "TUC Karte (Basic)",
    fields=[{"name": n} for n in ["Front", "Back", "Extra", "Figure", "FigureBack", "Header", "Source", "ID"]],
    templates=[{
        "name": "Karte",
        "qfmt": f'<div class="wrap">{CHIP}<div class="q">{{{{Front}}}}</div>{FIG_FRONT}</div>',
        "afmt": (f'<div class="wrap">{CHIP}<div class="q">{{{{Front}}}}</div>{FIG_BACK}'
                 f'<hr id="answer"><div class="a">{{{{Back}}}}</div>{TAIL}</div>'),
    }],
    css=CSS,
)

CLOZE = genanki.Model(
    MODEL_CLOZE, "TUC Lückentext (Cloze)",
    fields=[{"name": n} for n in ["Text", "Extra", "Figure", "FigureBack", "Header", "Source", "ID"]],
    templates=[{
        "name": "Lücke",
        "qfmt": f'<div class="wrap">{CHIP}<div class="q cl">{{{{cloze:Text}}}}</div>{FIG_FRONT}</div>',
        "afmt": (f'<div class="wrap">{CHIP}<div class="q cl">{{{{cloze:Text}}}}</div>{FIG_BACK}'
                 f'<hr id="answer">{TAIL}</div>'),
    }],
    css=CSS,
    model_type=genanki.Model.CLOZE,
)

CODE = genanki.Model(
    MODEL_CODE, "TUC Code",
    fields=[{"name": n} for n in ["Prompt", "Code", "Answer", "Explanation", "Header", "Source", "ID"]],
    templates=[{
        "name": "Code",
        "qfmt": f'<div class="wrap">{CHIP}<div class="q">{{{{Prompt}}}}</div>{{{{Code}}}}</div>',
        "afmt": (f'<div class="wrap">{CHIP}<div class="q">{{{{Prompt}}}}</div>{{{{Code}}}}'
                 '<hr id="answer"><div class="a">{{Answer}}</div>'
                 '{{#Explanation}}<div class="extra">{{Explanation}}</div>{{/Explanation}}'
                 '{{#Source}}<div class="src">{{Source}}</div>{{/Source}}</div>'),
    }],
    css=CSS,
)

KIND_LABEL = {
    "de": {"predict": "Was gibt es aus?", "bug": "Finde den Fehler", "fill": "Ergänze den Code",
           "error": "Fehlermeldung", "cloze": "Lücke", "figure": "Abbildung", "basic": "Frage"},
    "en": {"predict": "Predict the output", "bug": "Spot the bug", "fill": "Complete the code",
           "error": "Error message", "cloze": "Cloze", "figure": "Figure", "basic": "Question"},
}


class StableNote(genanki.Note):
    @property
    def guid(self):
        return genanki.guid_for("ws2627", self.fields[-1])  # ID is always the last field


def header_html(lec: dict, label: str) -> str:
    return f'<span>{html.escape(lec["header"])}</span><span class="kind">{html.escape(label)}</span>'


def img(name: str | None) -> str:
    return f'<img src="{name}">' if name else ""


def card_tags(course: str, lec: dict, card: dict) -> list[str]:
    tag = COURSES[course]["tag"]
    short = lec["id"][len(course) + 1:].upper()  # VL03
    t = [f"{tag}::{short}", f"typ::{card.get('kind') or card['type']}"]
    t += [str(x).replace(" ", "_") for x in card.get("tags", [])]
    return t


def build_note(course: str, lec: dict, card: dict, media: set[str]):
    lang = lec.get("lang", COURSES[course]["lang"])
    labels = KIND_LABEL[lang]
    fig_f, fig_b = figures(card)
    media.update(x for x in (fig_f, fig_b) if x)
    src = html.escape(card.get("source", ""))
    t = card["type"]
    kind = card.get("kind")
    label = card.get("label") or labels.get(kind or ("figure" if fig_b else t), labels["basic"])
    head = header_html(lec, label)
    tags = card_tags(course, lec, card)
    if t == "basic":
        fields = [md(card["front"]), md(card["back"]), md(card.get("extra")), img(fig_f), img(fig_b),
                  head, src, card["id"]]
        return StableNote(model=BASIC, fields=fields, tags=tags)
    if t == "cloze":
        fields = [md(card["text"]), md(card.get("extra")), img(fig_f), img(fig_b), head, src, card["id"]]
        return StableNote(model=CLOZE, fields=fields, tags=tags)
    if t == "code":
        code = code_html(card["code"], card.get("lang", "java"), linenos=card.get("linenos", kind in ("bug", "error")))
        if kind == "fill":
            text = md(card["prompt"]) + code
            extra = md(card.get("explanation"))
            if card.get("answer"):
                extra = output_html(card["answer"], lang) + extra
            fields = [text, extra, "", "", head, src, card["id"]]
            return StableNote(model=CLOZE, fields=fields, tags=tags)
        if kind == "predict":
            answer = output_html(card["answer"], lang)
        else:
            answer = md(card["answer"])
        fields = [md(card["prompt"]), code, answer, md(card.get("explanation")), head, src, card["id"]]
        return StableNote(model=CODE, fields=fields, tags=tags)
    raise ValueError(f"{card['id']}: unknown type {t}")


# ---------------------------------------------------------------- preview
def _render_tmpl(tmpl: str, f: dict) -> str:
    for _ in range(3):
        tmpl = re.sub(r"\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}", lambda m: m.group(2) if f.get(m.group(1)) else "", tmpl, flags=re.S)
        tmpl = re.sub(r"\{\{\^(\w+)\}\}(.*?)\{\{/\1\}\}", lambda m: "" if f.get(m.group(1)) else m.group(2), tmpl, flags=re.S)
    return re.sub(r"\{\{(?:cloze:)?(\w+)\}\}", lambda m: f.get(m.group(1), ""), tmpl)


def _cloze(text: str, n: int, back: bool) -> str:
    def rep(m):
        num, ans, hint = int(m.group(1)), m.group(2), m.group(3)
        if num != n:
            return ans
        if back:
            return f'<span class="cloze">{ans}</span>'
        return f'<span class="cloze">[{hint or "…"}]</span>'
    return re.sub(r"\{\{c(\d+)::(.*?)(?:::(.*?))?\}\}", rep, text, flags=re.S)


def preview_cards(note: genanki.Note):
    f = dict(zip([x["name"] for x in note.model.fields], note.fields))
    tmpl = note.model.templates[0]
    if note.model.model_type == genanki.Model.CLOZE:
        nums = sorted({int(x) for x in re.findall(r"\{\{c(\d+)::", f["Text"])})
        for n in nums:
            ff = dict(f, Text=_cloze(f["Text"], n, False))
            fb = dict(f, Text=_cloze(f["Text"], n, True))
            yield _render_tmpl(tmpl["qfmt"], ff), _render_tmpl(tmpl["afmt"], fb)
    else:
        yield _render_tmpl(tmpl["qfmt"], f), _render_tmpl(tmpl["afmt"], f)


def write_preview(groups: list[tuple[str, str, list]], out: Path, media: set[str]):
    out.mkdir(parents=True, exist_ok=True)
    for m in media | set(FONTS):
        shutil.copy(media_path(m), out / m)
    parts = ["<!doctype html><meta charset='utf-8'><title>Deck preview</title>",
             f"<style>{CSS}\nbody{{margin:0;background:#ccd5d0;font-family:sans-serif}}"
             ".row{display:grid;grid-template-columns:1fr 1fr;gap:0;}"
             ".row>.card{padding:6px 0;min-width:0}.lbl{font:12px monospace;padding:4px 10px;color:#333;background:#e8ece9}"
             "h2{font:600 20px sans-serif;padding:16px 12px 4px;margin:0}"
             "nav{padding:10px;font:13px sans-serif;columns:3}nav a{display:block}"
             "@media(max-width:900px){.row{grid-template-columns:1fr}}</style>"]
    parts.append("<nav>" + "".join(f'<a href="#{gid}">{html.escape(title)}</a>' for gid, title, _ in groups) + "</nav>")
    for gid, title, notes in groups:
        parts.append(f'<h2 id="{gid}">{html.escape(title)} ({len(notes)} Notizen)</h2>')
        for note in notes:
            for i, (q, a) in enumerate(preview_cards(note)):
                cid = note.fields[-1]
                parts.append(f'<div class="lbl">{cid} · card {i+1} · {note.model.name}</div>')
                parts.append(f'<div class="row"><div class="card">{q}</div><div class="card">{a}</div></div>')
                parts.append(f'<div class="row"><div class="card nightMode">{q}</div><div class="card nightMode">{a}</div></div>')
    (out / "index.html").write_text("\n".join(parts), encoding="utf-8")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", choices=list(COURSES))
    ap.add_argument("--only", help="comma-separated lecture ids")
    ap.add_argument("--no-apkg", action="store_true")
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None

    per_course: dict[str, list] = {}
    all_media: set[str] = set()
    groups = []
    for course, path, data in load_lectures(args.course):
        lec = data["lecture"]
        if only and lec["id"] not in only:
            continue
        deck_name = f'{COURSES[course]["root"]}::{lec["deck"]}'
        deck = genanki.Deck(stable_id("deck:" + deck_name), deck_name)
        lang = lec.get("lang", COURSES[course]["lang"])
        deck.description = lec.get("description", "")
        media: set[str] = set()
        notes = []
        for card in data.get("cards", []):
            if card.get("hold"):
                continue
            note = build_note(course, dict(lec, lang=lang), card, media)
            deck.add_note(note)
            notes.append(note)
        per_course.setdefault(course, []).append((deck, media))
        all_media |= media
        groups.append((lec["id"], deck_name, notes))
        print(f"{deck_name}: {len(notes)} notes")

    if not args.no_apkg:
        (ROOT / "out").mkdir(exist_ok=True)
        for course, items in per_course.items():
            decks = [d for d, _ in items]
            media = set().union(*[m for _, m in items]) | set(FONTS)
            pkg = genanki.Package(decks)
            pkg.media_files = [str(media_path(m)) for m in sorted(media)]
            suffix = "" if not only else "-partial"
            out = ROOT / "out" / f"{course}-ws2627{suffix}.apkg"
            pkg.write_to_file(out)
            print("wrote", out)
    write_preview(groups, ROOT / "preview", all_media)
    print("preview:", ROOT / "preview" / "index.html")


if __name__ == "__main__":
    main()
