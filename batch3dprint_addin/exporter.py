import math

import adsk.core
import adsk.fusion

from .fusion_helpers import compute_design

FORMAT_EXTENSIONS = {
    '3mf': '.3mf',
    'stl_binary': '.stl',
    'stl_ascii': '.stl',
    'obj': '.obj'
}

DISTANCE_UNITS = {
    'millimeter': 'MillimeterDistanceUnits',
    'centimeter': 'CentimeterDistanceUnits',
    'meter': 'MeterDistanceUnits',
    'inch': 'InchDistanceUnits',
    'foot': 'FootDistanceUnits'
}

MESH_REFINEMENTS = {
    'low': 'MeshRefinementLow',
    'medium': 'MeshRefinementMedium',
    'high': 'MeshRefinementHigh'
}


def extension_for_format(format_key):
    return FORMAT_EXTENSIONS.get(format_key, '.3mf')


def text_literal_for_fusion(text):
    return "'{}'".format(str(text).replace("'", "\\'"))


def set_parameter_value(parameter, number, mode_key, text_format):
    if mode_key == 'text':
        label = str(text_format or '{n}').replace('{n}', str(number))
        try:
            parameter.textValue = label
        except Exception:
            parameter.expression = text_literal_for_fusion(label)
        return label

    parameter.expression = str(number)
    return str(number)


def refinement_enum(refinement_key):
    name = MESH_REFINEMENTS.get(refinement_key, MESH_REFINEMENTS['medium'])
    try:
        return getattr(adsk.fusion.MeshRefinementSettings, name)
    except Exception:
        return None


def distance_unit_enum(unit_key):
    name = DISTANCE_UNITS.get(unit_key, DISTANCE_UNITS['millimeter'])
    try:
        return getattr(adsk.fusion.DistanceUnits, name)
    except Exception:
        return None


def _try_set(obj, attr, value):
    try:
        setattr(obj, attr, value)
        return True
    except Exception:
        return False


def _apply_refinement(options, refinement_key, custom_values):
    if refinement_key == 'custom':
        surface = float(custom_values.get('surface_deviation_cm', 0.0) or 0.0)
        normal = float(custom_values.get('normal_deviation_rad', 0.0) or 0.0)
        edge = float(custom_values.get('maximum_edge_length_cm', 0.0) or 0.0)
        aspect = float(custom_values.get('aspect_ratio', 0.0) or 0.0)

        if surface > 0:
            _try_set(options, 'surfaceDeviation', surface)
        if normal > 0:
            _try_set(options, 'normalDeviation', normal)
        if edge > 0:
            _try_set(options, 'maximumEdgeLength', edge)
        if aspect > 0:
            _try_set(options, 'aspectRatio', aspect)
        return

    value = refinement_enum(refinement_key)
    if value is not None:
        _try_set(options, 'meshRefinement', value)


def create_export_options(export_manager, geometry, file_path, settings):
    format_key = settings.get('format_key', '3mf')

    if format_key == '3mf':
        options = export_manager.createC3MFExportOptions(geometry, file_path)
    elif format_key == 'obj':
        options = export_manager.createOBJExportOptions(geometry, file_path)
    else:
        options = export_manager.createSTLExportOptions(geometry, file_path)
        _try_set(options, 'isBinaryFormat', format_key == 'stl_binary')

    _try_set(options, 'sendToPrintUtility', False)
    _try_set(options, 'isOneFilePerBody', bool(settings.get('one_file_per_body', False)))

    if format_key in ('stl_binary', 'stl_ascii', 'obj'):
        unit_value = distance_unit_enum(settings.get('unit_key', 'millimeter'))
        if unit_value is not None:
            _try_set(options, 'unitType', unit_value)

    _apply_refinement(
        options,
        settings.get('refinement_key', 'medium'),
        settings.get('custom_refinement', {})
    )
    return options


def export_one(design, geometry, file_path, settings):
    options = create_export_options(design.exportManager, geometry, file_path, settings)
    return design.exportManager.execute(options)


def restore_parameter(parameter, original_expression, design):
    parameter.expression = original_expression
    compute_design(design)


def degrees_to_radians(value):
    return float(value) * math.pi / 180.0
