# Changelog

## 1.0.0

- Moved the command to Fusion's `Make` panel.
- Added command icon resources and a placeholder tool clip image for the expanded tooltip.
- Expanded the command description and tooltip content, including a GitHub project link.
- Added multilingual support through the `lang/` directory with `en-us`, `pt-br`, `es-es`, `de-de`, and `fr-fr`.
- Renamed language files from `strings/` to `lang/` and changed the English locale file to `en-us.json`.
- Added Fusion UI language sync with locale fallback support.
- Added debug logging for startup and Fusion language detection through Fusion's Text Commands output.
- Changed the default language setting to `auto`.
- Normalized displayed paths and added the configurable `behavior.path_separator` setting.
- Changed the parameter picker to start with a blank `Select a parameter` placeholder instead of defaulting to manual entry.
- Changed the project license to PolyForm Noncommercial 1.0.0.

## 0.2.0

- Removed user-specific defaults and notes.
- Changed default number of files to 5.
- Split the source into modules by responsibility.
- Added a folder picker for the output parent folder.
- Removed the manual folder-name field. The export folder is generated from File base name plus a configurable suffix.
- Auto-fills File base name from the selected body, occurrence, or component while keeping the field editable.
- Added editable labels/tooltips/messages in `lang/en-us.json`.
- Added defaults and behavior settings in `config.json`.
- Added 3MF, STL Binary, STL ASCII, and OBJ export choices.
- Added unit selection for STL/OBJ and disabled units for 3MF.
- Added Low, Medium, High, and Custom mesh refinement settings.

## 0.1.0

- Initial batch export add-in.
