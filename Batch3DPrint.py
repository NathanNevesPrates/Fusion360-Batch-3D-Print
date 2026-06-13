# Fusion 360 add-in entry point.
# The implementation lives in batch3dprint_addin/ to keep responsibilities separated.

import os
import sys
import traceback

ADDIN_DIR = os.path.dirname(os.path.abspath(__file__))
if ADDIN_DIR not in sys.path:
    sys.path.insert(0, ADDIN_DIR)


def _message(text):
    try:
        import adsk.core
        app = adsk.core.Application.get()
        if app and app.userInterface:
            app.userInterface.messageBox(str(text))
    except Exception:
        pass


def run(context):
    try:
        from batch3dprint_addin import app
        app.run(context, ADDIN_DIR)
    except Exception:
        _message('Batch 3D Print failed to start:\n{}'.format(traceback.format_exc()))


def stop(context):
    try:
        from batch3dprint_addin import app
        app.stop(context)
    except Exception:
        _message('Batch 3D Print failed to stop:\n{}'.format(traceback.format_exc()))
