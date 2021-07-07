# Author-Hajime NAKAZATO
# Description-RPA module of insert-decal. Fusion 360 API doesn't have the function.

# This file is just for unit tests. Run as script to test.

import traceback
import os
import sys
import typing as ty
import adsk.core as ac
import adsk

CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)


# # test
# def run(context):
#     if 'insert_decal_rpa' in sys.modules:
#         import importlib
#         importlib.reload(sys.modules['insert_decal_rpa'])
#     from insert_decal_rpa import _launch_external_process, _call_external_process
#     import time
#     _launch_external_process()
#     time.sleep(1.)
#     args = (1, 2, 3)
#     ret = _call_external_process('echo', args)
#     if args != ret:
#         print('bad')
#     _call_external_process('exit', None)
#     print('run')


import importlib
for i in sys.modules.keys():
    if i.startswith('f360_insert_decal_rpa'):
        importlib.reload(sys.modules[i])
from f360_insert_decal_rpa import start as insert_decal_rpa_start


HANDLER: ty.Union[ac.CustomEventHandler, None] = None
CUSTOM_EVENT: ty.Union[ac.CustomEvent, None] = None


def run(context):
    global CUSTOM_EVENT, HANDLER
    app = ac.Application.get()
    try:
        HANDLER = WaitRpaDoneEventHandler()
        app.unregisterCustomEvent('wait_rpa_done')
        CUSTOM_EVENT = app.registerCustomEvent('wait_rpa_done')
        CUSTOM_EVENT.add(HANDLER)
        insert_decal_rpa_start('wait_rpa_done', 'foo', ac.ViewOrientations.TopViewOrientation, ac.Point3D.create(0., 0., 0.), [])
        adsk.autoTerminate(False)
    except Exception:
        ui = app.userInterface
        ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class WaitRpaDoneEventHandler(ac.CustomEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        global CUSTOM_EVENT, HANDLER
        app = ac.Application.get()
        CUSTOM_EVENT.remove(self)
        app.unregisterCustomEvent('wait_rpa_done')
        HANDLER = None
        CUSTOM_EVENT = None
        print('WaitRpaDone done')
        adsk.terminate()
