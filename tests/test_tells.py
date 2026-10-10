import json, os, subprocess, sys, tempfile, unittest

TELLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills", "tells", "tells.py")


def run(mode, stdin, *args, **env):
    p = subprocess.run([sys.executable, TELLS, mode, *args], input=stdin, capture_output=True,
                       text=True, env=dict(os.environ, **env))
    return p.returncode, p.stdout, p.stderr


def transcript(*entries):
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for e in entries:
        f.write(json.dumps(e) + "\n")
    f.close()
    return f.name


def prompt(text, ts="2026-10-05T10:00:00Z"):
    return {"type": "user", "timestamp": ts, "message": {"content": text}}


def reply(text, ts="2026-10-05T10:01:00Z", model="model-a"):
    return {"type": "assistant", "timestamp": ts,
            "message": {"model": model, "content": [{"type": "text", "text": text}]}}


class Scan(unittest.TestCase):
    def test_catalogue_entries_are_caught(self):
        for bad in ("Half right, and the half that's wrong is the interesting half.",
                    "Here\u2019s where it gets interesting.",
                    "Here's the part that nobody tells you.",
                    "Rather than guess, I'm verifying the facts before I revise.",
                    "The document is not a spec, it's a sediment layer.",
                    "That confirmation is load-bearing.",
                    "Done \u2014 it is live."):
            self.assertEqual(run("scan", bad)[0], 1, bad)

    def test_plain_text_passes(self):
        self.assertEqual(run("scan", "Fixed. The total now matches the ledger (412.50).")[0], 0)

    def test_quoted_text_is_exempt(self):
        for ok in ("```\na \u2014 b\n```", "The phrase `load-bearing` is banned.",
                   "> Here is where it gets interesting", 'It lists "load-bearing" as a tic.'):
            self.assertEqual(run("scan", ok)[0], 0, ok)

    def test_a_quote_wrapped_across_lines_is_still_quoted(self):
        self.assertEqual(run("scan", 'avoid "Here\'s where it gets\n   interesting", "Here\'s the part nobody tells you".')[0], 0)

    def test_ordinary_use_of_half(self):
        self.assertEqual(run("scan", "API is only half of it, the other half is URL generation.")[0], 0)

    def test_tells_off_disables_an_id(self):
        self.assertEqual(run("scan", "a \u2014 b", TELLS_OFF="dash")[0], 0)


class Rule(unittest.TestCase):
    def test_session_start_gets_the_rule_without_disabled_ids(self):
        out = json.loads(run("rule", "{}", TELLS_OFF="intensifier")[1])["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "SessionStart")
        self.assertIn("avoid em and en dashes", out["additionalContext"])
        self.assertNotIn("genuinely", out["additionalContext"])


class Remind(unittest.TestCase):
    def test_names_the_last_replys_tells(self):
        path = transcript(prompt("hi"), reply("Great question \u2014 this is load-bearing."))
        code, out, _ = run("remind", json.dumps({"transcript_path": path}))
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(code, 0)
        self.assertIn("your previous reply used em/en dash x1", ctx)
        self.assertIn("load-bearing x1", ctx)

    def test_silent_after_a_clean_reply(self):
        path = transcript(prompt("hi"), reply("Fixed."))
        self.assertEqual(run("remind", json.dumps({"transcript_path": path}))[1], "")

    def test_fails_open(self):
        self.assertEqual(run("remind", "not json")[0], 0)


class Check(unittest.TestCase):
    def test_off_unless_tells_block_is_set(self):
        self.assertEqual(run("check", json.dumps({"last_assistant_message": "a \u2014 b"}))[0], 0)

    def test_blocks_once_when_on(self):
        payload = {"last_assistant_message": "a \u2014 b \u2014 c"}
        code, _, err = run("check", json.dumps(payload), TELLS_BLOCK="1")
        self.assertEqual(code, 2)
        self.assertIn("em/en dash (x2)", err)
        payload["stop_hook_active"] = True
        self.assertEqual(run("check", json.dumps(payload), TELLS_BLOCK="1")[0], 0)


class Report(unittest.TestCase):
    def test_counts_only_the_reply_the_person_read(self):
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "proj"))
        entries = [prompt("a"), reply("checking \u2014 one sec"), reply("Done."),
                   prompt("b"), reply("Great question.", model="model-b"),
                   prompt("c"), reply("canned", model="<synthetic>")]
        with open(os.path.join(root, "proj", "s.jsonl"), "w") as f:
            f.writelines(json.dumps(e) + "\n" for e in entries)
        code, out, _ = run("report", "", "--root", root, "--days", "36500")
        self.assertEqual(code, 0)
        self.assertRegex(out, r"2026-W41 +2 +1 \(50%\)")
        self.assertRegex(out, r"model-a +1 +0 \(0%\)")
        self.assertRegex(out, r"model-b +1 +1 \(100%\)")
        self.assertNotIn("synthetic", out)
        self.assertIn("praising the question", out)
        self.assertNotIn("em/en dash", out)


if __name__ == "__main__":
    unittest.main()
