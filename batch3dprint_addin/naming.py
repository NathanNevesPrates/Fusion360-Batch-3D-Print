import os
import re

_INVALID_NAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1F]+')
_SPACE_RE = re.compile(r'\s+')


def sanitize_name(value, fallback='export'):
    text = str(value or '').strip()
    text = _INVALID_NAME_RE.sub('_', text)
    text = _SPACE_RE.sub('_', text)
    text = text.strip(' ._')
    return text or fallback


def unique_path(path):
    if not os.path.exists(path):
        return path
    root, ext = os.path.splitext(path)
    for index in range(1, 10000):
        candidate = '{}_{:03d}{}'.format(root, index, ext)
        if not os.path.exists(candidate):
            return candidate
    return path


def unique_folder_path(path):
    if not os.path.exists(path):
        return path
    for index in range(1, 10000):
        candidate = '{}_{:03d}'.format(path, index)
        if not os.path.exists(candidate):
            return candidate
    return path


def default_desktop():
    return os.path.expanduser('~/Desktop')


def expand_folder(path):
    text = str(path or '').strip()
    if not text:
        text = default_desktop()
    return os.path.normpath(os.path.expanduser(os.path.expandvars(text)))


def display_path(path, config=None):
    text = os.path.normpath(str(path or ''))
    behavior = config.get('behavior', {}) if isinstance(config, dict) else {}
    separator = str(behavior.get('path_separator', 'system') or 'system').lower()
    if separator in ('forward', 'slash', '/'):
        return text.replace('\\', '/')
    if separator in ('backward', 'backslash', '\\'):
        return text.replace('/', '\\')
    return text.replace('/', os.sep).replace('\\', os.sep)


def batch_folder_name(file_base, suffix):
    base = sanitize_name(file_base, 'BatchExport')
    suffix_text = str(suffix or '_BatchExport')
    return sanitize_name('{}{}'.format(base, suffix_text), 'BatchExport')


def build_output_folder(parent_folder, file_base, suffix):
    return os.path.normpath(os.path.join(expand_folder(parent_folder), batch_folder_name(file_base, suffix)))
