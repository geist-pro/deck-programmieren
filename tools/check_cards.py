#!/usr/bin/env python3
"""Lint all card YAMLs and verify every Java code card by compiling and running it.

usage: python3 tools/check_cards.py [--course <key>] [--only <lecture-id>] [--no-java]
Exit code 1 if any ERROR.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from cardlib import CARDS, FIGS, load_lectures, plain

YESNO = re.compile(r"^(ist|sind|kann|können|darf|hat|haben|gibt es|wird|is|are|can|does|do|has|have|will|should)\b", re.I)
SOURCE_REF = re.compile(r"\b(the slide|this slide|the lecture|auf der Folie|in der Vorlesung|laut Folie|the lecturer)\b", re.I)
AI_TELLS = re.compile(r"\b(delve|underscore[sd]?|intricate|tapestry|testament|pivotal|showcas\w*|foster\w*|leverag\w*|realm|seamless\w*|crucial|paramount|it is worth noting|it's important to note|plays a (key|vital|crucial) role|entscheidend|maßgeblich|spielt eine (wichtige|zentrale) Rolle|es ist wichtig zu beachten)\b", re.I)
REQ = {"basic": ["front", "back"], "cloze": ["text"], "code": ["prompt", "code", "kind"]}
KINDS = {"predict", "bug", "fill", "error"}

errors: list[str] = []
warns: list[str] = []
held: list[str] = []


def err(cid, msg):
    errors.append(f"ERROR {cid}: {msg}")


def warn(cid, msg):
    warns.append(f"warn  {cid}: {msg}")


def java_program(card: dict, code: str) -> tuple[str, str]:
    """Return (classname, full source)."""
    support = card.get("support", "")
    if card.get("run"):
        src = card["run"].replace("{code}", code)
    elif re.search(r"\bclass\s+\w+", code):
        src = code
    else:
        body = "\n".join("        " + l for l in code.splitlines())
        src = f"public class Main {{\n    public static void main(String[] args) {{\n{body}\n    }}\n}}"
    if support:
        src = src + "\n\n" + support
    m = re.search(r"public\s+(?:final\s+)?class\s+(\w+)", src)
    if not m:
        # no public class: pick the class that has main
        m = re.search(r"class\s+(\w+)[^{]*\{(?:(?!class\s).)*?static\s+void\s+main", src, re.S)
    name = m.group(1) if m else "Main"
    return name, src


def run_java(name: str, src: str) -> tuple[str, str, str]:
    """Return (stage, stdout, stderr); stage in compile_error | runtime_error | ok."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / f"{name}.java"
        p.write_text(src, encoding="utf-8")
        c = subprocess.run(["javac", "-encoding", "UTF-8", p.name], cwd=d, capture_output=True, text=True)
        if c.returncode != 0:
            return "compile_error", "", c.stderr
        r = subprocess.run(["java", "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", name], cwd=d,
                           capture_output=True, text=True, timeout=20, input=card_stdin.get(name, ""))
        if r.returncode != 0:
            return "runtime_error", r.stdout, r.stderr
        return "ok", r.stdout, r.stderr


card_stdin: dict[str, str] = {}


def norm(s: str) -> str:
    return "\n".join(l.rstrip() for l in str(s).strip().splitlines())


def check_java(card: dict):
    cid, kind = card["id"], card["kind"]
    code = card["code"]
    filled = re.sub(r"\{\{c\d+::(.*?)(?:::.*?)?\}\}", r"\1", code, flags=re.S)
    name, src = java_program(card, filled)
    if card.get("stdin"):
        card_stdin[name] = card["stdin"]
    stage, out, se = run_java(name, src)
    expect = card.get("expect") or ("output" if kind in ("predict", "fill") else None)
    if kind == "predict" or (kind == "fill" and card.get("answer")):
        if stage != "ok":
            err(cid, f"{stage}: {se.strip()[:300]}")
        elif norm(out) != norm(card["answer"]):
            err(cid, f"output mismatch\n   expected: {card['answer']!r}\n   actual:   {out!r}")
    elif kind == "fill":
        if stage == "compile_error":
            err(cid, f"filled code does not compile: {se.strip()[:300]}")
    elif kind in ("bug", "error"):
        exp = card.get("expect")
        if not exp:
            warn(cid, "bug/error card without 'expect:' (compile_error|runtime_error|wrong_output|ok)")
            return
        if exp == "wrong_output":
            if stage != "ok":
                err(cid, f"expected wrong_output but got {stage}: {se.strip()[:200]}")
            elif card.get("wrong_output") is not None and norm(out) != norm(card["wrong_output"]):
                err(cid, f"wrong_output mismatch: actual {out!r}")
        elif stage != exp:
            err(cid, f"expected {exp}, got {stage}. stderr: {se.strip()[:300]}")
        elif exp in ("compile_error", "runtime_error") and card.get("error_contains"):
            if card["error_contains"] not in se:
                err(cid, f"stderr lacks {card['error_contains']!r}: {se.strip()[:300]}")
        # optional: the fixed version must work
        if card.get("fixed"):
            n2, s2 = java_program(card, card["fixed"])
            st2, o2, e2 = run_java(n2, s2)
            if st2 != "ok":
                err(cid, f"fixed version fails: {e2.strip()[:300]}")
            elif card.get("fixed_output") is not None and norm(o2) != norm(card["fixed_output"]):
                err(cid, f"fixed output mismatch: {o2!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course")
    ap.add_argument("--only")
    ap.add_argument("--no-java", action="store_true")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    seen: dict[str, Path] = {}
    stats = []
    for course, path, data in load_lectures(a.course):
        lec = data.get("lecture") or {}
        for k in ("id", "deck", "header"):
            if k not in lec:
                err(path.name, f"lecture.{k} missing")
        if only and lec.get("id") not in only:
            continue
        cards = data.get("cards") or []
        for mid in data.get("_missing", []):
            warn(lec.get("id"), f"untranslated card {mid} (left out of the {course} deck)")
        for oid in data.get("_orphans", []):
            err(lec.get("id"), f"translation for unknown card id {oid}")
        n_cl = n_code = 0
        for c in cards:
            cid = c.get("id", "?")
            if cid in seen:
                err(cid, f"duplicate id (also in {seen[cid].name})")
            seen[cid] = path
            if not cid.startswith(lec.get("id", "") + "-"):
                err(cid, f"id must start with {lec.get('id')}-")
            t = c.get("type")
            if t not in REQ:
                err(cid, f"bad type {t}")
                continue
            for f in REQ[t]:
                if not c.get(f):
                    err(cid, f"missing field {f}")
            if not c.get("source"):
                warn(cid, "no source")
            if t == "cloze":
                n_cl += 1
                if not re.search(r"\{\{c\d+::", c["text"]):
                    err(cid, "cloze without {{cN::}}")
                if len(plain(re.sub(r"\{\{c\d+::(.*?)(::.*?)?\}\}", r"\1", c["text"]))) > 260:
                    warn(cid, "cloze text > 260 chars")
            if t == "basic":
                fr = plain(c["front"])
                if len(fr) > 220:
                    warn(cid, f"front {len(fr)} chars > 220")
                if YESNO.match(fr.strip()) and not fr.strip().endswith(("?)",)):
                    warn(cid, f"possible yes/no question: {fr[:60]!r}")
                if len(plain(c["back"])) > 600:
                    warn(cid, "back > 600 chars")
            if t == "code":
                n_code += 1
                if c["kind"] not in KINDS:
                    err(cid, f"bad kind {c['kind']}")
                if c["kind"] == "predict" and "answer" not in c:
                    err(cid, "predict card needs answer")
                if c["kind"] == "fill" and not re.search(r"\{\{c\d+::", c["code"]):
                    err(cid, "fill card without cloze in code")
                if len(c["code"].splitlines()) > 16:
                    warn(cid, f"code has {len(c['code'].splitlines())} lines (keep ≤ 12)")
                if not a.no_java and c.get("lang", "java") == "java" and not c.get("_base_code"):
                    c.setdefault("support", lec.get("support", ""))
                    check_java(c)
            for f in ("front", "text", "prompt", "back", "extra"):
                if c.get(f) and SOURCE_REF.search(str(c[f])):
                    warn(cid, f"refers to the source in {f}")
            for f in ("front", "back", "text", "extra", "prompt", "answer", "explanation"):
                v = str(c.get(f) or "")
                if "—" in v:
                    warn(cid, f"em-dash in {f} (recast with comma/colon/period)")
                m = AI_TELLS.search(v)
                if m:
                    warn(cid, f"AI-tell word {m.group(0)!r} in {f}")
            for k in ("figure", "figure_back"):
                fig = c.get(k)
                if fig is not None and not isinstance(fig, str):
                    err(cid, f"{k} must be a file name in figures/")
                elif fig and not (FIGS / fig).exists():
                    err(cid, f"{k} missing: figures/{fig}")
            if c.get("hold"):
                held.append(f"hold  {cid}: {c['hold']}")
        stats.append((lec.get("id"), len(cards), n_cl, n_code))
    for h in held:
        print(h)
    for w in warns:
        print(w)
    for e in errors:
        print(e)
    print("\nlecture        cards  cloze  code")
    for s in stats:
        print(f"{s[0]:<14} {s[1]:>5} {s[2]:>6} {s[3]:>5}")
    print(f"\n{len(errors)} errors, {len(warns)} warnings, {len(held)} cards on hold")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
