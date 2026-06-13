# Batch 3D Print for Autodesk Fusion

Batch 3D Print exports repeated mesh files while changing a Fusion user parameter before each export. It is meant for models that contain a parameter-driven label, serial number, size marker, or similar variation.

## License

This project is available under the MIT license.

## What it exports

The command can export one selected body, occurrence, or root component.

Supported output choices:

- 3MF
- STL Binary
- STL ASCII
- OBJ

STL and OBJ expose a unit selector. 3MF disables the unit selector because Fusion's API exposes STL/OBJ unit settings separately from 3MF export settings.

## Install

Copy the entire `Batch3DPrint` folder into Fusion's AddIns directory.

Windows:

```text
%appdata%\Autodesk\Autodesk Fusion\API\AddIns\Batch3DPrint
```

macOS:

```text
~/Library/Application Support/Autodesk/Autodesk Fusion/API/AddIns/Batch3DPrint
```

Then open Fusion and run:

```text
Utilities > Scripts and Add-Ins > Add-Ins > Batch3DPrint > Run
```

The command appears in the Solid workspace under the ADD-INS panel as **Batch 3D Print**.

## Basic workflow

1. Create a user parameter that drives the thing you want to change.
2. Run **Batch 3D Print**.
3. Select the body, occurrence, or root component to export.
4. Choose the user parameter.
5. Set the starting value, increment, and number of files.
6. Choose the export format and mesh refinement.
7. Choose the output parent folder.
8. Click **Export**.

The default file count is `5` so accidental exports stay small.

Example sequence:

```text
Starting value: 1
Increment: 1
Number of files: 5
File base name: Part
```

creates files like:

```text
Part_1.3mf
Part_2.3mf
Part_3.3mf
Part_4.3mf
Part_5.3mf
```

inside a generated folder named:

```text
Part_BatchExport
```

## Parameter modes

**Number only** writes raw numeric expressions such as `1`, `2`, `3` to the selected user parameter.

**Text label using format** writes text generated from the Text format field. Use `{n}` where the current number should appear, for example:

```text
Label {n}
```

## Configuration

Edit `config.json` to change defaults and behavior. Common settings:

```json
{
  "defaults": {
    "file_count": 5,
    "export_format": "3mf",
    "unit_type": "millimeter",
    "refinement": "medium"
  },
  "behavior": {
    "folder_suffix": "_BatchExport",
    "restore_parameter_after_export": true,
    "avoid_overwriting_files": true,
    "auto_name_from_selection": true,
    "path_separator": "system"
  }
}
```

The generated output folder is based on the editable File base name plus `behavior.folder_suffix`.

After a successful export starts, the add-in remembers the last-used dialog settings in `batch3dprint_state.json`. This generated file is local to the installed add-in and is ignored by Git.

## User-facing text

Edit files in `lang/` to change labels, descriptions, tooltips, notes, and messages.

## Source layout

```text
Batch3DPrint.py                  Fusion entry point
batch3dprint_addin/app.py         Add-in startup/shutdown
batch3dprint_addin/handlers.py    Command event handlers
batch3dprint_addin/ui.py          Dialog construction
batch3dprint_addin/exporter.py    Export and parameter logic
batch3dprint_addin/fusion_helpers.py Fusion API helpers
batch3dprint_addin/config.py      Config loading/defaults
batch3dprint_addin/localization.py Language loading helpers
batch3dprint_addin/naming.py      File/folder naming helpers
config.json                       Editable default behavior
lang/en-us.json                   Editable English user-facing text
```

## Notes

- Existing files are not overwritten when `avoid_overwriting_files` is true; `_001`, `_002`, etc. is appended when needed.
- The selected parameter is restored after export when `restore_parameter_after_export` is true.
- Preview and triangle count are intentionally omitted because every iteration can produce different geometry.
- Batch mode always writes files. It does not send each exported mesh to a print utility.
