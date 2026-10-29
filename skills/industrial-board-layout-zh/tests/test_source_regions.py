"""Synthetic fixtures test region validation, not real product/design judgment."""
import contextlib
import copy
import io
import json
import math
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from source_regions import inspect_sources, write_source_map
from typography_layout import render_elements
from review_gate import initialize, check, write

class SourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        Image.new('RGB',(100,80),'gray').save(self.root/'reference.png')
        self.detail=dict(id='detail',type='image-box',x=20,y=20,w=180,h=140,
            source='reference.png',fit='crop',evidence_status='visible-crop',
            evidence_note='Synthetic rectangle fixture only; no semantic product claim',
            source_region=[.2,.25,.4,.5],target_feature='test area',exclude_features=['outside test area'])
        self.data={'canvas':{'width':400,'height':300},'elements':[self.detail]}
    def tearDown(self):self.tmp.cleanup()
    def test_normalized_region_to_pixels(self):
        r=inspect_sources(self.data,self.root,strict=True)
        self.assertEqual(r['regions'][0]['pixel_bounds'],[20,20,60,60])
    def test_region_errors(self):
        for roi in [[-.1,0,.2,.2],[.8,.8,.3,.3],[0,0,0,.5],[0,0,math.nan,.2],[0,0,True,.2]]:
            with self.subTest(roi=roi):
                d=copy.deepcopy(self.data);d['elements'][0]['source_region']=roi
                with self.assertRaises(ValueError):inspect_sources(d,self.root,strict=True)
    def test_missing_region_or_target_rejected(self):
        for key in ['source_region','target_feature','exclude_features']:
            d=copy.deepcopy(self.data);d['elements'][0].pop(key)
            with self.assertRaises(ValueError):inspect_sources(d,self.root,strict=True)
    def test_missing_product_source_rejected(self):
        d=copy.deepcopy(self.data);d['elements'][0]['source']='unknown.png'
        with self.assertRaisesRegex(ValueError,'source unavailable'):inspect_sources(d,self.root,strict=True)
    def test_unknown_evidence_not_treated_as_verified(self):
        d=copy.deepcopy(self.data);d['elements'][0].pop('evidence_status')
        with self.assertRaisesRegex(ValueError,'evidence status'):inspect_sources(d,self.root,strict=True)
    def test_explicit_placeholder_does_not_create_a_product(self):
        d=copy.deepcopy(self.data);d['elements'][0].update(evidence_status='unsupported-placeholder',source='not provided')
        d['elements'][0].pop('source_region')
        r=inspect_sources(d,self.root,strict=True)
        self.assertFalse(r['regions'])
        self.assertEqual(r['product_evidence'][0]['status'],'unsupported-placeholder')
    def test_map_embeds_unchanged_source_and_roi(self):
        r=inspect_sources(self.data,self.root,strict=True);write_source_map(r,self.root)
        svg=ET.parse(self.root/'source-map.svg')
        self.assertEqual(len(svg.findall('.//{http://www.w3.org/2000/svg}image')),1)
        self.assertIn('data:image/png;base64,',(self.root/'source-map.svg').read_text())
        self.assertEqual(json.loads((self.root/'source-regions.json').read_text())['regions'],r['regions'])
    def render_review_fixture(self):
        with contextlib.redirect_stdout(io.StringIO()):render_elements(self.data,self.root)
        (self.root/'generation-prompt.txt').write_text('Synthetic test; not a real product handoff')
        # Synthetic gate fixture, not real material-placement validation.
        (self.root/'placement-preview.png').write_bytes((self.root/'wireframe-image-input.png').read_bytes())
        r=initialize(self.root)
        for phase in r['rounds']:
            phase['status']='pass'
            for item in phase['checks'].values():item.update(status='pass',note='Simulated fixture record, not actual visual review')
            phase['evidence']=[{'kind':'visual','path':'wireframe-image-input.png','note':'fixture'}]
            if phase['number']==2:phase['evidence'].append({'kind':'measurement','path':'layout-checks.json','note':'fixture'})
            if phase['number']==5:phase['evidence'].append({'kind':'prompt','path':'generation-prompt.txt','note':'fixture'})
            if phase['number']==3:phase['evidence'].append({'kind':'placement','path':'placement-preview.png','note':'Synthetic gate fixture only'})
        return r
    def test_gate_requires_actual_region_map_record(self):
        r=self.render_review_fixture();write(self.root/'qa-review.json',r)
        with self.assertRaisesRegex(ValueError,'required evidence missing'):check(self.root)
        r['rounds'][0]['evidence'].append({'kind':'source-map','path':'source-map.svg','note':'Simulated fixture only'})
        write(self.root/'qa-review.json',r)
        self.assertEqual(check(self.root)['state'],'ready_for_handoff')
    def test_source_photo_cannot_replace_guide_visual_review(self):
        r=self.render_review_fixture()
        r['rounds'][0]['evidence']=[{'kind':'visual','path':'reference.png','note':'Fixture attempts to use source instead of guide'}]
        write(self.root/'qa-review.json',r)
        with self.assertRaisesRegex(ValueError,'current rendered guide'):check(self.root)
    def test_gate_rejects_stale_region_metadata(self):
        self.render_review_fixture()
        p=self.root/'source-regions.json';r=json.loads(p.read_text());r['regions'][0]['target_feature']='different area';write(p,r)
        with self.assertRaisesRegex(ValueError,'metadata is stale'):initialize(self.root)

if __name__=='__main__':unittest.main()
