"""Run with a Pillow-enabled Python; no external services or product assets needed."""
import copy
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from typography_layout import render_elements

class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((Path(__file__).resolve().parents[1]/'assets/example-board-wireframe.json').read_text())
    def render(self,data):
        with tempfile.TemporaryDirectory() as t, contextlib.redirect_stdout(io.StringIO()):
            render_elements(data,Path(t))
            return json.loads((Path(t)/'layout-checks.json').read_text())
    def test_existing_bilingual_layout(self):
        r=self.render(self.data)
        self.assertEqual(len(r['text_blocks']),3)
        self.assertTrue(all(c['measured_delta']==0 for c in r['alignment_checks']))
    def test_reject_invalid_layouts(self):
        cases=[('Text overflow',lambda d:d['elements'][3].update(h=20)),
               ('Outside canvas',lambda d:d['elements'][2].update(x=790)),
               ('Duplicate ID',lambda d:d['elements'][3].update(id='title')),
               ('Unintended overlap',lambda d:d['elements'][3].update(x=400)),
               ('Alignment mismatch',lambda d:d['elements'][4].update(x=49)),
               ('Unbreakable word',lambda d:d['elements'][3].update(text='W'*100))]
        for error,change in cases:
            with self.subTest(error=error):
                d=copy.deepcopy(self.data);change(d)
                with self.assertRaisesRegex(ValueError,error):self.render(d)
    def test_cjk_boundary(self):
        d={'canvas':{'width':400,'height':500},'elements':[{'id':'zh','type':'text','x':20,'y':20,'w':64,'h':450,'font_size':20,'line_height':30,'text':'中文中文，中文（中文）中文。'}]}
        r=self.render(d)
        for line in r['text_blocks'][0]['lines']:
            self.assertFalse(line.startswith(('，','。','）')))
            self.assertFalse(line.endswith('（'))
    def test_fonts_and_first_last_baselines(self):
        cjk=Path('/System/Library/Fonts/Hiragino Sans GB.ttc')
        latin=Path('/System/Library/Fonts/Helvetica.ttc')
        if not cjk.exists() or not latin.exists():self.skipTest('Two known test fonts unavailable')
        d={'canvas':{'width':800,'height':300},'language_profiles':{'zh-CN':{'font_path':str(cjk)},'en':{'font_path':str(latin)}},'elements':[
            {'id':'zh','type':'text','language':'zh-CN','x':40,'y':40,'w':300,'h':120,'font_size':20,'line_height':30,'text':'中文标题\n中文正文'},
            {'id':'en','type':'text','language':'en','x':420,'y':40,'w':300,'h':120,'font_size':20,'line_height':30,'text':'English heading\nEnglish body'}],
            'alignments':[{'axis':'first-baseline','ids':['zh','en'],'tolerance':0},{'axis':'last-baseline','ids':['zh','en'],'tolerance':0}]}
        r=self.render(d)
        self.assertNotEqual(r['text_blocks'][0]['font_path'],r['text_blocks'][1]['font_path'])
        self.assertEqual(r['text_blocks'][0]['last_baseline'],90)
        self.assertEqual(len(r['text_blocks'][0]['ink_bounds']),4)
        d['elements'][1]['text']='One line'
        with self.assertRaisesRegex(ValueError,'Alignment mismatch'):self.render(d)
    def test_cross_region_heading_image_caption_and_gap(self):
        def text(id,x,y):
            return dict(id=id,type='text',x=x,y=y,w=180,h=40,font_size=20,line_height=30,text='Label')
        d={'canvas':{'width':800,'height':600},'elements':[
            text('left-head',40,40),text('right-head',300,56),
            dict(id='left-image',type='image-box',x=40,y=180,w=180,h=200),
            dict(id='right-image',type='image-box',x=300,y=100,w=400,h=260),
            text('left-caption',40,404),text('right-caption',300,384)],
            'alignment_bands':[{'id':'row','heading_ids':['left-head','right-head'],
                'image_ids':['left-image','right-image'],'caption_ids':['left-caption','right-caption'],'tolerance':0}],
            'gap_rules':[{'id':'caption-space','pairs':[['left-image','left-caption'],['right-image','right-caption']],'expected':24,'tolerance':0}]}
        with self.assertRaisesRegex(ValueError,'Alignment mismatch'):self.render(d)
        d['elements'][1]['y']=40
        with self.assertRaisesRegex(ValueError,'Alignment mismatch'):self.render(d)
        d['elements'][2]['y']=160
        with self.assertRaisesRegex(ValueError,'Alignment mismatch'):self.render(d)
        d['elements'][4]['y']=384
        self.assertEqual(self.render(d)['gap_checks'][0]['measured_gaps'],[24,24])
        # Even aligned caption baselines cannot hide inconsistent image-caption gaps.
        d['elements'][4]['y']=d['elements'][5]['y']=388
        with self.assertRaisesRegex(ValueError,'Gap mismatch'):self.render(d)

    def test_horizontal_photo_gutter_drift_rejected(self):
        d={'canvas':{'width':420,'height':200},'elements':[{'id':'a','type':'image-box','x':20,'y':20,'w':100,'h':100},{'id':'b','type':'image-box','x':138,'y':20,'w':100,'h':100},{'id':'c','type':'image-box','x':256,'y':20,'w':100,'h':100}], 'gap_rules':[{'id':'photo-gutter','axis':'horizontal','pairs':[['a','b'],['b','c']],'expected':18,'tolerance':0}]}
        self.assertEqual(self.render(d)['gap_checks'][0]['measured_gaps'],[18,18])
        d['elements'][2]['x']=260
        with self.assertRaisesRegex(ValueError,'Gap mismatch'):self.render(d)

    def test_english_widow_warning(self):
        d={'canvas':{'width':400,'height':300},'elements':[{'id':'en','type':'text','x':20,'y':20,'w':300,'h':100,'font_size':20,'line_height':30,'text':'First line\nword'}]}
        self.assertTrue(self.render(d)['warnings'])

if __name__=='__main__':unittest.main()
