"""Tests for narrate.py --check (spec 3.3 and 4.4): the engine of the script's lang, the three
script errors that each stop the check alone, and the guard of a Russian narration. Every case
runs narrate.py as a process on a script written to a temp dir; no engine runs. Each test names
the mutation that turns it red."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_narrate import FILM_TEMPLATE, NARRATE_PY, TEMPLATE

CLEAN = "Код готов."
ENGLISH = "Hello there."
ADD = " (add to pronounce)"
WRITE_OUT = " (write the words out, as «то есть»)"
HEAVY_MODULES = ("torch", "numpy", "kokoro_onnx", "soundfile")   # the check path imports none of them


class CheckCase(unittest.TestCase):
    """A script is the film template's header (the brainrot template's where a case says so),
    the case's own header keys, and its scenes with "id" and "narration" only, in the given
    order. Every run has a PYTHONPATH where torch, numpy, kokoro_onnx and soundfile raise on
    import, so a check that imports one of them fails."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="narrate-check-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.audio = self.tmp / "audio"
        self.count = 0
        stubs = self.tmp / "stubs"
        stubs.mkdir()
        for name in HEAVY_MODULES:
            (stubs / f"{name}.py").write_text(f"raise ImportError('{name} is imported')\n", encoding="utf-8")
        self.env = dict(os.environ, PYTHONPATH=str(stubs))

    def script(self, scenes, template=FILM_TEMPLATE, **keys):
        """Write a new script file and return its path; scenes are (id, narration) pairs."""
        header = {k: v for k, v in json.loads(template.read_text(encoding="utf-8")).items() if k != "scenes"}
        script = dict(header, **keys, scenes=[{"id": sid, "narration": text} for sid, text in scenes])
        self.count += 1
        path = self.tmp / f"script-{self.count}.json"
        path.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
        return path

    def ru(self, narration, **keys):
        """A Russian script of one scene "intro"."""
        return self.script([("intro", narration)], lang="ru", **keys)

    def run_narrate(self, *args):
        return subprocess.run(
            [sys.executable, str(NARRATE_PY), *map(str, args)],
            capture_output=True, encoding="utf-8", env=self.env,
        )

    def check(self, script, *options):
        return self.run_narrate("--check", *options, script)

    def assert_engine(self, run, engine):
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, engine + "\n", ""))

    def assert_fails(self, run, *lines):
        """Exit 2 and exactly these lines on stdout, each after "narration: FAIL "."""
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertEqual(run.stdout, "".join(f"narration: FAIL {line}\n" for line in lines))


class EngineAndScript(CheckCase):
    def test_check_prints_the_engine_of_the_lang(self):
        """Mutation: --check prints a fixed engine, or ignores lang, or ignores --engine; or the
        check path imports torch, numpy, kokoro_onnx or soundfile (the stand-ins raise)."""
        self.assert_engine(self.check(self.script([("intro", ENGLISH)])), "kokoro")
        russian = self.ru(CLEAN)
        self.assert_engine(self.check(russian), "silero")
        self.assert_engine(self.check(russian, "--engine", "say"), "say")

    def test_engine_must_fit_lang(self):
        """Mutation: the engine is not checked against lang, or the line names another engine or lang."""
        self.assert_fails(self.check(self.ru(CLEAN), "--engine", "kokoro"), "engine kokoro cannot narrate lang ru")
        english = self.script([("intro", ENGLISH)])
        self.assert_fails(self.check(english, "--engine", "silero"), "engine silero cannot narrate lang en")

    def test_lang_ru_narrates_at_speed_1_only(self):
        """Mutation: the speed is not checked for ru, or it is checked for English too."""
        self.assert_fails(self.check(self.ru(CLEAN), "--speed", "1.2"), "lang ru narrates at speed 1.0 only")
        self.assert_engine(self.check(self.script([("intro", ENGLISH)]), "--speed", "1.2"), "kokoro")

    def test_the_first_three_errors_stop_alone(self):
        """Mutation: the check collects the format, engine, speed and guard errors together, or
        runs them in another order."""
        latin = "Hello there, port 8080."   # the guard refuses it
        slides = self.ru(latin, format="slides")
        self.assert_fails(
            self.check(slides, "--engine", "kokoro", "--speed", "1.2"),
            f"script {slides}: format must be film, brainrot or clip")
        russian = self.ru(latin)
        self.assert_fails(self.check(russian, "--engine", "kokoro", "--speed", "1.2"), "engine kokoro cannot narrate lang ru")
        self.assert_fails(self.check(russian, "--speed", "1.2"), "lang ru narrates at speed 1.0 only")

    def test_script_rules_of_the_validator(self):
        """Mutation: a rule of build-timeline.mjs's checkLang is not copied, or its cause text
        differs, or more than the first cause prints, or a key with a no-break space passes (a
        test for the ASCII space only), or a key is quoted with ASCII escapes."""
        ru = {"lang": "ru"}
        cases = [
            (FILM_TEMPLATE, {"lang": "de"}, "lang must be en or ru"),
            (FILM_TEMPLATE, {"lang": 7}, "lang must be en or ru"),
            (TEMPLATE, ru, "lang ru is for the film and clip formats only"),
            (FILM_TEMPLATE, {"pronounce": {"JSON": "джейсон"}}, "pronounce needs lang ru"),
            (FILM_TEMPLATE, dict(ru, pronounce=["JSON"]), "pronounce must be an object"),
            (FILM_TEMPLATE, dict(ru, pronounce={"": "пусто"}), 'pronounce key "" is empty'),
            (FILM_TEMPLATE, dict(ru, pronounce={"Spring Boot": "спринг бут"}),
             'pronounce key "Spring Boot" holds whitespace'),
            # A no-break space (U+00A0) between the two words.
            (FILM_TEMPLATE, dict(ru, pronounce={"Spring Boot": "спринг бут"}),
             'pronounce key "Spring Boot" holds whitespace'),
            (FILM_TEMPLATE, dict(ru, pronounce={"т.": "то"}), 'pronounce key "т." ends with "."'),
            # Two causes; only the first prints.
            (FILM_TEMPLATE, dict(ru, pronounce={"a b?": "эй"}), 'pronounce key "a b?" holds whitespace'),
            (FILM_TEMPLATE, dict(ru, pronounce={"JSON": "  "}),
             'pronounce value of "JSON" must be a string with a non-space character'),
            (FILM_TEMPLATE, dict(ru, pronounce={"JSON": 5}),
             'pronounce value of "JSON" must be a string with a non-space character'),
        ]
        for template, keys, cause in cases:
            with self.subTest(cause=cause, keys=keys):
                script = self.script([("intro", CLEAN)], template, **keys)
                self.assert_fails(self.check(script), f"script {script}: {cause}")

    def test_an_exception_is_a_fail_line_not_a_traceback(self):
        """Mutation: an exception inside the check escapes as a traceback (exit 1)."""
        script = self.script([("intro", 5)], lang="ru")
        run = self.check(script)
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertTrue(run.stdout.startswith(f"narration: FAIL script {script}: "), run.stdout)
        self.assertEqual(len(run.stdout.splitlines()), 1, run.stdout)
        self.assertNotIn("Traceback", run.stderr)

    def test_check_takes_the_script_alone(self):
        """Mutation: --check accepts an audio dir, --models or --fallback and ignores it."""
        script = self.ru(CLEAN)
        for extra in ([script, self.audio], ["--models", self.tmp, script], ["--fallback", "uv not found", script]):
            with self.subTest(extra=extra):
                run = self.run_narrate("--check", *extra)
                self.assertEqual((run.returncode, run.stdout), (2, ""), run.stderr)
                self.assertTrue(run.stderr.startswith("usage: "), run.stderr)


class Guard(CheckCase):
    def test_unspoken_text_line(self):
        """Mutation: a token shows with its punctuation ("8080."), or the scenes are not in script
        order, or a look-alike gets no code point, or a Latin word or a number gets one, or a
        token of capitals ("СУБД") passes."""
        # K is a Latin K in front of the Cyrillic "афка".
        script = self.script(
            [("tools", "Шаблон KafkaTemplate на 8080."), ("intro", "Это JSON, Kафка и СУБД.")], lang="ru")
        self.assert_fails(
            self.check(script),
            'unspoken text: tools: "KafkaTemplate", "8080"; intro: "JSON", "Kафка" (U+004B), "СУБД"' + ADD)

    def test_each_character_rule_fails(self):
        """Mutation: "+" passes before any letter, or a zero-width space passes, or "#" passes, or
        a code point shows for a digit or a Latin word, or none shows for a character that is
        not a letter, or two capitals pass."""
        cases = [
            ("#", '"#" (U+0023)'),
            ("+т", '"+т" (U+002B)'),               # a "+" before a consonant
            ("сло​во", '"сло​во" (U+200B)'),   # a zero-width space inside the word
            ("5", '"5"'),
            ("code", '"code"'),
            ("ОС", '"ОС"'),
        ]
        for token, shown in cases:
            with self.subTest(token=token):
                self.assert_fails(self.check(self.ru(f"Это {token} тут.")), f"unspoken text: intro: {shown}{ADD}")

    def test_a_value_with_latin_is_reported(self):
        """Mutation: the guard reads the written token and skips one that is a pronounce key, so
        the Latin left in its value passes."""
        script = self.ru("Это JSON.", pronounce={"JSON": "джейсон JSON"})
        self.assert_fails(self.check(script), 'unspoken text: intro: "JSON"' + ADD)

    def test_abbreviation_line(self):
        """Mutation: a one-letter abbreviation passes, or a "(" before it shows, or "т.е." passes,
        or a sentence-final "напр." before a lower-case sentence passes. In the first four cases
        each abbreviation also ends a sentence before a lower-case one; the last two are caught
        by the one-letter form alone (the "д." that ends the narration) and by the "." between
        two letters alone ("т.е.," inside a sentence)."""
        cases = [
            ("Это т. е. пример.", '"т.", "е."'),
            ("Это (т. е. пример).", '"т.", "е."'),
            ("Это т.е. пример.", '"т.е."'),
            ("Смотрите напр. так.", '"напр."'),
            ("Это сделали и т. д.", '"т.", "д."'),
            ("Это, т.е., пример.", '"т.е."'),
        ]
        for text, shown in cases:
            with self.subTest(text=text):
                self.assert_fails(self.check(self.ru(text)), f"abbreviation: intro: {shown}{WRITE_OUT}")

    def test_a_key_does_not_hide_an_abbreviation(self):
        """Mutation: the abbreviation rule reads the spoken text, where the key turns "т." into "то."."""
        script = self.ru("Это т. е. пример.", pronounce={"т": "то"})
        self.assert_fails(self.check(script), 'abbreviation: intro: "т.", "е."' + WRITE_OUT)

    def test_these_pass(self):
        """Mutation: a quote, bracket, dash or ellipsis is refused, or "я." is taken for an
        abbreviation, or "+" before a vowel (either case) is refused, or "напр." with no sentence
        after it is an abbreviation, or the guard reads the written text (a mapped key fails, a
        backtick shows)."""
        texts = (
            "«Так», — сказал он: (да) „нет“ ‘да’ … – конец!",
            "Так решил я.",
            "Это к+афка.",
            "+Эхо идёт.",
            "Конец, напр.",
        )
        for text in texts:
            with self.subTest(text=text):
                self.assert_engine(self.check(self.ru(text)), "silero")
        mapped = self.ru("Это `JSON`, а не 404.", pronounce={"JSON": "джейсон", "404": "четыреста четыре"})
        self.assert_engine(self.check(mapped), "silero")

    def test_no_letter_line(self):
        """Mutation: a letter after "+" counts, or a sentence of punctuation passes, or sentences
        are counted from 0."""
        script = self.script([("intro", "Начало. ..."), ("outro", "+ё.")], lang="ru")
        self.assert_fails(self.check(script), "no letter: intro sentence 2; outro sentence 1")

    def test_too_long_line(self):
        """Mutation: the limit is off by one, or the length is of the written sentence (a long
        value passes)."""
        self.assert_fails(self.check(self.ru("а" * 900 + ".")), "too long: intro sentence 1 (901 characters) (max 900)")
        self.assert_engine(self.check(self.ru("а" * 899 + ".")), "silero")
        expanded = self.ru("Это A.", pronounce={"A": "а" * 900})   # spoken: "Это " + 900 letters + "."
        self.assert_fails(self.check(expanded), "too long: intro sentence 1 (905 characters) (max 900)")

    def test_lines_come_in_rule_order(self):
        """Mutation: the lines come per scene, not per rule, or in another rule order, or the
        scenes are sorted, or scenes are separated by ", "."""
        zeta = "Код 8080 т. е. так. " + "Д" + "а" * 900 + ". " + "О" + "о" * 904 + ". ... ?!"
        alpha = "+ё. Это JSON, т.е. так. " + "Б" + "б" * 949 + "."
        script = self.script([("zeta", zeta), ("alpha", alpha)], lang="ru")
        self.assert_fails(
            self.check(script),
            'unspoken text: zeta: "8080"; alpha: "JSON"' + ADD,
            'abbreviation: zeta: "т.", "е."; alpha: "т.е."' + WRITE_OUT,
            "no letter: zeta sentence 6, 7; alpha sentence 1",
            "too long: zeta sentence 4 (902 characters), 5 (906 characters); alpha sentence 4 (951 characters) (max 900)",
        )

    def test_english_is_not_guarded(self):
        """Mutation: the guard runs for every lang."""
        self.assert_engine(self.check(self.script([("intro", "Port 8080, т.е. the port.")])), "kokoro")

    def test_say_is_guarded_too(self):
        """Mutation: --engine say skips the guard."""
        self.assert_fails(self.check(self.ru("Порт 8080."), "--engine", "say"), 'unspoken text: intro: "8080"' + ADD)


class Synthesis(CheckCase):
    def test_synthesis_applies_the_check(self):
        """Mutation: a synthesis run skips the check, so say narrates the script (or refuses it for
        another cause)."""
        run = self.run_narrate("--engine", "say", self.ru("Порт 8080."), self.audio)
        self.assert_fails(run, 'unspoken text: intro: "8080"' + ADD)
        self.assertFalse(self.audio.exists(), "no audio dir is made")

    def test_mismatch_before_models(self):
        """Mutation: the engine is built (and its models checked) before the script is checked."""
        models = self.tmp / "models"
        models.mkdir()
        run = self.run_narrate("--engine", "kokoro", "--models", models, self.ru(CLEAN), self.audio)
        self.assert_fails(run, "engine kokoro cannot narrate lang ru")
        self.assertFalse(self.audio.exists())

    def test_silero_needs_models(self):
        """Mutation: --engine silero runs without --models (a traceback or "models missing")."""
        run = self.run_narrate("--engine", "silero", self.ru(CLEAN), self.audio)
        self.assertEqual((run.returncode, run.stdout), (2, ""), run.stderr)
        self.assertTrue(run.stderr.startswith("usage: "), run.stderr)
        self.assertIn("--engine silero needs --models <dir>", run.stderr)


if __name__ == "__main__":
    unittest.main()
