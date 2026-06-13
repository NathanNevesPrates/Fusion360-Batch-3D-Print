import math
import os
import traceback

import adsk.core
import adsk.fusion

from . import constants as ids
from .config import get, load_config, load_state, save_state
from .exporter import export_one, extension_for_format, restore_parameter, set_parameter_value
from .fusion_helpers import (
    app_ui_design,
    bool_value,
    compute_design,
    debug_log,
    entity_token,
    geometry_display_name,
    get_input,
    get_user_parameter_names,
    fusion_language_locale,
    open_folder_dialog,
    open_folder_in_os,
    resolve_entity_from_token,
    selected_item_name,
    show_message,
)
from .localization import Localizer
from .naming import build_output_folder, display_path, expand_folder, sanitize_name, unique_folder_path, unique_path
from .ui import CHOICE_PATHS, build_inputs


def selected_choice_key(inputs, input_id, localizer, default_key):
    dropdown = get_input(inputs, input_id)
    label = selected_item_name(dropdown)
    return localizer.choice_key(CHOICE_PATHS[input_id], label, default_key)


def manual_parameter_label(localizer):
    return localizer.choice_label('choices.parameter_select', ids.MANUAL_PARAMETER_KEY, 'Type name manually')


def placeholder_parameter_label(localizer):
    return localizer.choice_label('choices.parameter_select', ids.SELECT_PARAMETER_KEY, 'Select a parameter')


def selected_parameter_name(inputs, localizer):
    dropdown = get_input(inputs, ids.PARAM_SELECT)
    manual = get_input(inputs, ids.PARAM_NAME)
    selected = selected_item_name(dropdown)
    if selected == placeholder_parameter_label(localizer):
        return ''
    if selected == manual_parameter_label(localizer):
        try:
            return manual.value.strip()
        except Exception:
            return ''
    return selected.strip() if selected else ''


def input_value(inputs, input_id, default=None):
    command_input = get_input(inputs, input_id)
    try:
        return command_input.value
    except Exception:
        return default


def set_visible(command_input, visible):
    try:
        command_input.isVisible = bool(visible)
    except Exception:
        pass


def set_enabled(command_input, enabled):
    try:
        command_input.isEnabled = bool(enabled)
    except Exception:
        pass


def update_preview(inputs, config):
    file_base = get_input(inputs, ids.FILE_BASE)
    parent = get_input(inputs, ids.OUTPUT_PARENT_FOLDER)
    preview = get_input(inputs, ids.OUTPUT_FOLDER_PREVIEW)
    if not file_base or not parent or not preview:
        return
    folder = build_output_folder(parent.value, file_base.value, get(config, 'behavior.folder_suffix', '_BatchExport'))
    try:
        preview.value = display_path(folder, config)
    except Exception:
        pass


def update_visibility(inputs, config, localizer):
    mode_key = selected_choice_key(inputs, ids.PARAM_MODE, localizer, get(config, 'defaults.parameter_mode', 'number'))
    format_key = selected_choice_key(inputs, ids.EXPORT_FORMAT, localizer, get(config, 'defaults.export_format', '3mf'))
    refinement_key = selected_choice_key(inputs, ids.REFINEMENT, localizer, get(config, 'defaults.refinement', 'medium'))

    set_visible(get_input(inputs, ids.TEXT_FORMAT), mode_key == 'text')

    manual_selected = selected_item_name(get_input(inputs, ids.PARAM_SELECT)) == manual_parameter_label(localizer)
    set_visible(get_input(inputs, ids.PARAM_NAME), manual_selected)

    units = get_input(inputs, ids.UNIT_TYPE)
    set_enabled(units, format_key != '3mf')

    custom_visible = refinement_key == 'custom'
    for input_id in (ids.SURFACE_DEVIATION, ids.NORMAL_DEVIATION, ids.MAX_EDGE_LENGTH, ids.ASPECT_RATIO):
        set_visible(get_input(inputs, input_id), custom_visible)

    update_preview(inputs, config)


class BatchCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self, handlers, addin_dir):
        super().__init__()
        self.handlers = handlers
        self.addin_dir = addin_dir

    def notify(self, args):
        try:
            event_args = adsk.core.CommandCreatedEventArgs.cast(args)
            command = event_args.command
            config = load_config(self.addin_dir)
            app, _, design = app_ui_design()
            locale = get(config, 'language', 'auto')
            
            if str(locale or 'auto').lower() == 'auto':
                locale = fusion_language_locale(app)
            debug_log('Resolved command locale: {}'.format(locale))
            localizer = Localizer(self.addin_dir, locale)
            parameter_names = get_user_parameter_names(design)

            build_inputs(command, config, localizer, parameter_names)
            update_visibility(command.commandInputs, config, localizer)

            execute_handler = BatchCommandExecuteHandler(config, localizer, self.addin_dir)
            command.execute.add(execute_handler)
            self.handlers.append(execute_handler)

            validate_handler = BatchValidateInputsHandler(config, localizer)
            command.validateInputs.add(validate_handler)
            self.handlers.append(validate_handler)

            input_changed_handler = BatchInputChangedHandler(config, localizer)
            command.inputChanged.add(input_changed_handler)
            self.handlers.append(input_changed_handler)

            selection_handler = BatchSelectionHandler(config, localizer, input_changed_handler, command)
            command.select.add(selection_handler)
            self.handlers.append(selection_handler)

        except Exception:
            show_message('Batch 3D Print command creation failed:\n{}'.format(traceback.format_exc()))


class BatchInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self, config, localizer):
        super().__init__()
        self.config = config
        self.localizer = localizer
        self.auto_file_base = bool(get(config, 'behavior.auto_name_from_selection', True))
        self.last_auto_file_base = str(get(config, 'defaults.file_base_name', 'BatchExport') or 'BatchExport')

    def notify(self, args):
        try:
            event_args = adsk.core.InputChangedEventArgs.cast(args)
            inputs = event_args.inputs
            changed_input = event_args.input
            changed_id = changed_input.id if changed_input else ''

            if changed_id == ids.FILE_BASE:
                file_base = get_input(inputs, ids.FILE_BASE)
                if file_base and file_base.value != self.last_auto_file_base:
                    self.auto_file_base = False

            if changed_id == ids.GEOMETRY:
                self._maybe_update_file_base(inputs)

            if changed_id == ids.BROWSE_FOLDER:
                self._browse_for_folder(inputs, changed_input)

            update_visibility(inputs, self.config, self.localizer)
        except Exception:
            pass

    def _maybe_update_file_base(self, inputs):
        if not self.auto_file_base:
            return
        geometry = get_input(inputs, ids.GEOMETRY)
        file_base = get_input(inputs, ids.FILE_BASE)
        if not geometry or not file_base or geometry.selectionCount != 1:
            return
        try:
            entity = geometry.selection(0).entity
            self.update_file_base_from_entity(inputs, entity)
        except Exception:
            pass

    def update_file_base_from_entity(self, inputs, entity):
        if not self.auto_file_base:
            return
        file_base = get_input(inputs, ids.FILE_BASE)
        if not file_base or not entity:
            return
        name = sanitize_name(geometry_display_name(entity), 'Selection')
        self.last_auto_file_base = name
        file_base.value = name
        update_preview(inputs, self.config)

    def _browse_for_folder(self, inputs, changed_input):
        try:
            if not bool_value(changed_input, False):
                return
            folder_input = get_input(inputs, ids.OUTPUT_PARENT_FOLDER)
            initial = folder_input.value if folder_input else ''
            title = self.localizer.t('dialog.folder_title', 'Choose output folder')
            folder = open_folder_dialog(expand_folder(initial), title)
            if folder and folder_input:
                folder_input.value = display_path(folder, self.config)
            try:
                changed_input.value = False
            except Exception:
                pass
        except Exception:
            try:
                changed_input.value = False
            except Exception:
                pass


class BatchSelectionHandler(adsk.core.SelectionEventHandler):
    def __init__(self, config, localizer, input_changed_handler, command):
        super().__init__()
        self.config = config
        self.localizer = localizer
        self.input_changed_handler = input_changed_handler
        self.command = command

    def notify(self, args):
        try:
            event_args = adsk.core.SelectionEventArgs.cast(args)
            active_input = event_args.activeInput
            if not active_input or active_input.id != ids.GEOMETRY:
                return
            selection = event_args.selection
            entity = selection.entity if selection else None
            self.input_changed_handler.update_file_base_from_entity(self.command.commandInputs, entity)
        except Exception:
            pass


class BatchValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    def __init__(self, config, localizer):
        super().__init__()
        self.config = config
        self.localizer = localizer

    def notify(self, args):
        try:
            event_args = adsk.core.ValidateInputsEventArgs.cast(args)
            inputs = event_args.inputs
            event_args.areInputsValid = self._are_inputs_valid(inputs)
        except Exception:
            try:
                event_args.areInputsValid = False
            except Exception:
                pass

    def _are_inputs_valid(self, inputs):
        geometry = get_input(inputs, ids.GEOMETRY)
        if not geometry or geometry.selectionCount != 1:
            return False

        if not selected_parameter_name(inputs, self.localizer):
            return False

        parent = get_input(inputs, ids.OUTPUT_PARENT_FOLDER)
        if not parent or not str(parent.value or '').strip():
            return False

        file_base = get_input(inputs, ids.FILE_BASE)
        if not file_base or not str(file_base.value or '').strip():
            return False

        file_count = get_input(inputs, ids.FILE_COUNT)
        if not file_count or int(file_count.value) < 1:
            return False

        refinement_key = selected_choice_key(inputs, ids.REFINEMENT, self.localizer, get(self.config, 'defaults.refinement', 'medium'))
        if refinement_key == 'custom':
            for input_id in (ids.SURFACE_DEVIATION, ids.NORMAL_DEVIATION, ids.MAX_EDGE_LENGTH, ids.ASPECT_RATIO):
                command_input = get_input(inputs, input_id)
                try:
                    if not command_input.isValidExpression:
                        return False
                except Exception:
                    pass

        return True


class BatchCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self, config, localizer, addin_dir):
        super().__init__()
        self.config = config
        self.localizer = localizer
        self.addin_dir = addin_dir

    def notify(self, args):
        try:
            event_args = adsk.core.CommandEventArgs.cast(args)
            inputs = event_args.command.commandInputs
            app, ui, design = app_ui_design()
            if not design:
                show_message(self.localizer.t('messages.no_design', 'Open a Fusion design before running this command.'))
                return

            geometry_input = get_input(inputs, ids.GEOMETRY)
            geometry = geometry_input.selection(0).entity
            geometry_token = entity_token(geometry)

            parameter_name = selected_parameter_name(inputs, self.localizer)
            parameter = design.userParameters.itemByName(parameter_name)
            if not parameter:
                show_message(self.localizer.t('messages.parameter_missing', 'No user parameter named "{name}" was found.').format(name=parameter_name))
                return

            settings = self._read_export_settings(inputs)
            file_base = sanitize_name(input_value(inputs, ids.FILE_BASE, 'BatchExport'), 'BatchExport')
            parent_folder = expand_folder(input_value(inputs, ids.OUTPUT_PARENT_FOLDER, ''))
            output_folder = build_output_folder(parent_folder, file_base, get(self.config, 'behavior.folder_suffix', '_BatchExport'))
            file_count = int(input_value(inputs, ids.FILE_COUNT, 1))
            start_value = int(input_value(inputs, ids.START_VALUE, 1))
            increment = int(input_value(inputs, ids.INCREMENT, 1))

            if not self._confirm_large_batch(ui, file_count):
                return

            self._save_last_used(inputs, parameter_name, parent_folder)

            if bool(get(self.config, 'behavior.create_unique_output_folder', False)):
                output_folder = unique_folder_path(output_folder)
            os.makedirs(output_folder, exist_ok=True)

            original_expression = parameter.expression
            exported = []
            failed = []
            cancelled = False

            progress = ui.createProgressDialog()
            try:
                progress.isBackgroundTranslucent = False
            except Exception:
                pass
            progress.cancelButtonText = self.localizer.t('buttons.cancel', 'Cancel')
            progress.show(
                self.localizer.t('titles.progress', 'Batch 3D Print'),
                self.localizer.t('messages.progress', 'Exporting %v of %m files...'),
                0,
                file_count,
                1
            )

            try:
                for index in range(file_count):
                    if progress.wasCancelled:
                        cancelled = True
                        break

                    number = start_value + (index * increment)
                    set_parameter_value(
                        parameter,
                        number,
                        settings['parameter_mode_key'],
                        settings['text_format']
                    )
                    compute_design(design)

                    current_geometry = resolve_entity_from_token(design, geometry_token, geometry)
                    file_stem = sanitize_name('{}_{}'.format(file_base, number), 'export_{}'.format(index + 1))
                    extension = extension_for_format(settings['format_key'])
                    file_path = os.path.join(output_folder, file_stem + extension)
                    if bool(get(self.config, 'behavior.avoid_overwriting_files', True)):
                        file_path = unique_path(file_path)

                    try:
                        ok = export_one(design, current_geometry, file_path, settings)
                        if ok:
                            exported.append(file_path)
                        else:
                            failed.append(display_path(file_path, self.config))
                    except Exception as export_error:
                        failed.append('{} ({})'.format(display_path(file_path, self.config), export_error))

                    progress.progressValue = index + 1
                    adsk.doEvents()
            finally:
                try:
                    progress.hide()
                except Exception:
                    pass
                if bool(get(self.config, 'behavior.restore_parameter_after_export', True)):
                    try:
                        restore_parameter(parameter, original_expression, design)
                    except Exception:
                        pass

            if bool(get(self.config, 'behavior.auto_open_output_folder', False)) and exported:
                open_folder_in_os(output_folder)

            self._show_summary(output_folder, exported, failed, cancelled)
        except Exception:
            show_message('Batch 3D Print failed:\n{}'.format(traceback.format_exc()))

    def _save_last_used(self, inputs, parameter_name, parent_folder):
        try:
            state = load_state(self.addin_dir)
            state['last_used'] = {
                'parameter_name': str(parameter_name or ''),
                'parameter_mode': selected_choice_key(inputs, ids.PARAM_MODE, self.localizer, get(self.config, 'defaults.parameter_mode', 'number')),
                'start_value': int(input_value(inputs, ids.START_VALUE, 1)),
                'increment': int(input_value(inputs, ids.INCREMENT, 1)),
                'file_count': int(input_value(inputs, ids.FILE_COUNT, 1)),
                'export_format': selected_choice_key(inputs, ids.EXPORT_FORMAT, self.localizer, get(self.config, 'defaults.export_format', '3mf')),
                'unit_type': selected_choice_key(inputs, ids.UNIT_TYPE, self.localizer, get(self.config, 'defaults.unit_type', 'millimeter')),
                'one_file_per_body': bool_value(get_input(inputs, ids.ONE_FILE_PER_BODY), False),
                'refinement': selected_choice_key(inputs, ids.REFINEMENT, self.localizer, get(self.config, 'defaults.refinement', 'medium')),
                'custom_refinement': {
                    'surface_deviation_cm': float(input_value(inputs, ids.SURFACE_DEVIATION, 0.0) or 0.0),
                    'normal_deviation_deg': float(input_value(inputs, ids.NORMAL_DEVIATION, 0.0) or 0.0) * 180.0 / math.pi,
                    'maximum_edge_length_cm': float(input_value(inputs, ids.MAX_EDGE_LENGTH, 0.0) or 0.0),
                    'aspect_ratio': float(input_value(inputs, ids.ASPECT_RATIO, 0.0) or 0.0)
                },
                'output_parent_folder': expand_folder(parent_folder)
            }
            if save_state(self.addin_dir, state):
                debug_log('Saved last-used command settings.')
        except Exception:
            debug_log('Failed to save last-used command settings.')

    def _read_export_settings(self, inputs):
        custom = {
            'surface_deviation_cm': float(input_value(inputs, ids.SURFACE_DEVIATION, 0.0) or 0.0),
            'normal_deviation_rad': float(input_value(inputs, ids.NORMAL_DEVIATION, 0.0) or 0.0),
            'maximum_edge_length_cm': float(input_value(inputs, ids.MAX_EDGE_LENGTH, 0.0) or 0.0),
            'aspect_ratio': float(input_value(inputs, ids.ASPECT_RATIO, 0.0) or 0.0)
        }
        return {
            'parameter_mode_key': selected_choice_key(inputs, ids.PARAM_MODE, self.localizer, get(self.config, 'defaults.parameter_mode', 'number')),
            'text_format': str(input_value(inputs, ids.TEXT_FORMAT, '{n}') or '{n}'),
            'format_key': selected_choice_key(inputs, ids.EXPORT_FORMAT, self.localizer, get(self.config, 'defaults.export_format', '3mf')),
            'unit_key': selected_choice_key(inputs, ids.UNIT_TYPE, self.localizer, get(self.config, 'defaults.unit_type', 'millimeter')),
            'refinement_key': selected_choice_key(inputs, ids.REFINEMENT, self.localizer, get(self.config, 'defaults.refinement', 'medium')),
            'custom_refinement': custom,
            'one_file_per_body': bool_value(get_input(inputs, ids.ONE_FILE_PER_BODY), False)
        }

    def _confirm_large_batch(self, ui, file_count):
        threshold = int(get(self.config, 'limits.warn_if_file_count_above', 0) or 0)
        if threshold <= 0 or file_count <= threshold:
            return True
        try:
            message = self.localizer.t(
                'messages.large_batch_warning',
                'You are about to export {count} files. Continue?'
            ).format(count=file_count, threshold=threshold)
            result = ui.messageBox(
                message,
                self.localizer.t('titles.progress', 'Batch 3D Print'),
                adsk.core.MessageBoxButtonTypes.YesNoButtonType,
                adsk.core.MessageBoxIconTypes.WarningIconType
            )
            return result == adsk.core.DialogResults.DialogYes
        except Exception:
            return True

    def _show_summary(self, output_folder, exported, failed, cancelled):
        message = self.localizer.t('messages.summary', 'Export folder:\n{folder}\n\nExported: {exported}').format(
            folder=display_path(output_folder, self.config),
            exported=len(exported)
        )
        if cancelled:
            message += '\n' + self.localizer.t('messages.cancelled', 'Cancelled before completion.')
        if failed:
            preview = '\n'.join(failed[:10])
            if len(failed) > 10:
                preview += '\n...'
            message += '\n\n' + self.localizer.t('messages.failed', 'Failed: {failed}\n{details}').format(
                failed=len(failed),
                details=preview
            )
        show_message(message)
