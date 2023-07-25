# Author-Hajime NAKAZATO
# Description-RPA module of insert-decal. Fusion 360 API doesn't have the function.

# This file is just for unit tests. Run as script to test.

import traceback
import sys
import pathlib
import typing as ty
import tempfile
import adsk.core as ac
import adsk.fusion as af
import adsk

CURRENT_DIR = pathlib.Path(__file__).parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))
ap = CURRENT_DIR / 'app-packages'
if str(ap) not in sys.path:
    sys.path.append(str(ap))

from PIL import Image

# F360 Python doesn't reload modules. It is too bad when debugging.
import importlib
for i in sys.modules.keys():
    if i.startswith('f360_insert_decal_rpa'):
        importlib.reload(sys.modules[i])

from f360_insert_decal_rpa import start as insert_decal_rpa_start
from f360_insert_decal_rpa import InsertDecalParameter


WAIT_RPA_DONE_ID = 'wait_rpa_done'
ERROR_ID = 'rpa_error'
WAIT_HANDLER: ty.Union[ac.CustomEventHandler, None] = None
WAIT_EVENT: ty.Union[ac.CustomEvent, None] = None
ERROR_HANDLER: ty.Union[ac.CustomEventHandler, None] = None
ERROR_EVENT: ty.Union[ac.CustomEvent, None] = None
DOC: ty.Union[ac.Document, None] = None


TEST_PARAMS = [
    {'attributes': ('foo', 'bar', 'baz')},
    {'opacity': 50},
    {'x_distance': 0.1},
    {'y_distance': 0.1},
    {'z_angle': 0.1},
    {'scale_x': 1.4},
    {'scale_y': 1.4},
    {'scale_plane_xy': 2.4},
    {'h_flip': True},
    {'v_flip': True},
    {'chain_faces': False, 'scale_plane_xy': 2.4},
]


def run(context):
    global WAIT_EVENT, WAIT_HANDLER, ERROR_EVENT, ERROR_HANDLER, DOC
    app: ac.Application = ac.Application.get()
    try:
        ui = app.userInterface
        ui.messageBox("This is unit test of f360_insert_decal_rpa.\nDon't touch the mouse or keyboard until the next message.", 'f360_insert_decal_rpa')  # noqa: E501
        DOC = app.documents.add(ac.DocumentTypes.FusionDesignDocumentType)
        root_comp: af.Component = app.activeProduct.rootComponent
        trans = ac.Matrix3D.create()
        src_occ = root_comp.occurrences.addNewComponent(trans)
        src_comp = src_occ.component
        src_comp.name = 'Source Component'
        sketch = src_comp.sketches.add(src_comp.xYConstructionPlane)
        sketch.sketchCurves.sketchLines.addTwoPointRectangle(
            ac.Point3D.create(-1., -1., 0.), ac.Point3D.create(1., 1., 0.), )
        ext_in = src_comp.features.extrudeFeatures.createInput(
            sketch.profiles.item(0), af.FeatureOperations.NewBodyFeatureOperation)
        distance = ac.ValueInput.createByReal(0.2)
        ext_in.setDistanceExtent(False, distance)
        _ = src_comp.features.extrudeFeatures.add(ext_in)
        acc_occ = root_comp.occurrences.addNewComponent(trans)
        acc_occ.component.name = 'Accommodate Component'

        params: ty.List[InsertDecalParameter] = []
        cd = pathlib.Path(__file__).parent
        for i, p in enumerate(TEST_PARAMS):
            dif = cd / 'test_data/decal_image' / f'{i % 10}.png'
            idp = InsertDecalParameter(src_occ, acc_occ, str(i), dif, **p)
            params.append(idp)

        WAIT_HANDLER = WaitRpaDoneEventHandler()
        ERROR_HANDLER = ErrorEventHandler()
        app.unregisterCustomEvent(WAIT_RPA_DONE_ID)
        app.unregisterCustomEvent(ERROR_ID)
        WAIT_EVENT = app.registerCustomEvent(WAIT_RPA_DONE_ID)
        ERROR_EVENT = app.registerCustomEvent(ERROR_ID)
        WAIT_EVENT.add(WAIT_HANDLER)
        ERROR_EVENT.add(ERROR_HANDLER)
        insert_decal_rpa_start(WAIT_RPA_DONE_ID, ERROR_ID, ac.ViewOrientations.TopViewOrientation, ac.Point3D.create(0., 0., 0.), params, True)
        adsk.autoTerminate(False)

    except Exception:
        ui = app.userInterface
        ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def cleanup_handler(app: ac.Application):
    global WAIT_EVENT, WAIT_HANDLER, ERROR_EVENT, ERROR_HANDLER
    WAIT_EVENT.remove(WAIT_HANDLER)
    ERROR_EVENT.remove(ERROR_HANDLER)
    app.unregisterCustomEvent(WAIT_RPA_DONE_ID)
    app.unregisterCustomEvent(ERROR_ID)
    WAIT_HANDLER = None
    ERROR_HANDLER = None
    WAIT_EVENT = None
    ERROR_EVENT = None


class ErrorEventHandler(ac.CustomEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args: ac.CustomEventArgs):
        app = ac.Application.get()
        app.userInterface.messageBox(f'f360_insert_decal_rpa unit test failed.\n{args.additionalInfo}', 'f360_insert_decal_rpa')  # noqa: E501
        cleanup_handler(app)
        adsk.terminate()


class WaitRpaDoneEventHandler(ac.CustomEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        app = ac.Application.get()
        root_comp: af.Component = app.activeProduct.rootComponent

        for o in root_comp.occurrences:
            if o.component.name == 'Source Component':
                src_occ = o
            o.isLightBulbOn = False
        src_occ.isLightBulbOn = True
        camera: ac.Camera = app.activeViewport.camera
        camera.viewOrientation = ac.ViewOrientations.IsoTopLeftViewOrientation
        camera.isSmoothTransition = False
        app.activeViewport.camera = camera
        camera = app.activeViewport.camera
        camera.isFitView = True
        app.activeViewport.camera = camera

        cleanup_handler(app)

        for o in root_comp.occurrences:
            if o.component.name == 'Accommodate Component':
                acc_occ = o
            o.isLightBulbOn = False
        acc_occ.isLightBulbOn = True
        for o in acc_occ.component.occurrences:
            o.isLightBulbOn = False
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            ui = app.userInterface
            for o in acc_occ.component.occurrences:
                o.isLightBulbOn = True
                app.activeViewport.saveAsImageFile(str(t / f'{o.component.name}.png'), 200, 200)
                o.isLightBulbOn = False
            ui.messageBox('Compare test result with test oracle by your eyes.\nLeft is oracle and right is result.\nComputer is not good enough at this job yet :-)', 'Insert Decal RPA')  # noqa: E501
            # In detail: F360's window size affects test results subtly. I tried to find a good way to compare results with oracles
            # like feature value (SIFT etc.), but useless.
            for o in acc_occ.component.occurrences:
                gen = Image.open(str(t / f'{o.component.name}.png'))
                oracle = Image.open(str(CURRENT_DIR / f'test_data/oracle/{o.component.name}.png'))
                c = Image.new('RGB', (gen.width + oracle.width, max(gen.height, oracle.height)))
                c.paste(oracle, (0, 0))
                c.paste(gen, (oracle.width, 0))
                c.show()
        
        DOC.close(False)
        adsk.terminate()
