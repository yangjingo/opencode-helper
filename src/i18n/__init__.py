"""Internationalization — loads JSON string tables, supports formatting."""
import json
import os

_strings: dict = {}
_lang: str = 'zh_CN'

def load(lang: str) -> dict:
    path = os.path.join(os.path.dirname(__file__), f'{lang}.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def set_lang(lang: str):
    global _lang, _strings
    _lang = lang
    _strings = load(lang)

def get_lang() -> str:
    return _lang

def t(key: str, **kwargs) -> str:
    global _strings
    if not _strings:
        set_lang(_lang)
    value = _strings.get(key, key)
    if kwargs:
        return value.format(**kwargs)
    return value
