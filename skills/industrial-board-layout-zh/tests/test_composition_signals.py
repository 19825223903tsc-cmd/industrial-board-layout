"""Geometry invariants only, not simulated aesthetic validation."""
import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from composition_signals import union_area,signals,horizontal_neighbors
class SignalsTests(unittest.TestCase):
 def test_neighbors_cover_tall_hero_and_stacked_right_images(self):
  e=[{'type':'image-box','id':'hero','x':0,'y':0,'w':100,'h':300},{'type':'image-box','id':'upper','x':136,'y':0,'w':80,'h':100},{'type':'image-box','id':'lower','x':136,'y':160,'w':80,'h':140}]
  pairs=horizontal_neighbors(e);self.assertEqual({(a['left_id'],a['right_id']) for a in pairs},{('hero','upper'),('hero','lower')});self.assertEqual([a['gap_px'] for a in pairs],[36,36])
 def test_neighbors_find_unequal_gutters(self):
  e=[{'type':'image-box','id':str(i),'x':x,'y':0,'w':100,'h':100} for i,x in enumerate([0,126,268])];self.assertEqual([p['gap_px'] for p in horizontal_neighbors(e)],[26,42])
 def test_union_does_not_double_count_overlap(self):self.assertEqual(union_area([[0,0,10,10],[5,0,15,10]]),150)
 def test_union_ignores_empty_clipped_rectangles(self):self.assertEqual(union_area([[0,20,10,10],[0,0,2,3]]),6)
 def test_density_differs_and_does_not_issue_aesthetic_pass(self):
  d={'canvas':{'width':100,'height':100},'typography':{},'elements':[{'id':'body','type':'text'}]};c={'text_blocks':[{'id':'body','ink_bounds':[0,0,50,20]}]}
  r=signals(d,c,Path('.'));self.assertIsNone(r['aesthetic_verdict']);self.assertEqual(r['quarter_coverage'][0]['frame_and_ink_bbox_coverage'],.4);self.assertEqual(r['quarter_coverage'][3]['frame_and_ink_bbox_coverage'],0);self.assertEqual(r['full_width_empty_strips'][0]['height_px'],80)
 def test_missing_ink_measurement_is_not_silently_scored(self):
  with self.assertRaisesRegex(ValueError,'ink missing'):signals({'canvas':{'width':100,'height':100},'elements':[{'id':'absent','type':'text'}]}, {'text_blocks':[]},Path('.'))
 def test_physical_aspect_mismatch_is_reported(self):
  d={'canvas':{'width':100,'height':100,'physical_width_mm':297,'physical_height_mm':420},'typography':{},'elements':[]};r=signals(d,{'text_blocks':[]},Path('.'));self.assertFalse(r['physical']['aspect_ratio_consistent'])
if __name__=='__main__':unittest.main()
