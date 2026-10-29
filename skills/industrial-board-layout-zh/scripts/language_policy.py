"""Apply a standalone skill's language defaults before wireframe rendering.

This checks declared language and obvious accidental CJK prose in English
output. It does not infer semantic language, approve copy, or judge typography.
"""
import copy
import json
import re
from pathlib import Path


def load_policy():
    return json.loads((Path(__file__).resolve().parents[1] /
                       'assets/language-policy.json').read_text(encoding='utf-8'))


def normalize_language(value):
    value = str(value).lower().replace('_', '-')
    if value in ('zh', 'zh-cn', 'zh-hans', 'chinese'):
        return 'zh-CN'
    if value == 'en' or value.startswith('en-') or value == 'english':
        return 'en'
    return value


def prepare_layout(data, policy=None):
    """Copy input, resolve language/font defaults, reject mismatched layouts."""
    policy = policy or load_policy()
    primary = policy['primary_language']
    result = copy.deepcopy(data)
    canvas = result['canvas']
    declared = normalize_language(canvas.get('language', primary))
    if declared != primary:
        other = 'industrial-board-layout-en' if primary == 'zh-CN' else 'industrial-board-layout-zh'
        raise ValueError(f'Primary language mismatch: this skill uses {primary}; use {other} for {declared}')
    canvas['language'] = primary
    profiles = result.setdefault('language_profiles', {})
    profile = profiles.setdefault(primary, {})
    font = profile.get('font_path') or canvas.get('font_path')
    if font and not Path(font).is_file():
        raise ValueError(f'Font unavailable: {font}; choose a font available in this environment')
    if not font:
        font = next((p for p in policy['font_candidates'] if Path(p).is_file()), None)
    if not font:
        raise ValueError(f'No available font for {primary}; set canvas.font_path or language_profiles')
    canvas.setdefault('font_path', font)
    profile.setdefault('font_path', font)
    for element in result.get('elements', []):
        if element.get('type') != 'text':
            continue
        ident = element['id']
        language = normalize_language(element.get('language', primary))
        exception = bool(str(element.get('language_exception_note', '')).strip())
        # Short Latin brand/model names are expected in Chinese product boards.
        allowed = (primary, 'en') if primary == 'zh-CN' else (primary,)
        if language not in allowed and not exception:
            raise ValueError(f'{ident}: text language mismatch; document a required proper-name exception or use the other skill')
        if primary == 'en' and re.search(r'[\u3400-\u9fff]', element.get('text', '')) and not exception:
            raise ValueError(f'{ident}: CJK text in English board; supply English copy or document a required proper-name exception')
        element['language'] = language
    text_copy = [e.get('text', '') for e in result.get('elements', []) if e.get('type') == 'text' and e.get('text', '').strip()]
    if primary == 'zh-CN' and text_copy and not any(re.search(r'[\u3400-\u9fff]', text) for text in text_copy):
        raise ValueError('Chinese-primary board has no CJK copy; supply Chinese copy or use industrial-board-layout-en')
    result['language_policy'] = {
        'skill': policy['skill'], 'primary_language': primary,
        'version': policy['version'],
        'limits': 'Language/default-font validation only; inspect wrapping, glyphs and model output separately.'
    }
    return result
