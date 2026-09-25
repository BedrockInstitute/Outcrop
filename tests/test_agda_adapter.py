import json
from pathlib import Path
import re
import unittest


from outcrop.adapters.agda import build

TOOL = Path(build.__file__).parent / "resources"


class OutcropAgdaAdapterTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((TOOL / "manifest.json").read_text())
        self.adapter = TOOL / self.manifest["adapter"]
        self.patch = self.adapter.read_text()

    def test_version_lock_names_an_existing_thin_adapter(self):
        self.assertEqual(self.manifest["agda_version"], "2.8.0")
        self.assertEqual(self.manifest["happy_version"], "2.2")
        self.assertTrue(self.adapter.is_file())
        self.assertTrue((TOOL / "src/Outcrop/Agda/TypeTrace.hs").is_file())

    def test_compiler_lock_pins_hosts_but_not_a_project_library(self):
        self.assertEqual(self.manifest["tested_ghc_version"], "9.4.8")
        self.assertEqual(self.manifest["tested_cabal_version"], "3.12.1.0")
        self.assertNotIn('cubical', json.dumps(self.manifest))

    def test_adapter_only_touches_declared_semantic_hook_files(self):
        touched = {
            line.removeprefix("+++ b/")
            for line in self.patch.splitlines()
            if line.startswith("+++ b/")
        }
        self.assertEqual(touched, {
            "Agda.cabal",
            "src/full/Agda/Main.hs",
            "src/full/Agda/Interaction/Imports.hs",
            "src/full/Agda/TypeChecking/Rules/Application.hs",
            "src/full/Agda/TypeChecking/Rules/Decl.hs",
            "src/full/Agda/TypeChecking/Rules/LHS.hs",
            "src/full/Agda/TypeChecking/Rules/Term.hs",
        })

    def test_adapter_contains_calls_but_no_tracing_implementation(self):
        additions = [
            line for line in self.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        self.assertLessEqual(len(additions), 80)
        self.assertIn("Outcrop.Agda.TypeTrace", self.patch)
        self.assertNotIn("module Outcrop.", self.patch)
        self.assertNotIn("x-revision:", self.patch)
        self.assertNotIn("aeson                >=", self.patch)

    def test_universe_application_records_its_inferred_sort(self):
        self.assertIn(
            'Outcrop.traceType "application" e (sort $ getSort type_)',
            self.patch,
        )

    def test_overlay_rejects_dummy_types_structurally_before_queueing(self):
        source = (TOOL / 'src/Outcrop/Agda/TypeTrace.hs').read_text()
        self.assertIn('foldTerm isDummy type_', source)
        self.assertIn('isDummy Dummy{} = Any True', source)
        self.assertLess(source.index('foldTerm isDummy type_'), source.index('closure <- buildClosure'))

    def test_adapter_hunk_headers_match_their_bodies(self):
        lines = self.patch.splitlines()
        header = re.compile(
            r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@"
        )
        for index, line in enumerate(lines):
            match = header.match(line)
            if not match:
                continue
            old_expected = int(match.group(1) or 1)
            new_expected = int(match.group(2) or 1)
            old_actual = new_actual = 0
            for body in lines[index + 1:]:
                if body.startswith("@@ ") or body.startswith("--- a/"):
                    break
                old_actual += body.startswith((" ", "-"))
                new_actual += body.startswith((" ", "+"))
            self.assertEqual(old_actual, old_expected, line)
            self.assertEqual(new_actual, new_expected, line)

    def test_build_bootstraps_the_pinned_happy_executable(self):
        source = Path(build.__file__).read_text()
        self.assertIn('manifest["happy_version"]', source)
        self.assertIn('"--install-method=copy"', source)
        self.assertIn('"unset GHCRTS\\n"', source)
        self.assertIn('command.append(f"--with-happy={happy}")', source)


if __name__ == "__main__":
    unittest.main()
