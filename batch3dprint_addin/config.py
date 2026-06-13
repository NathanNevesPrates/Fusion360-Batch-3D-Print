import copy
import json
import os

DEFAULT_CONFIG = {
    'language': 'auto',
    'defaults': {
        'parameter_name': '',
        'parameter_mode': 'number',
        'text_format': 'Label {n}',
        'start_value': 1,
        'increment': 1,
        'file_count': 5,
        'export_format': '3mf',
        'unit_type': 'millimeter',
        'refinement': 'medium',
        'custom_refinement': {
            'surface_deviation_cm': 0.01,
            'normal_deviation_deg': 15.0,
            'maximum_edge_length_cm': 0.0,
            'aspect_ratio': 0.0
        },
        'file_base_name': 'File',
        'output_parent_folder': '',
        'one_file_per_body': False
    },
    'limits': {
        'min_file_count': 1,
        'max_file_count': 1000000,
        'warn_if_file_count_above': 100,
        'min_integer_value': -1000000000,
        'max_integer_value': 1000000000
    },
    'behavior': {
        'folder_suffix': '_BatchExport',
        'restore_parameter_after_export': True,
        'avoid_overwriting_files': True,
        'create_unique_output_folder': False,
        'auto_name_from_selection': True,
        'auto_open_output_folder': False,
        'path_separator': 'system'
    }
}


def _deep_merge(base, override):
    result = copy.deepcopy(base)
    if not isinstance(override, dict):
        return result
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(addin_dir):
    path = os.path.join(addin_dir, 'config.json')
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            user_config = json.load(handle)
    except Exception:
        user_config = {}
    return _deep_merge(DEFAULT_CONFIG, user_config)


def get(config, dotted_path, default=None):
    node = config
    for part in dotted_path.split('.'):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node
