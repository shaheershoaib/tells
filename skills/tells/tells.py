#!/usr/bin/env python3
"""tells: catch the phrases that make an AI reply read as AI-written.

  tells.py scan              text on stdin -> the tells found; exit 1 if any (any harness, CI, a draft)
  tells.py rule              Claude Code SessionStart hook: the one-line rule, once per session
                             (and again after a compaction or resume)
  tells.py remind            Claude Code UserPromptSubmit hook: when the previous reply carried a
                             tell, names it next to the new prompt; silent otherwise, so a clean
                             session pays nothing per turn
  tells.py check             Claude Code Stop hook: sends a reply back once for a rewrite; only
                             active with TELLS_BLOCK=1
  tells.py report [--days N] [--root DIR]
                             share of replies carrying a tell, per week, from Claude Code transcripts

Patterns live in patterns.json beside this file. TELLS_OFF="dash,intensifier" turns ids off.
Text inside code fences, inline backticks, double quotes and > blockquotes is skipped, so a
reply can discuss a phrase without using it. Stdlib only. The hook modes fail open: an error
here never breaks a session.
"""
import datetime
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_patterns():
    off = {s.strip() for s in os.environ.get("TELLS_OFF", "").split(",") if s.strip()}
    with open(os.path.join(HERE, "patterns.json"), encoding="utf-8") as f:
        return [dict(p, rx=re.compile(p["regex"], re.IGNORECASE)) for p in json.load(f) if p["id"] not in off]


def strip_quoted(text):
    text = re.sub(r"(?s)```.*?```", " ", text)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r'"[^"]{1,200}"|\u201c[^\u201d]{1,200}\u201d', " ", text)
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith(">"))


def find(text, patterns):
    """[(pattern, count, snippet)] for each pattern present in the unquoted prose."""
    prose, found = strip_quoted(text), []
    for p in patterns:
        hits = list(p["rx"].finditer(prose))
        if hits:
            s, e = max(0, hits[0].start() - 30), min(len(prose), hits[0].end() + 30)
            found.append((p, len(hits), " ".join(prose[s:e].split())))
    return found


def entry_text(entry):
    blocks = (entry.get("message") or {}).get("content") or []
    return "\n".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")


def is_prompt(entry):
    """A prompt the person typed, as opposed to a tool result or injected context."""
    return (entry.get("type") == "user" and not entry.get("isMeta")
            and isinstance((entry.get("message") or {}).get("content"), str))


def last_reply(transcript_path):
    try:
        with open(transcript_path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except (OSError, TypeError):
        return ""
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("type") == "assistant" and not entry.get("isSidechain") and entry_text(entry):
            return entry_text(entry)
    return ""


def cmd_scan():
    found = find(sys.stdin.read(), load_patterns())
    for p, n, snip in found:
        print('%s (x%d): "...%s..."' % (p["name"], n, snip))
    sys.exit(1 if found else 0)


def context(event, msg):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": msg}}))


def cmd_rule():
    try:
        patterns = load_patterns()
    except Exception:
        sys.exit(0)
    context("SessionStart", "Writing style (tells): in replies and drafts, avoid "
            + "; ".join(p["brief"] for p in patterns) + ". Say the point plainly. Quoted text is exempt.")


def cmd_remind():
    try:
        payload = json.load(sys.stdin)
        found = find(last_reply(payload.get("transcript_path")), load_patterns())
    except Exception:
        sys.exit(0)
    if found:
        context("UserPromptSubmit", "Writing style (tells): your previous reply used %s. Leave them out of "
                "this one." % "; ".join("%s x%d (avoid %s)" % (p["name"], n, p["brief"]) for p, n, _ in found))


def cmd_check():
    if os.environ.get("TELLS_BLOCK") != "1":
        sys.exit(0)
    try:
        payload = json.load(sys.stdin)
        if payload.get("stop_hook_active"):
            sys.exit(0)                   # blocks once per turn: the rewrite is not rechecked
        text = payload.get("last_assistant_message")
        if not isinstance(text, str):
            text = last_reply(payload.get("transcript_path"))
        found = find(text, load_patterns())
    except Exception:
        sys.exit(0)
    if not found:
        sys.exit(0)
    # exit 2 + stderr is the Stop-hook block contract: the message goes back to the agent.
    print("tells: the reply you just sent reads as AI-written:\n%s\n\nSend it again in full without "
          "these. Do not mention this check. Text you are quoting goes in double quotes, backticks "
          "or a > blockquote, which this check skips."
          % "\n".join('  - %s (x%d), e.g. "...%s..."' % (p["name"], n, s) for p, n, s in found),
          file=sys.stderr)
    sys.exit(2)


def final_replies(root, since):
    """(timestamp, model, text) of each turn's last assistant text, i.e. the reply the person read."""
    for path in glob.glob(os.path.join(root, "*", "*.jsonl")):
        if os.path.getmtime(path) < since.timestamp():
            continue
        pending = None
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("type") == "assistant" and not entry.get("isSidechain") and entry_text(entry):
                    pending = (entry.get("timestamp"), entry["message"].get("model") or "unknown", entry_text(entry))
                elif is_prompt(entry) and pending:
                    yield pending
                    pending = None
        if pending:
            yield pending


def cmd_report(args):
    days = int(args[args.index("--days") + 1]) if "--days" in args else 56
    root = args[args.index("--root") + 1] if "--root" in args else os.path.expanduser("~/.claude/projects")
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    patterns, weeks, models, totals = load_patterns(), {}, {}, {}
    for ts, model, text in final_replies(root, since):
        try:
            when = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            continue
        if when < since or model.startswith("<"):    # "<synthetic>": a canned message, not a model
            continue
        year, week, _ = when.isocalendar()
        found = find(text, patterns)
        for row in (weeks.setdefault("%d-W%02d" % (year, week), [0, 0]), models.setdefault(model, [0, 0])):
            row[0] += 1
            row[1] += bool(found)
        for p, n, _ in found:
            totals[p["name"]] = totals.get(p["name"], 0) + 1
    if not weeks:
        print("No Claude Code replies found under %s in the last %d days." % (root, days))
        return
    for title, rows, order in (("week", weeks, sorted(weeks)),
                               ("model", models, sorted(models, key=lambda m: -models[m][0]))):
        print("%-28s %7s  %s" % (title, "replies", "with a tell"))
        for key in order:
            n, bad = rows[key]
            print("%-28s %7d  %5d (%d%%)" % (key, n, bad, round(100.0 * bad / n)))
        print()
    print("replies carrying each tell:")
    for name, n in sorted(totals.items(), key=lambda kv: -kv[1]):
        print("  %-22s %d" % (name, n))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "scan":
        cmd_scan()
    elif mode == "rule":
        cmd_rule()
    elif mode == "remind":
        cmd_remind()
    elif mode == "check":
        cmd_check()
    elif mode == "report":
        cmd_report(sys.argv[2:])
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(64)                      # not 2: in a Stop hook, 2 would block


if __name__ == "__main__":
    main()
