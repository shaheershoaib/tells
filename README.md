# tells

Find out how often your coding agent's replies read as AI-written, from the transcripts it has
already saved. Then keep those phrases out of the replies that follow.

```text
$ python3 skills/tells/tells.py report --days 60
(the per-week table comes first)

model                        replies  with a tell
claude-opus-4-8                 1919   1418 (74%)
claude-opus-5-5                 1283     54 (4%)
claude-opus-5                    373    321 (86%)
claude-fable-5-1                 345     45 (13%)
claude-sonnet-5-5                103      6 (6%)
claude-fable-5                    14     12 (86%)
claude-haiku-4-5-20251001          1      0 (0%)
claude-opus-4-7                    1      1 (100%)

replies carrying each tell:
  em/en dash             1760
  intensifier            401
  load-bearing           12
  narrating rigor        9
  halves construction    7
  praising the question  6
  not-X-it's-Y reframe   3
  teaser setup           3
  generic AI filler      2
```

That is my own Claude Code history from August to October 2026. A tell is a phrase or habit a
reader spots before weighing what the text says: an em dash every other sentence, "Here's where
it gets interesting", "load-bearing", "Great question". The list starts from the crowd-sourced
catalogue at [claudeisms.org](https://claudeisms.org).

For me the model made the biggest difference. Opus 4.8 and Opus 5 put a tell in three replies
out of four or more. Opus 5.5, on the same kind of work, did it in about 1 reply in 24, and my
weekly rate fell from 69% to 4% the week I switched to it. Measure before you decide how much
enforcement you need.

## Why I built this

I wanted Claude to stop writing Claudeisms in the replies and drafts it writes for me, so I
started with a writing rule and a hook that sent back any reply carrying one. Then I ran the
scanner over my saved transcripts and found the current model had already brought the rate down
to about 4%. Blocking every slip at that rate mostly meant reading replies twice, so blocking
became opt-in and the measurement became the main feature.

## Measure yours

```bash
python3 skills/tells/tells.py report --days 60
```

It reads the session transcripts Claude Code keeps under `~/.claude/projects` and counts the
reply you read at the end of each turn, not the status lines in between. It prints the share of
replies with a tell per week and per model, then which tells. Nothing leaves your machine. By
default the Claude Code CLI deletes transcripts after 30 days (`cleanupPeriodDays`), which limits
how far back a first report can see.

## Keep them out (Claude Code)

| When | What happens | Cost |
| --- | --- | --- |
| Session start, and after a compaction | A one-line rule goes into context | about 130 tokens, once |
| Each new prompt | If the previous reply carried a tell, the agent is told which ones | nothing after a clean reply |
| End of a turn, opt-in | With `TELLS_BLOCK=1`, a reply with a tell is sent back once for a rewrite | one rewrite, and you see both versions |

The rewrite is opt-in because the end-of-turn check runs after you have read the reply. Turn it
on when replies are drafts you paste somewhere else. For ordinary chat the note on the next
prompt costs less.

The `tells` skill holds the full rules, checks a draft when asked, and runs the report.

## Install

**Claude Code** (skill, hooks and report):

```bash
claude plugin marketplace add shaheershoaib/tells
```

```bash
claude plugin install tells@tells
```

**Other agents that read skills** (Codex, Cursor, GitHub Copilot, Gemini CLI and more):

```bash
npx skills add shaheershoaib/tells
```

An agent loads a skill when it judges the skill relevant, so this covers checking drafts but is
not always on. For always-on, paste the Rules section of
[`skills/tells/SKILL.md`](skills/tells/SKILL.md) into `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` or
`.cursorrules`. The report reads Claude Code transcripts only.

**Any text, in CI or a pre-commit hook**: the scanner reads stdin and exits 1 on a tell.

```bash
python3 skills/tells/tells.py scan < docs/release-notes.md
```

Needs Python 3.9 or newer as `python3`. No dependencies.

## Settings

| Variable | Effect |
| --- | --- |
| `TELLS_OFF="dash,intensifier"` | Turns pattern ids off (ids are in [`patterns.json`](skills/tells/patterns.json)) |
| `TELLS_BLOCK=1` | Turns on the end-of-turn rewrite |

In Claude Code, set them under `env` in `~/.claude/settings.json`.

The scanner skips text inside code fences, inline backticks, double quotes and `>` blockquotes,
so a reply can discuss a phrase without being flagged for it.

## How it compares

| Tool | What it does |
| --- | --- |
| [humanizer](https://github.com/blader/humanizer) | A skill that rewrites text you hand it |
| [unslop](https://github.com/MohamedAbdallah-14/unslop) | Rewrites text in six assistants and loads its rules at session start; scores its rewrites with an LLM judge |
| [claude-code-hooks](https://github.com/m-Xone/claude-code-hooks) | Among its security hooks, scores each reply at the end of a turn and warns you or blocks |
| [anti-slop](https://github.com/TheMizeGuy/anti-slop) | Scans prose, code and UI files and keeps a score history for them |
| [slop-check](https://github.com/le0li0n/slop-check) | Warns when Claude writes prose into outward-facing files |
| tells | Measures your reply history per week and per model, then notes slips back to the agent |

None of the others (checked October 2026) reads your saved transcripts to tell you how often your
replies carried a tell, or which model wrote them. Use humanizer or unslop to rewrite a long
document; tells matches literal phrases and leaves the rewriting to the agent.

Habits that need judgement (a sentence that only sets up the next one, stacked metaphors) are
in the rules but not in the scanner, because a regex guessing at them would fire on ordinary
prose.

## Development

```bash
python3 -m unittest discover -s tests
```

CI runs the tests and scans this README and the skill for tells.

## License

[Apache 2.0](LICENSE): free to use, modify, and share, including commercially. Keep the
[`NOTICE`](NOTICE) file with any redistribution (§4(d)), and don't market a fork under the `tells`
name (§6). The patent grant in §3 means adopting this doesn't expose you to a patent claim over it.

Required Notice: Copyright Shaheer Shoaib (https://github.com/shaheershoaib)
