import os
import traceback

import adsk.core

from .constants import CMD_DESCRIPTION, CMD_ID, CMD_NAME, PANEL_ID, WORKSPACE_ID
from .config import get, load_config
from .fusion_helpers import debug_log, fusion_language_locale, show_message
from .handlers import BatchCommandCreatedHandler
from .localization import Localizer

_app = None
_ui = None
_handlers = []


def run(context, addin_dir):
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface

        config = load_config(addin_dir)
        locale = get(config, 'language', 'auto')
        if str(locale or 'auto').lower() == 'auto':
            locale = fusion_language_locale(_app)
        debug_log('Resolved startup locale: {}'.format(locale))
        
        localizer = Localizer(addin_dir, locale)
        command_name = localizer.t('command.name', CMD_NAME)
        command_description = localizer.t('command.description', CMD_DESCRIPTION)
        command_tooltip_description = localizer.t('command.tooltip_description', '')
        resource_dir = os.path.join(addin_dir, 'resources')
        toolclip_path = os.path.join(resource_dir, 'toolclip.svg')

        command_definition = _ui.commandDefinitions.itemById(CMD_ID)
        if not command_definition:
            command_definition = _ui.commandDefinitions.addButtonDefinition(
                CMD_ID,
                command_name,
                command_description,
                resource_dir
            )

        try:
            command_definition.tooltip = command_description
        except Exception:
            pass

        try:
            if command_tooltip_description:
                command_definition.tooltipDescription = command_tooltip_description
        except Exception:
            pass

        try:
            if os.path.isfile(toolclip_path):
                command_definition.toolClipFilename = toolclip_path
        except Exception:
            pass

        created_handler = BatchCommandCreatedHandler(_handlers, addin_dir)
        command_definition.commandCreated.add(created_handler)
        _handlers.append(created_handler)

        panel = _target_panel(_ui)
        if panel and not panel.controls.itemById(CMD_ID):
            control = panel.controls.addCommand(command_definition)
            try:
                control.isPromoted = False
            except Exception:
                pass
    except Exception:
        show_message('Batch 3D Print failed to start:\n{}'.format(traceback.format_exc()))


def stop(context):
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface if app else None
        if not ui:
            return

        panel = _target_panel(ui)
        if panel:
            control = panel.controls.itemById(CMD_ID)
            if control:
                control.deleteMe()

        command_definition = ui.commandDefinitions.itemById(CMD_ID)
        if command_definition:
            command_definition.deleteMe()

        _handlers.clear()
    except Exception:
        show_message('Batch 3D Print failed to stop:\n{}'.format(traceback.format_exc()))


def _target_panel(ui):
    panel = None
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if workspace:
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
    if not panel:
        panel = ui.allToolbarPanels.itemById(PANEL_ID)
    return panel
