import json
import os


def _deep_merge(base, override):
    result = dict(base) if isinstance(base, dict) else {}
    if not isinstance(override, dict):
        return result
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Localizer:
    def __init__(self, addin_dir, language='en-us'):
        self.addin_dir = addin_dir
        self.language = language or 'en-us'
        self.data = {}
        self._load()

    def _load(self):
        language = self.language.lower().replace('_', '-')
        aliases = {
            'en': 'en-us',
            'pt': 'pt-br',
            'es': 'es-es'
        }
        language = aliases.get(language, language)
        paths = [
            os.path.join(self.addin_dir, 'lang', 'en-us.json'),
            os.path.join(self.addin_dir, 'lang', '{}.json'.format(language))
        ]
        for path in paths:
            try:
                with open(path, 'r', encoding='utf-8') as handle:
                    self.data = _deep_merge(self.data, json.load(handle))
            except Exception:
                pass

    def node(self, dotted_path, default=None):
        node = self.data
        for part in dotted_path.split('.'):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def t(self, dotted_path, default=''):
        value = self.node(dotted_path, default)
        return value if isinstance(value, str) else default

    def choices(self, dotted_path):
        value = self.node(dotted_path, {})
        if isinstance(value, dict):
            return [(key, str(label)) for key, label in value.items()]
        return []

    def choice_label(self, dotted_path, key, default=None):
        value = self.node(dotted_path, {})
        if isinstance(value, dict) and key in value:
            return str(value[key])
        return default if default is not None else str(key)

    def choice_key(self, dotted_path, label, default=None):
        value = self.node(dotted_path, {})
        if isinstance(value, dict):
            for key, candidate in value.items():
                if str(candidate) == str(label):
                    return key
        return default
