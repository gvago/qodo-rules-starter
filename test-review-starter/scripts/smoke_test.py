"""Exercise the copyable starter in a disposable real Git repo."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as directory:
    work = Path(directory)
    shutil.copytree(root / 'example', work, dirs_exist_ok=True)
    (work / 'scripts').mkdir()
    shutil.copy2(root / 'scripts/test_evidence.py', work / 'scripts/test_evidence.py')
    def run(*args, expected=0):
        p = subprocess.run(args, cwd=work, env={**os.environ, 'PYTHONPATH': 'src'}, text=True, capture_output=True)
        if p.returncode != expected:
            raise AssertionError((args, p.returncode, p.stdout, p.stderr))
        return p.stdout.strip()
    run('git', 'init', '-q')
    run('git', 'add', 'src', 'tests')
    run('git', '-c', 'user.name=Starter test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'baseline')
    base = run('git', 'rev-parse', 'HEAD')
    (work / 'src/quotes.py').write_text('def quote(total):\n    if total >= 100:\n        return total - 10\n    return total\n')
    run('git', 'add', 'src')
    run('git', '-c', 'user.name=Starter test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'discount')
    def measure():
        (work / 'ci-output').mkdir(exist_ok=True)
        run(sys.executable, '-m', 'pytest', 'tests', '-q', '--cov=src', '--cov-branch', '--cov-report=json:ci-output/coverage.json', '--junitxml=ci-output/junit.xml')
        run(sys.executable, 'scripts/test_evidence.py', 'collect', '--base', base)
        return json.loads((work / 'ci-output/evidence.json').read_text())
    missing = measure()
    assert missing['tests_run'] == 1 and missing['files'][0]['missing_branches']
    with (work / 'tests/test_quotes.py').open('a') as f:
        f.write('\n\ndef test_boundaries():\n    assert quote(99) == 99\n    assert quote(100) == 90\n    assert quote(101) == 91\n')
    covered = measure()
    assert covered['tests_run'] == 2 and not covered['files'][0]['missing_branches']
    (work / 'ci-output/junit.xml').write_text('<testsuite tests="0"/>')
    run(sys.executable, 'scripts/test_evidence.py', 'collect', '--base', base, expected=2)
    print('PASS: copied starter, real pytest/coverage, missing -> covered, empty suite refusal')
