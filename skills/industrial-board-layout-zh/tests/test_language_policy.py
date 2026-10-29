import copy
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from language_policy import prepare_layout


class LanguagePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # Policy selection is deterministic here; rendering tests check real fonts.
        self.font = Path(self.tmp.name) / 'test-font'
        self.font.write_bytes(b'font-candidate')
        self.data = {'canvas': {'width': 600, 'height': 400},
                     'elements': [{'id': 'body', 'type': 'text', 'text': 'Visible form'}]}

    def tearDown(self):
        self.tmp.cleanup()

    def policy(self, lang):
        return {'skill': 'test', 'version': '14', 'primary_language': lang,
                'font_candidates': [str(self.font)]}

    def test_defaults_are_distinct_and_input_is_not_mutated(self):
        for lang in ('zh-CN', 'en'):
            data = copy.deepcopy(self.data)
            if lang == 'zh-CN':data['elements'][0]['text'] = '产品形态'
            result = prepare_layout(data, self.policy(lang))
            self.assertEqual(result['canvas']['language'], lang)
            self.assertEqual(result['elements'][0]['language'], lang)
            self.assertEqual(result['canvas']['font_path'], str(self.font))
        self.assertNotIn('language', self.data['canvas'])

    def test_wrong_primary_language_rejected_both_ways(self):
        for primary, other in [('en', 'zh-CN'), ('zh-CN', 'en')]:
            data = copy.deepcopy(self.data)
            data['canvas']['language'] = other
            with self.assertRaisesRegex(ValueError, 'Primary language mismatch'):
                prepare_layout(data, self.policy(primary))

    def test_english_rejects_unlabelled_cjk_copy(self):
        data = copy.deepcopy(self.data)
        data['elements'][0]['text'] = '产品形态研究'
        with self.assertRaisesRegex(ValueError, 'CJK text'):
            prepare_layout(data, self.policy('en'))

    def test_chinese_can_preserve_english_model_names(self):
        data = copy.deepcopy(self.data)
        data['elements'][0].update(language='en', text='OP-1 field')
        data['elements'].append({'id': 'heading', 'type': 'text', 'text': '产品形态'})
        self.assertEqual(prepare_layout(data, self.policy('zh-CN'))['elements'][0]['text'], 'OP-1 field')

    def test_chinese_rejects_an_entirely_english_board(self):
        with self.assertRaisesRegex(ValueError, 'no CJK copy'):
            prepare_layout(self.data, self.policy('zh-CN'))

    def test_required_proper_name_exception_is_explicit(self):
        data = copy.deepcopy(self.data)
        data['elements'][0].update(language='zh-CN', text='品牌名')
        with self.assertRaisesRegex(ValueError, 'language mismatch'):
            prepare_layout(data, self.policy('en'))
        data['elements'][0]['language_exception_note'] = 'User requires the original registered brand spelling.'
        result = prepare_layout(data, self.policy('en'))
        self.assertEqual(result['elements'][0]['language'], 'zh-CN')

    def test_missing_font_is_actionable_and_not_silent_fallback(self):
        data = copy.deepcopy(self.data)
        data['canvas']['font_path'] = str(Path(self.tmp.name) / 'missing.ttf')
        with self.assertRaisesRegex(ValueError, 'Font unavailable'):
            prepare_layout(data, self.policy('en'))

    def test_regional_english_alias_is_normalized(self):
        data = copy.deepcopy(self.data)
        data['canvas']['language'] = 'en-GB'
        self.assertEqual(prepare_layout(data, self.policy('en'))['canvas']['language'], 'en')


if __name__ == '__main__':
    unittest.main()
