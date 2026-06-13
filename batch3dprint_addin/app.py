import traceback

import adsk.core

from .constants import CMD_DESCRIPTION, CMD_ID, CMD_NAME, PANEL_ID, WORKSPACE_ID
from .config import get, load_config
from .handlers import BatchCommandCreatedHandler
from .fusion_helpers import show_message
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
        localizer = Localizer(addin_dir, get(config, 'language', 'en'))
        command_name = localizer.t('command.name', CMD_NAME)
        command_description = localizer.t('command.description', CMD_DESCRIPTION)

        command_definition = _ui.commandDefinitions.itemById(CMD_ID)
        if not command_definition:
            command_definition = _ui.commandDefinitions.addButtonDefinition(CMD_ID, command_name, command_description)

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
