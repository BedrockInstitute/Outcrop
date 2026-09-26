import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
from outcrop.adapters import extract_types


class ExtractTypesTests(unittest.TestCase):
    def test_run_agda_uses_the_selected_executable(self):
        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with mock.patch.object(extract_types.subprocess, "run", return_value=completed) as run:
            extract_types.run_agda("commands", "/project/_build/bin/outcrop-agda")
        self.assertEqual(
            run.call_args.args[0],
            ["/project/_build/bin/outcrop-agda", "--interaction-json"],
        )

    def test_main_forwards_agda_option(self):
        with mock.patch.object(extract_types, "extract", return_value={}) as extract, \
             mock.patch("builtins.print"):
            self.assertEqual(
                extract_types.main(["--agda", "/tmp/outcrop-agda", "--html-dir", "generated", "--src", "chapters"]),
                0,
            )
        extract.assert_called_once_with("generated", "chapters", "/tmp/outcrop-agda", entry=None, libraries=[], options=[])

    def test_definition_names_include_pattern_synonyms(self):
        with tempfile.TemporaryDirectory() as directory:
            html = Path(directory) / "Demo.html"
            html.write_text(
                '<a id="tt*"></a><a id="245" href="Demo.html#245" '
                'class="InductiveConstructor">tt*</a> '
                '<a id="250" class="Symbol">to</a> '
                '<a id="253" class="Function">map₁</a>',
                encoding="utf-8",
            )
            self.assertEqual(
                extract_types.definition_names(directory, ["Demo"]),
                {"Demo": [("tt*", "InductiveConstructor"), ("map₁", "Function")]},
            )

    def test_query_missing_recovers_inferred_types_and_skips_errors(self):
        output = "\n".join([
            '{"kind":"DisplayInfo","info":{"kind":"NormalForm","expr":"Set"}}',
            '{"kind":"DisplayInfo","info":{"kind":"InferredType",'
            '"expr":"Lift Unit"}}',
            '{"kind":"DisplayInfo","info":{"kind":"NormalForm",'
            '"expr":"Set"}}',
            '{"kind":"DisplayInfo","info":{"kind":"Error"}}',
            '{"kind":"DisplayInfo","info":{"kind":"NormalForm",'
            '"expr":"Set"}}',
        ])
        with mock.patch.object(extract_types, "run_agda", return_value=output) as run:
            result = extract_types.query_missing(
                "/project/types-loader.agda",
                [("Cubical.Data.Unit.Base", "tt*"), ("Demo", "private")],
                "agda",
            )
        self.assertEqual(result, {"Cubical.Data.Unit.Base": {"tt*": "Lift Unit"}})
        commands = run.call_args.args[0]
        self.assertEqual(run.call_args.kwargs['cwd'], '/project')
        self.assertIn("Cmd_infer_toplevel Simplified", commands)
        self.assertIn('"Cubical.Data.Unit.Base.tt*"', commands)
        self.assertIn("Cmd_compute_toplevel DefaultCompute", commands)

    def test_internal_parameter_names_are_not_published_as_types(self):
        ready = '{"kind":"DisplayInfo","info":{"kind":"NormalForm","expr":"Set"}}\n'
        contents = ('{"kind":"DisplayInfo","info":{"kind":"ModuleContents",'
                    '"contents":[{"name":"good","term":"A → B"},'
                    '{"name":"bad","term":"_A_4 → _A_4 / _R_5"}]}}')
        with mock.patch.object(extract_types, 'run_agda', return_value=ready + contents):
            self.assertEqual(extract_types.query('/tmp/types-loader.agda', ['Demo'], 'agda'),
                             ({'Demo': {'good': 'A → B'}}, 1))
        inferred = (ready + '{"kind":"DisplayInfo","info":{"kind":"InferredType",'
                    '"expr":"_A_4 → _A_4 / _R_5"}}\n' + ready)
        with mock.patch.object(extract_types, 'run_agda', return_value=inferred):
            self.assertEqual(extract_types.query_missing('/tmp/types-loader.agda',
                             [('Demo', 'Box.wrap')], 'agda'), {})

    def test_load_failure_is_not_treated_as_an_empty_module(self):
        response = '{"kind":"DisplayInfo","info":{"kind":"Error","message":"library unavailable"}}'
        with mock.patch.object(extract_types, 'run_agda', return_value=response):
            with self.assertRaisesRegex(RuntimeError, 'type loader failed'):
                extract_types.query('/tmp/project/types-loader.agda', ['Start'], 'agda')

    def test_successful_empty_module_is_allowed_but_missing_response_is_not(self):
        ready = '{"kind":"DisplayInfo","info":{"kind":"NormalForm","expr":"Set"}}\n'
        empty = '{"kind":"DisplayInfo","info":{"kind":"ModuleContents","contents":[]}}'
        with mock.patch.object(extract_types, 'run_agda', return_value=ready + empty):
            self.assertEqual(extract_types.query('/tmp/types-loader.agda', ['Empty'], 'agda'), ({'Empty': {}}, 0))
        with mock.patch.object(extract_types, 'run_agda', return_value=ready):
            with self.assertRaisesRegex(RuntimeError, 'incomplete responses'):
                extract_types.query('/tmp/types-loader.agda', ['Empty'], 'agda')

    def test_nonzero_process_does_not_succeed_because_it_printed_json(self):
        result = subprocess.CompletedProcess([], 42, stdout='{}', stderr='failed')
        with mock.patch.object(extract_types.subprocess, 'run', return_value=result):
            with self.assertRaises(SystemExit):
                extract_types.run_agda('commands', 'agda')

    def test_protocol_mark_needs_no_builtin_string_and_accepts_qualification(self):
        self.assertIn('DefaultCompute "Set"', extract_types.load_commands('/tmp/loader.agda'))
        for name in ('Set', 'Agda.Primitive.Set'):
            response = '{"kind":"DisplayInfo","info":{"kind":"NormalForm","expr":"' + name + '"}}\ntail'
            self.assertEqual(extract_types.after_load(response), 'tail')


if __name__ == "__main__":
    unittest.main()
