---
name: tells
description: Use when writing or revising text a person will read (a chat reply, a Slack or email draft, a PR description, docs), when asked to make text sound less AI-written or to check a draft for AI tells, and when asked how often replies carry them or which model writes them most. Lists the phrases and habits that mark text as AI-written (em dashes, teaser setups, "load-bearing", praising the question, "not X, it's Y" reframes), what to write instead, and a stdlib scanner that checks a draft or reports the tell rate over time.
---

# tells

A tell is a phrase or habit that marks text as AI-written before the reader has weighed what
it says. The list below comes from the crowd-sourced catalogue at https://claudeisms.org plus
the habits it groups under. Avoid the PATTERN, not only the exact phrase: a reworded version
of the same move is the same tell.

## Rules

1. **Teaser setups** that announce a point instead of making it: "Here's where it gets
   interesting", "Here's the part nobody tells you". State the point.
2. **The halves construction**: "half right, and the wrong half is the interesting half".
   Say which part is right and which is wrong.
3. **"Not X, it's Y" reframes** used for effect ("not a spec, it's a sediment layer"). Only
   correct a real misunderstanding, in plain words.
4. **Decorative engineering metaphors**: "load-bearing", "the fold", "the fulcrum", "sediment
   layer". Name the actual thing: the fact the conclusion depends on, the test that fails.
5. **Praising the question or the person**: "Great question", "You're right to ask". Answer.
6. **Narrating your own rigor**: "Rather than guess, I'm verifying...". Do the check and
   report what it showed.
7. **Intensifiers** on ordinary findings: "genuinely", "crucially", "a real regression".
   Severity comes from facts: what breaks, for whom, since when.
8. **Aphorism chains**: stacked metaphors or semicolon triads ("the X is the prize; the Y is
   the gate"). One literal sentence per idea.
9. **Em and en dashes.** Use commas, colons, parentheses or a new sentence. Hyphens in
   compound words are fine.
10. **Generic filler**: "delve", "it's worth noting", "I hope this helps", "happy to help".

Quoting someone else's words is exempt. Before sending, reread once for these; a sentence that
only sets up the next sentence gets cut.

## Check a draft

Run the scanner on the text, then rewrite each hit it names:

```bash
python3 <this skill's directory>/tells.py scan < draft.txt
```

It exits 1 when it finds a tell, so it also works as a CI or pre-commit check on docs. It skips
text in code fences, inline backticks, double quotes and > blockquotes. It matches literal
tells only; rules 1, 7 and 8 also need a read-through, because no regex catches them reliably.

## Measure

In Claude Code, `python3 <this skill's directory>/tells.py report --days 60` prints the share of
your replies that carried at least one tell, per week and per model, and which tells. Run it
before and after a change (a new model, a new rule) to see whether the change worked.

## Settings

- `TELLS_OFF="dash,intensifier"`: turn pattern ids off (ids are in `patterns.json`).
- `TELLS_BLOCK=1`: the Claude Code Stop hook sends a reply back once for a rewrite.
