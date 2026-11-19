# Contributing

Corrections, new cards and removals are all welcome. Small fixes are the most useful kind:
a typo, a wrong year, an answer that is too vague.

## The quick way

1. Find the card with the repository search: a few words from it, or its ID (e.g. `gdp-vl03-005`).
2. Click the pencil icon, edit, and choose *Propose changes*.
3. Say in one sentence why. A check runs on the pull request; if it fails, the log names the card.

## Rules for the files

- **Never change or reuse an `id`.** The ID is how Anki recognises a card. If it changes, everyone
  who already studies the card loses its history.
- **Add new cards at the end** of the lecture's list, with the next free number.
- **To remove a card, don't delete it.** Add `hold: "reason"` to it. It then stays out of the deck
  and the ID is never reused.
- One file per lecture. Strings in double quotes. Keep `source:` (lecture and slide).
- **German and English.** `cards/gdp/` is the original. `cards/gdp-en/` holds the translated text
  for the same IDs and nothing else. If you change the German text, please update the English entry
  too, or say in the pull request that it still needs translating. A card without an English entry
  is left out of the English deck.
- **Code cards are compiled and run.** For a `predict` card, `answer` must be exactly what the
  program prints. A `bug` or `error` card must really fail the way `expect:` says.

## Card format

```yaml
- id: gdp-vl03-005          # fixed
  type: basic              # basic | cloze | code
  front: "Question"
  back: "**Answer in bold.** One or two sentences of explanation."
  extra: "Optional: example, contrast, where it matters."
  source: "Lecture 3, slide 12"
  tags: [transfer]         # optional
  figure: "name.png"       # optional, file in figures/
  figure_back: "name-back.png"   # optional, replaces the figure on the answer side
```

Cloze cards use `text:` with `{{c1::hidden part}}`. Text fields understand `**bold**`,
`*italic*`, `` `code` `` and `- ` bullet lists.

Code cards:

```yaml
- id: gdp-vl01-001
  type: code
  kind: predict            # predict | bug | fill | error
  prompt: "Was gibt dieses Programm aus?"
  code: |
    int a = 7;
    System.out.println(a / 2);
  answer: "3"
  explanation: "Why."
  # bug / error cards also need: expect: compile_error | runtime_error | wrong_output
```

A snippet without a class is wrapped in `main` automatically. `run:` with `{code}` gives a custom
wrapper; the lecture-level `support:` adds helper classes.

## What makes a good card

- **One thing per card.** One question, one correct answer. If the answer has an "and", split it.
- **Understandable on its own.** The card will show up between cards from other lectures, so the
  question has to name its context.
- **No yes/no questions.** Ask "which", "why" or "what happens if".
- **No "list all seven…" cards.** Use one cloze per item, or ask which category an example belongs to.
- **Short.** Question up to about 220 characters, answer up to 600. Answer first, then why.
- **Only one reasonable answer.** If a different correct answer is possible, narrow the question.
- **Only what the lecture covers**, in the lecture's own terms. No names of staff, nothing about exams.
- **Plain language.** Short sentences, no filler.
- **Figures** only when the content is visual, and only your own drawings. No photos, screenshots
  or figures copied from papers or books.

## Check locally (optional)

```sh
pip install -r requirements.txt
python3 tools/check_cards.py            # must end with "0 errors"
python3 tools/build_deck.py             # out/*.apkg and preview/index.html
```

## Licence

By contributing you agree that your cards are published under CC BY-SA 4.0 and code under MIT.
