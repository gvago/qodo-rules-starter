import unittest
from llvm_cov_to_coverage_json import convert

EXPORT = {"data": [{"files": [{"filename": "/repo/a.cpp", "branches": [[2, 19, 2, 27, 0, 1, 1, 0, 4], [6, 21, 6, 30, 1, 0, 0, 0, 4]], "expansions": [{"branches": [[2, 19, 2, 27, 0, 1, 1, 0, 4]], "source_region": [4, 12, 4, 17, 1, 0, 1, 1]}]}]}]}


class ConvertTest(unittest.TestCase):
    def test_macro_branch_is_attributed_to_invocation_line(self):
        files = convert(EXPORT, '/repo')['files']['a.cpp']
        # Macro on line 2 is invoked on line 4: its decision must appear there.
        self.assertIn([4, -1], files['missing_branches'])
        self.assertIn([4, -2], files['executed_branches'])
        self.assertFalse(any(a[0] == 2 for a in files['missing_branches'] + files['executed_branches']))


if __name__ == '__main__':
    unittest.main()
