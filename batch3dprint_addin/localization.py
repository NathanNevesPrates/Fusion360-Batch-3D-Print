import json
import os


class Localizer:
    def __init__(self, addin_dir, language='en'):
        self.addin_dir = addin_dir
        self.language = language or 'en'
        self.data = {}
        self._load()

    def _load(self):
        paths = [
            os.path.join(self.addin_dir, 'strings', '{}.json'.format(self.language)),
            os.path.join(self.addin_dir, 'strings', 'en.json')
        ]
        for path in paths:
            try:
                with open(path, 'r', encoding='utf-8') as handle:
                    self.data = json.load(handle)
                return
            except Exception:
                pass
        self.data = {}

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
