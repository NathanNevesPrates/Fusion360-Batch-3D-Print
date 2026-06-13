import os
import subprocess
import sys
import webbrowser

import adsk.core
import adsk.fusion


def app_ui_design():
    app = adsk.core.Application.get()
    ui = app.userInterface if app else None
    design = adsk.fusion.Design.cast(app.activeProduct) if app else None
    return app, ui, design


def debug_log(text):
    try:
        app = adsk.core.Application.get()
        if app:
            app.log('[Batch3DPrint] {}'.format(str(text)))
    except Exception:
        pass


def fusion_language_locale(app=None):
    app = app or adsk.core.Application.get()
    if not app:
        debug_log('No Fusion app available for language detection; defaulting to en-us.')
        return 'en-us'
    try:
        language = app.preferences.generalPreferences.userLanguage
    except Exception:
        debug_log('Failed to read Fusion userLanguage; defaulting to en-us.')
        return 'en-us'

    enum_mappings = [
        ('EnglishLanguage', 'en-us'),
        ('GermanLanguage', 'de-de'),
        ('FrenchLanguage', 'fr-fr'),
        ('SpanishLanguage', 'es-es'),
        ('PortugueseBrazilianLanguage', 'pt-br')
    ]

    try:
        user_languages = adsk.core.UserLanguages
    except Exception:
        user_languages = None

    if user_languages:
        for attr_name, locale in enum_mappings:
            try:
                enum_value = getattr(user_languages, attr_name)
                if language == enum_value:
                    
                    return locale
            except Exception:
                pass

    language_name = str(language)
    for attr_name, locale in enum_mappings:
        if attr_name in language_name:
            
            return locale

    debug_log('No language mapping matched; defaulting to en-us.')
    return 'en-us'


def show_message(text):
    try:
        _, ui, _ = app_ui_design()
        if ui:
            ui.messageBox(str(text))
    except Exception:
        pass


def compute_design(design):
    try:
        design.computeAll()
    except Exception:
        pass
    try:
        adsk.doEvents()
    except Exception:
        pass
    try:
        app = adsk.core.Application.get()
        if app and app.activeViewport:
            app.activeViewport.refresh()
    except Exception:
        pass


def get_user_parameter_names(design):
    names = []
    if not design:
        return names
    try:
        for parameter in design.userParameters.asArray():
            try:
                names.append(parameter.name)
            except Exception:
                pass
    except Exception:
        pass
    return sorted(set(names), key=lambda value: value.lower())


def entity_token(entity):
    try:
        return entity.entityToken
    except Exception:
        return ''


def resolve_entity_from_token(design, token, fallback):
    if token:
        try:
            found = design.findEntityByToken(token)
            if found and len(found) > 0:
                return found[0]
        except Exception:
            pass
    return fallback


def geometry_display_name(entity):
    for attr in ('name',):
        try:
            value = getattr(entity, attr)
            if value:
                return str(value)
        except Exception:
            pass
    try:
        component = entity.component
        if component and component.name:
            return str(component.name)
    except Exception:
        pass
    try:
        object_type = entity.objectType.split('::')[-1]
        if object_type:
            return object_type
    except Exception:
        pass
    return 'Selection'


def get_input(inputs, input_id):
    try:
        found = inputs.itemById(input_id)
        if found:
            return found
    except Exception:
        pass

    try:
        count = inputs.count
    except Exception:
        count = 0

    for index in range(count):
        try:
            item = inputs.item(index)
        except Exception:
            continue
        try:
            child_inputs = item.children
            if child_inputs:
                found = get_input(child_inputs, input_id)
                if found:
                    return found
        except Exception:
            pass
    return None


def selected_item_name(dropdown):
    try:
        if dropdown and dropdown.selectedItem:
            return dropdown.selectedItem.name
    except Exception:
        pass
    return ''


def bool_value(command_input, default=False):
    try:
        return bool(command_input.value)
    except Exception:
        return default


def open_folder_dialog(initial_directory, title):
    app, ui, _ = app_ui_design()
    if not ui:
        return None
    folder_dialog = ui.createFolderDialog()
    folder_dialog.title = title
    if initial_directory and os.path.isdir(initial_directory):
        try:
            folder_dialog.initialDirectory = initial_directory
        except Exception:
            pass
    result = folder_dialog.showDialog()
    if result == adsk.core.DialogResults.DialogOK:
        return folder_dialog.folder
    return None


def open_folder_in_os(path):
    try:
        if sys.platform.startswith('win'):
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])
        return True
    except Exception:
        try:
            return webbrowser.open('file://' + os.path.abspath(path))
        except Exception:
            return False
