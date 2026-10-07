from importlib import import_module

LANGUAGE_MODULE_NAMES = (
    'eng',
    'ita',
    'spa',
    'por',
    'jpn',
    'zho_hans',
    'zho_hant',
    'kor',
    'hin',
    'fra',
    'ara',
    'rus',
    'deu',
    'tur',
    'ind',
    'vie',
    'pol',
    'ben',
    'tha',
    'fas',
    'urd',
    'ukr',
    'nld',
    'ell',
    'ces',
    'ron'
)

LANGUAGES = {}
for _module_name in LANGUAGE_MODULE_NAMES:
    _module = import_module(f"{__name__}.{_module_name}")
    LANGUAGES[_module.CODE] = _module

def get_language_data(code):
    key = code.value if hasattr(code, "value") else str(code)
    return LANGUAGES[key]
