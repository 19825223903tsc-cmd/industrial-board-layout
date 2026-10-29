"""Tests simulate review records to validate gating; they do not perform visual review."""
import hashlib
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from typography_layout import render_elements
from review_gate import initialize, check, write


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        data=json.loads((Path(__file__).resolve().parents[1]/'assets/example-board-wireframe.json').read_text())
        with contextlib.redirect_stdout(io.StringIO()):render_elements(data,self.root)
        (self.root/'generation-prompt.txt').write_text('Test-only prompt; not a real handoff.')
        self.report=initialize(self.root)
    def tearDown(self):self.temp.cleanup()
    def filled_fixture(self):
        r=self.report
        # Explicitly simulated records: exercise validation, not visual inspection.
        for phase in r['rounds']:
            phase['status']='pass'
            for item in phase['checks'].values():
                item.update(status='pass',note='Simulated test fixture observation')
            phase['evidence']=[{'kind':'visual','path':'wireframe-image-input.png','note':'Test fixture only'}]
            if phase['number']==2:phase['evidence'].append({'kind':'measurement','path':'layout-checks.json','note':'Test fixture only'})
            if phase['number']==5:phase['evidence'].append({'kind':'prompt','path':'generation-prompt.txt','note':'Test fixture only'})
        geometry=json.loads((self.root/'layout-checks.json').read_text())
        r['warning_resolutions']={w:'Simulated rationale for fixture only' for w in geometry.get('warnings',[])}
        write(self.root/'qa-review.json',r)
        return r
    def test_legacy_three_rounds_cannot_release(self):
        r=self.filled_fixture();r['rounds']=r['rounds'][:3]
        write(self.root/'qa-review.json',r)
        with self.assertRaisesRegex(ValueError,'five ordered'):check(self.root)

    def test_reference_limit_checked_before_submission(self):
        ref={'path':'wireframe-image-input.png','role':'layout','sha256':hashlib.sha256((self.root/'wireframe-image-input.png').read_bytes()).hexdigest()}
        write(self.root/'generation-inputs.json',{'reference_limit':1,'references':[ref,ref]})
        with self.assertRaisesRegex(ValueError,'reference limit'):initialize(self.root)
    def test_reference_file_change_is_detected(self):
        path=self.root/'atlas.png';path.write_bytes(b'synthetic-reference-fixture')
        ref={'path':'atlas.png','role':'source-atlas','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        write(self.root/'generation-inputs.json',{'reference_limit':5,'references':[ref]});initialize(self.root)
        path.write_bytes(b'changed-synthetic-reference-fixture')
        with self.assertRaisesRegex(ValueError,'reference missing or changed'):check(self.root)
    def test_reference_role_is_required(self):
        ref={'path':'wireframe-image-input.png','role':'','sha256':hashlib.sha256((self.root/'wireframe-image-input.png').read_bytes()).hexdigest()}
        write(self.root/'generation-inputs.json',{'reference_limit':5,'references':[ref]})
        with self.assertRaisesRegex(ValueError,'role missing'):initialize(self.root)

    def test_initial_pending_cannot_release(self):
        with self.assertRaisesRegex(ValueError,'incomplete'):check(self.root)
        self.assertFalse((self.root/'handoff-ready.json').exists())
    def test_record_complete_can_release(self):
        self.filled_fixture()
        self.assertEqual(check(self.root)['state'],'ready_for_handoff')
        self.assertTrue((self.root/'handoff-ready.json').exists())
    def test_version_change_revokes_release(self):
        self.filled_fixture();check(self.root)
        (self.root/'generation-prompt.txt').write_text('Changed version')
        with self.assertRaisesRegex(ValueError,'version changed'):check(self.root)
        self.assertFalse((self.root/'handoff-ready.json').exists())
    def test_unresolved_issue_blocks(self):
        r=self.filled_fixture()
        r['rounds'][1]['issues']=[{'issue':'Headings offset','resolved':False}]
        write(self.root/'qa-review.json',r)
        with self.assertRaisesRegex(ValueError,'unresolved issue'):check(self.root)
    def test_missing_visual_evidence_blocks(self):
        r=self.filled_fixture();r['rounds'][1]['evidence']=r['rounds'][1]['evidence'][1:]
        write(self.root/'qa-review.json',r)
        with self.assertRaisesRegex(ValueError,'required evidence missing'):check(self.root)
    def test_unrelated_evidence_blocks(self):
        r=self.filled_fixture();(self.root/'unrelated.txt').write_text('unrelated')
        r['rounds'][0]['evidence']=[{'kind':'visual','path':'unrelated.txt','note':'not a preview'}]
        write(self.root/'qa-review.json',r)
        with self.assertRaisesRegex(ValueError,'not part of the reviewed version'):check(self.root)
    def test_missing_round_blocks(self):
        r=self.filled_fixture();r['rounds'].pop()
        write(self.root/'qa-review.json',r)
        with self.assertRaisesRegex(ValueError,'five ordered'):check(self.root)
    def test_unresolved_warning_blocks(self):
        # Create an actual English widow independently of the language-specific example.
        data=json.loads((self.root/'layout.json').read_text())
        next(e for e in data['elements'] if e['id']=='body')['text']='Fixture line\nword'
        with contextlib.redirect_stdout(io.StringIO()):render_elements(data,self.root)
        self.report=initialize(self.root)
        r=self.filled_fixture();r['warning_resolutions']={}
        write(self.root/'qa-review.json',r)
        geometry=json.loads((self.root/'layout-checks.json').read_text())
        self.assertTrue(geometry['warnings'])
        with self.assertRaisesRegex(ValueError,'Unresolved renderer warnings'):check(self.root)
    def test_reinitialize_archives_and_clears_release(self):
        self.filled_fixture();check(self.root)
        initialize(self.root)
        self.assertFalse((self.root/'handoff-ready.json').exists())
        self.assertTrue(list((self.root/'qa-history').glob('*.json')))

if __name__=='__main__':unittest.main()
