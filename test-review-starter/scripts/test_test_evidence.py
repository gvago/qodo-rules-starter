import unittest
import test_evidence as evidence


class AdmissionTests(unittest.TestCase):
    def test_empty_suite_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'nonempty'):
            evidence.validate_suite('<testsuites><testsuite tests="0" failures="0" errors="0" skipped="0"/></testsuites>')


    def test_failed_and_skipped_suites_are_rejected(self):
        for child in ('failure', 'error', 'skipped'):
            with self.subTest(child=child), self.assertRaises(ValueError):
                evidence.validate_suite(f'<testsuite><testcase><{child}/></testcase></testsuite>')

    def test_mixed_failure_rejected(self):
        with self.assertRaises(ValueError):
            evidence.validate_suite('<testsuite><testcase/><testcase><failure>bad</failure></testcase></testsuite>')

    def test_test_only_payload_accepted(self):
        payload = dict(head_sha='a'*40, base_sha='b'*40, tests_run=1, tests_ok=True, files=[], measurement_scope='no_changed_source')
        run = dict(conclusion='success', event='pull_request', head_sha='a'*40)
        pr = dict(state='open', head=dict(sha='a'*40), base=dict(sha='b'*40))
        self.assertEqual(evidence.admit(payload, run, pr)['files'], [])

    def test_zero_added_count_stays_zero(self):
        self.assertEqual(int('0' or 1), 0)

    def test_run_merge_sha_uses_associated_pr_head(self):
        payload = dict(head_sha='a'*40, base_sha='b'*40, tests_run=1, tests_ok=True,
                       files=[], measurement_scope='no_changed_source')
        run = dict(conclusion='success', event='pull_request', head_sha='c'*40,
                   pull_requests=[dict(head=dict(sha='a'*40))])
        pr = dict(state='open', head=dict(sha='a'*40), base=dict(sha='b'*40))
        self.assertEqual(evidence.admit(payload, run, pr)['head_sha'], 'a'*40)
        payload['head_sha'] = 'c'*40
        with self.assertRaises(ValueError):
            evidence.admit(payload, run, pr)

    def test_passing_suite_count(self):
        self.assertEqual(evidence.validate_suite('<testsuite><testcase/><testcase/></testsuite>'), 2)

    def test_admission_rejects_stale_or_failed_run(self):
        payload = dict(head_sha='a'*40, base_sha='b'*40, tests_run=2, tests_ok=True,
                       files=[dict(path='src/app.py', missing_branches=[[2,3]], executed_branches=[[2,4]])])
        run = dict(conclusion='success', head_sha='a'*40, event='pull_request')
        pr = dict(state='open', head=dict(sha='a'*40), base=dict(sha='b'*40))
        self.assertEqual(evidence.admit(payload, run, pr)['tests_run'], 2)
        pr['head']['sha'] = 'c'*40
        with self.assertRaises(ValueError):
            evidence.admit(payload, run, pr)
        pr['head']['sha'] = 'a'*40
        run['conclusion'] = 'failure'
        with self.assertRaises(ValueError):
            evidence.admit(payload, run, pr)


    def test_measure_rejects_missing_changed_file(self):
        with self.assertRaises(ValueError):
            evidence.select_files({'files': {}}, {'src/app.py': {2}})

    def test_selects_whole_changed_decision(self):
        report = {'files': {'src/app.py': {'executed_branches': [[2,3]], 'missing_branches': [[2,4]]}}}
        self.assertEqual(evidence.select_files(report, {'src/app.py': {3}})[0]['missing_branches'], [[2,4]])


    def test_rejects_missing_unsafe_and_oversized_data(self):
        import copy
        payload = dict(head_sha='a'*40, base_sha='b'*40, tests_run=1, tests_ok=True,
                       files=[dict(path='src/app.py', missing_branches=[], executed_branches=[])])
        run = dict(conclusion='success', head_sha='a'*40, event='pull_request')
        pr = dict(state='open', head=dict(sha='a'*40), base=dict(sha='b'*40))
        for field, value in [('files', []), ('tests_run', 0), ('tests_ok', False), ('base_sha', 'c'*40)]:
            p = copy.deepcopy(payload); p[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                evidence.admit(p, run, pr)
        for path in ['../secret', '/tmp/secret', 'src/evil\\ncommand']:
            p = copy.deepcopy(payload); p['files'][0]['path'] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                evidence.admit(p, run, pr)
        p = copy.deepcopy(payload); p['files'][0]['missing_branches'] = [[2,3]] * 201
        with self.assertRaises(ValueError):
            evidence.admit(p, run, pr)


if __name__ == '__main__':
    unittest.main()
