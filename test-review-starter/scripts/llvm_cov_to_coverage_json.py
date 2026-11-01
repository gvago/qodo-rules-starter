"""Convert `llvm-cov export -format=text` JSON to the coverage.py-shaped JSON
that test_evidence.py collect reads. Arc encoding for non-Python code:
[line, -(2k+1)] = k-th branch on that line, true side;
[line, -(2k+2)] = same branch, false side. Negative targets never collide
with line numbers, so changed-line matching uses the decision line only."""
import json, os, sys

def convert(export, root):
    files = {}
    for f in export['data'][0]['files']:
        path = os.path.relpath(f['filename'], root)
        seen, rows = {}, {'missing_branches': [], 'executed_branches': []}
        for b in f.get('branches', []):
            line, true_n, false_n = b[0], b[4], b[5]
            k = seen[line] = seen.get(line, -1) + 1
            for n, side in ((true_n, -(2 * k + 1)), (false_n, -(2 * k + 2))):
                rows['executed_branches' if n else 'missing_branches'].append([line, side])
        files[path] = rows
    return {'meta': {'branch_coverage': True}, 'files': files}

if __name__ == '__main__':
    src, out, root = sys.argv[1:4]
    json.dump(convert(json.load(open(src)), os.path.abspath(root)), open(out, 'w'), indent=1)
