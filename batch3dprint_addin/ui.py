import math
import os

import adsk.core

from . import constants as ids
from .config import get
from .naming import build_output_folder, default_desktop, display_path, expand_folder


CHOICE_PATHS = {
    ids.PARAM_MODE: 'choices.parameter_modes',
    ids.EXPORT_FORMAT: 'choices.export_formats',
    ids.UNIT_TYPE: 'choices.unit_types',
    ids.REFINEMENT: 'choices.refinement'
}


def set_tooltip(command_input, localizer, input_id):
    try:
        tooltip = localizer.t('tooltips.{}.base'.format(input_id), '')
        description = localizer.t('tooltips.{}.description'.format(input_id), '')
        if tooltip:
            command_input.tooltip = tooltip
        if description:
            command_input.tooltipDescription = description
    except Exception:
        pass
    return command_input


def add_group(inputs, input_id, label_key, localizer, expanded=True):
    group = inputs.addGroupCommandInput(input_id, localizer.t(label_key, input_id))
    try:
        group.isExpanded = expanded
    except Exception:
        pass
    return group.children


def add_choices(dropdown, localizer, choices_path, default_key):
    choices = localizer.choices(choices_path)
    if not choices:
        return
    keys = [key for key, _ in choices]
    selected_key = default_key if default_key in keys else keys[0]
    for key, label in choices:
        dropdown.listItems.add(label, key == selected_key, '')


def default_parent_folder(config):
    configured = get(config, 'defaults.output_parent_folder', '')
    return expand_folder(configured or default_desktop())


def build_inputs(cmd, config, localizer, parameter_names):
    cmd.okButtonText = localizer.t('buttons.export', 'Export')
    try:
        cmd.isExecutedWhenPreEmpted = False
    except Exception:
        pass

    inputs = cmd.commandInputs
    defaults = get(config, 'defaults', {})
    limits = get(config, 'limits', {})

    geometry_inputs = add_group(inputs, 'geometryGroup', 'groups.geometry', localizer, True)
    geometry = geometry_inputs.addSelectionInput(
        ids.GEOMETRY,
        localizer.t('labels.{}'.format(ids.GEOMETRY), 'Geometry to export'),
        localizer.t('prompts.{}'.format(ids.GEOMETRY), 'Select geometry to export.')
    )
    for filter_name in ids.GEOMETRY_FILTERS:
        geometry.addSelectionFilter(filter_name)
    geometry.setSelectionLimits(1, 1)
    set_tooltip(geometry, localizer, ids.GEOMETRY)

    sequence_inputs = add_group(inputs, 'sequenceGroup', 'groups.sequence', localizer, True)
    param_dropdown = sequence_inputs.addDropDownCommandInput(
        ids.PARAM_SELECT,
        localizer.t('labels.{}'.format(ids.PARAM_SELECT), 'User parameter'),
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    default_parameter = str(defaults.get('parameter_name', '') or '')
    selected_parameter = default_parameter if default_parameter in parameter_names else ''
    placeholder_label = localizer.choice_label('choices.parameter_select', ids.SELECT_PARAMETER_KEY, 'Select a parameter')
    param_dropdown.listItems.add(placeholder_label, not bool(selected_parameter), '')
    for name in parameter_names:
        selected = bool(selected_parameter and name == selected_parameter)
        param_dropdown.listItems.add(name, selected, '')
    manual_label = localizer.choice_label('choices.parameter_select', ids.MANUAL_PARAMETER_KEY, 'Type name manually')
    param_dropdown.listItems.add(manual_label, False, '')
    set_tooltip(param_dropdown, localizer, ids.PARAM_SELECT)

    manual_parameter = sequence_inputs.addStringValueInput(
        ids.PARAM_NAME,
        localizer.t('labels.{}'.format(ids.PARAM_NAME), 'Parameter name'),
        selected_parameter
    )
    set_tooltip(manual_parameter, localizer, ids.PARAM_NAME)

    mode = sequence_inputs.addDropDownCommandInput(
        ids.PARAM_MODE,
        localizer.t('labels.{}'.format(ids.PARAM_MODE), 'Parameter value mode'),
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    add_choices(mode, localizer, CHOICE_PATHS[ids.PARAM_MODE], defaults.get('parameter_mode', 'number'))
    set_tooltip(mode, localizer, ids.PARAM_MODE)

    text_format = sequence_inputs.addStringValueInput(
        ids.TEXT_FORMAT,
        localizer.t('labels.{}'.format(ids.TEXT_FORMAT), 'Text format'),
        str(defaults.get('text_format', 'Label {n}'))
    )
    set_tooltip(text_format, localizer, ids.TEXT_FORMAT)

    min_int = int(limits.get('min_integer_value', -1000000000))
    max_int = int(limits.get('max_integer_value', 1000000000))
    sequence_inputs.addIntegerSpinnerCommandInput(
        ids.START_VALUE,
        localizer.t('labels.{}'.format(ids.START_VALUE), 'Starting value'),
        min_int,
        max_int,
        1,
        int(defaults.get('start_value', 1))
    )
    set_tooltip(sequence_inputs.itemById(ids.START_VALUE), localizer, ids.START_VALUE)

    sequence_inputs.addIntegerSpinnerCommandInput(
        ids.INCREMENT,
        localizer.t('labels.{}'.format(ids.INCREMENT), 'Increment'),
        min_int,
        max_int,
        1,
        int(defaults.get('increment', 1))
    )
    set_tooltip(sequence_inputs.itemById(ids.INCREMENT), localizer, ids.INCREMENT)

    sequence_inputs.addIntegerSpinnerCommandInput(
        ids.FILE_COUNT,
        localizer.t('labels.{}'.format(ids.FILE_COUNT), 'Number of files'),
        int(limits.get('min_file_count', 1)),
        int(limits.get('max_file_count', 1000000)),
        1,
        int(defaults.get('file_count', 5))
    )
    set_tooltip(sequence_inputs.itemById(ids.FILE_COUNT), localizer, ids.FILE_COUNT)

    export_inputs = add_group(inputs, 'exportGroup', 'groups.export', localizer, True)
    export_format = export_inputs.addDropDownCommandInput(
        ids.EXPORT_FORMAT,
        localizer.t('labels.{}'.format(ids.EXPORT_FORMAT), 'Format'),
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    add_choices(export_format, localizer, CHOICE_PATHS[ids.EXPORT_FORMAT], defaults.get('export_format', '3mf'))
    set_tooltip(export_format, localizer, ids.EXPORT_FORMAT)

    unit_type = export_inputs.addDropDownCommandInput(
        ids.UNIT_TYPE,
        localizer.t('labels.{}'.format(ids.UNIT_TYPE), 'Units'),
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    add_choices(unit_type, localizer, CHOICE_PATHS[ids.UNIT_TYPE], defaults.get('unit_type', 'millimeter'))
    set_tooltip(unit_type, localizer, ids.UNIT_TYPE)

    refinement = export_inputs.addDropDownCommandInput(
        ids.REFINEMENT,
        localizer.t('labels.{}'.format(ids.REFINEMENT), 'Refinement'),
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    add_choices(refinement, localizer, CHOICE_PATHS[ids.REFINEMENT], defaults.get('refinement', 'medium'))
    set_tooltip(refinement, localizer, ids.REFINEMENT)

    custom = defaults.get('custom_refinement', {}) or {}
    surface = export_inputs.addFloatSpinnerCommandInput(
        ids.SURFACE_DEVIATION,
        localizer.t('labels.{}'.format(ids.SURFACE_DEVIATION), 'Surface deviation'),
        'cm',
        0.0,
        1000000.0,
        0.001,
        float(custom.get('surface_deviation_cm', 0.01) or 0.01)
    )
    set_tooltip(surface, localizer, ids.SURFACE_DEVIATION)

    normal_degrees = float(custom.get('normal_deviation_deg', 15.0) or 15.0)
    normal = export_inputs.addFloatSpinnerCommandInput(
        ids.NORMAL_DEVIATION,
        localizer.t('labels.{}'.format(ids.NORMAL_DEVIATION), 'Normal deviation'),
        'deg',
        0.0,
        math.pi,
        1.0,
        normal_degrees * math.pi / 180.0
    )
    set_tooltip(normal, localizer, ids.NORMAL_DEVIATION)

    edge = export_inputs.addFloatSpinnerCommandInput(
        ids.MAX_EDGE_LENGTH,
        localizer.t('labels.{}'.format(ids.MAX_EDGE_LENGTH), 'Maximum edge length'),
        'cm',
        0.0,
        1000000.0,
        0.01,
        float(custom.get('maximum_edge_length_cm', 0.0) or 0.0)
    )
    set_tooltip(edge, localizer, ids.MAX_EDGE_LENGTH)

    aspect = export_inputs.addFloatSpinnerCommandInput(
        ids.ASPECT_RATIO,
        localizer.t('labels.{}'.format(ids.ASPECT_RATIO), 'Aspect ratio'),
        '',
        0.0,
        1000000.0,
        1.0,
        float(custom.get('aspect_ratio', 0.0) or 0.0)
    )
    set_tooltip(aspect, localizer, ids.ASPECT_RATIO)

    one_file = export_inputs.addBoolValueInput(
        ids.ONE_FILE_PER_BODY,
        localizer.t('labels.{}'.format(ids.ONE_FILE_PER_BODY), 'One file per body'),
        True,
        '',
        bool(defaults.get('one_file_per_body', False))
    )
    set_tooltip(one_file, localizer, ids.ONE_FILE_PER_BODY)

    output_inputs = add_group(inputs, 'outputGroup', 'groups.output', localizer, True)
    file_base = output_inputs.addStringValueInput(
        ids.FILE_BASE,
        localizer.t('labels.{}'.format(ids.FILE_BASE), 'File base name'),
        str(defaults.get('file_base_name', 'BatchExport') or 'BatchExport')
    )
    set_tooltip(file_base, localizer, ids.FILE_BASE)

    parent_folder = default_parent_folder(config)
    folder = output_inputs.addStringValueInput(
        ids.OUTPUT_PARENT_FOLDER,
        localizer.t('labels.{}'.format(ids.OUTPUT_PARENT_FOLDER), 'Output parent folder'),
        display_path(parent_folder, config)
    )
    try:
        folder.isEnabled = False
    except Exception:
        pass
    set_tooltip(folder, localizer, ids.OUTPUT_PARENT_FOLDER)

    browse = output_inputs.addBoolValueInput(
        ids.BROWSE_FOLDER,
        localizer.t('labels.{}'.format(ids.BROWSE_FOLDER), 'Choose folder...'),
        False,
        '',
        False
    )
    set_tooltip(browse, localizer, ids.BROWSE_FOLDER)

    preview_path = build_output_folder(parent_folder, file_base.value, get(config, 'behavior.folder_suffix', '_BatchExport'))
    preview = output_inputs.addStringValueInput(
        ids.OUTPUT_FOLDER_PREVIEW,
        localizer.t('labels.{}'.format(ids.OUTPUT_FOLDER_PREVIEW), 'Generated export folder'),
        display_path(preview_path, config)
    )
    try:
        preview.isEnabled = False
    except Exception:
        pass
    set_tooltip(preview, localizer, ids.OUTPUT_FOLDER_PREVIEW)

    notes_text = localizer.t('notes.command', '')
    if notes_text:
        notes = inputs.addTextBoxCommandInput(
            ids.NOTES,
            localizer.t('labels.{}'.format(ids.NOTES), 'Notes'),
            notes_text,
            5,
            True
        )
        set_tooltip(notes, localizer, ids.NOTES)
