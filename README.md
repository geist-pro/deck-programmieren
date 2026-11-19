# Programmieren: Karteikarten

Karteikarten zur Vorlesung *Grundlagen der Programmierung* (Java) an der TU Clausthal,
Wintersemester 2026/27. Ein Teilstapel pro Vorlesung, rund 290 Notizen, auf Deutsch und in einer
englischen Übersetzung. Die Karten liegen hier als Textdateien. Jede und jeder kann eine Karte per
Pull Request korrigieren, ergänzen oder entfernen.

*English: flashcards for the introductory Java course at TU Clausthal, in German with an English
translation. Everything below applies to both; see [CONTRIBUTING.md](CONTRIBUTING.md).*

## Stapel laden

`gdp-ws2627.apkg` (Deutsch) oder `gdp-en-ws2627.apkg` (English) aus dem
[neuesten Release](https://github.com/geist-pro/deck-programmieren/releases/latest) laden und in
[Bergmönch](https://apps.geist.pro/bergmoench/), Anki, AnkiDroid oder AnkiMobile öffnen.

Bei einem neuen Release die Datei noch einmal importieren. Geänderte Karten werden aktualisiert,
der Lernstand bleibt erhalten, es entstehen keine Duplikate.

## Eine Karte verbessern

Hier im Repository nach ein paar Wörtern der Karte suchen, dann steht man direkt bei ihr. Jede
Karte hat außerdem eine ID (zum Beispiel `gdp-vl03-005`); in Anki steht sie in der Kartenübersicht
im Feld *ID*.

```yaml
- id: gdp-vl05-012
  type: basic
  front: "Was ist bei einer `ArrayList` der Unterschied zwischen `add(i, x)` und `set(i, x)`?"
  back: "**`add(i, x)` fügt ein, der Rest rutscht nach rechts. `set(i, x)` ersetzt das Element bei Index i.**"
  source: "VL 5, Folie 12"
```

Auf GitHub das Stift-Symbol anklicken, den Text ändern, Änderung vorschlagen. Bei jedem Pull
Request läuft eine Prüfung, die auch jedes Java-Beispiel kompiliert und ausführt. Installieren muss
man dafür nichts.

Unsicher, wie die Korrektur aussehen soll? Dann genügt ein
[Issue](https://github.com/geist-pro/deck-programmieren/issues/new/choose) mit ein paar Wörtern der Karte.

Die englische Fassung steht in `cards/gdp-en/` in der Datei mit demselben Namen. Sie enthält nur
die übersetzten Texte; Code, Ausgaben und Abbildungen kommen aus der deutschen Karte.

Regeln für gute Karten und das Dateiformat: [CONTRIBUTING.md](CONTRIBUTING.md).

## Selbst bauen

```sh
pip install -r requirements.txt   # dazu ein JDK 25 oder neuer für die Code-Karten
python3 tools/check_cards.py      # prüft alle Karten, kompiliert die Java-Beispiele
python3 tools/build_deck.py       # schreibt out/*.apkg und preview/index.html
```

## Aufbau

| Pfad | Inhalt |
|---|---|
| `cards/gdp/*.yaml` | die deutschen Karten, eine Datei pro Vorlesung |
| `cards/gdp-en/*.yaml` | englische Übersetzung, gleiche IDs |
| `figures/` | Abbildungen auf den Karten |
| `fonts/` | Fira Sans und Fira Mono, im Stapel eingebettet |
| `tools/` | Prüfer, Builder, Importtest |

## Lizenz

Karten und Abbildungen: [CC BY-SA 4.0](LICENSE). Skripte in `tools/`: [MIT](LICENSE-CODE).
Schriften: SIL Open Font License, siehe `fonts/OFL.txt`.

Die Karten folgen der Vorlesung von Kai Kunze, [GEIST](https://geist.pro), TU Clausthal.
