import contextlib
import io
import json
import unittest
from unittest.mock import patch

from toolz_cli import readiness


class ReadinessTests(unittest.TestCase):
    def test_present_executables_never_imply_verified_integration(self):
        result = readiness.inventory(lambda name: "/private/" + name, "Linux")
        self.assertTrue(all(tool["available"] for tool in result["tools"].values()))
        self.assertFalse(result["ready_for_device_execution"])
        self.assertEqual(set(result["verification"].values()), {"pending"})
        self.assertNotIn("/private/", json.dumps(result))

    def test_missing_tools_and_windows_host(self):
        queried = []
        def lookup(name):
            queried.append(name)
            return "C:\\tools\\git.exe" if name == "git" else None
        result = readiness.inventory(lookup, "Windows")
        self.assertEqual(queried, list(readiness.TOOLS))
        self.assertTrue(result["tools"]["git"]["available"])
        self.assertFalse(result["tools"]["cline"]["available"])
        self.assertEqual(result["host_system"], "Windows")

    def test_json_output_is_machine_readable_and_omits_secret_marker(self):
        with patch.dict("os.environ", {"BRIDGE_CONTROLLER_TOKEN": "private-test-marker"}):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(readiness.main(["--json"]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["schema_version"], 1)
        self.assertNotIn("private-test-marker", output.getvalue())
        self.assertFalse(result["ready_for_device_execution"])

    def test_unknown_arguments_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as failure:
            readiness.main(["--execute"])
        self.assertEqual(failure.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
