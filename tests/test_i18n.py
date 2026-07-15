import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from i18n import load, t, set_lang, get_lang

def test_load_zh_cn():
    strings = load('zh_CN')
    assert isinstance(strings, dict)
    assert strings['app.title'] == 'OpenCode Helper'

def test_load_en_us():
    strings = load('en_US')
    assert strings['app.title'] == 'OpenCode Helper'

def test_t_simple_key():
    set_lang('zh_CN')
    result = t('app.title')
    assert result == 'OpenCode Helper'

def test_t_with_format():
    set_lang('zh_CN')
    result = t('detect.node_version', version='20.11.0')
    assert '20.11.0' in result

def test_t_fallback_to_key():
    set_lang('zh_CN')
    result = t('nonexistent.key')
    assert result == 'nonexistent.key'

def test_get_lang_default():
    assert get_lang() == 'zh_CN'

def test_set_lang():
    set_lang('en_US')
    assert get_lang() == 'en_US'
    set_lang('zh_CN')
