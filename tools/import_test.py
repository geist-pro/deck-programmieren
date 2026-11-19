#!/usr/bin/env python3
"""Headless import test with the official `anki` library (run with a venv that has `pip install anki`).
Imports each .apkg into a fresh throw-away collection, prints deck/card counts, renders every card
(question+answer) to catch template errors, and re-imports to prove that stable GUIDs update notes
instead of duplicating them.

usage: <venv>/bin/python tools/import_test.py out/*.apkg
"""
import sys
import tempfile
from pathlib import Path

from anki.collection import Collection, ImportAnkiPackageOptions, ImportAnkiPackageRequest


def import_pkg(col, path):
    req = ImportAnkiPackageRequest(package_path=str(path), options=ImportAnkiPackageOptions(
        merge_notetypes=True, with_scheduling=False, with_deck_configs=False))
    return col.import_anki_package(req)


def main():
    ok = True
    for p in sys.argv[1:]:
        p = Path(p).resolve()
        with tempfile.TemporaryDirectory() as d:
            col = Collection(str(Path(d) / "test.anki2"))
            out = import_pkg(col, p)
            n_notes, n_cards = col.note_count(), col.card_count()
            print(f"\n== {p.name}: {n_notes} notes, {n_cards} cards, "
                  f"new={len(out.log.new)} updated={len(out.log.updated)}")
            for name_id in sorted(col.decks.all_names_and_ids(), key=lambda x: x.name):
                c = len(col.find_cards(f'deck:"{name_id.name}" -deck:"{name_id.name}::*"'))
                if c:
                    print(f"   {c:4d} cards  {name_id.name}")
            print("   note types:", ", ".join(m["name"] for m in col.models.all()
                                            if col.models.use_count(m)))
            bad = 0
            for cid in col.find_cards(""):
                card = col.get_card(cid)
                q, a = card.question(), card.answer()
                if "{{" in q or "{{" in a or not q.strip():
                    bad += 1
                    print("   TEMPLATE PROBLEM in card", card.note()["ID"])
            media = sorted(Path(col.media.dir()).iterdir())
            print(f"   media files: {len(media)}; render problems: {bad}")
            out2 = import_pkg(col, p)
            dup = col.note_count() != n_notes
            print(f"   re-import: notes {n_notes} -> {col.note_count()} "
                  f"(new={len(out2.log.new)}, duplicates={'YES' if dup else 'no'})")
            ok &= not dup and bad == 0
            col.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
