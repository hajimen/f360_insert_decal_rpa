# Author-Hajime NAKAZATO
# Description-RPA module of "Insert -> Decal -> Insert from my computer" operation. Fusion 360 API doesn't have the function.

# This file is just for testing. Run as a script to test.

import traceback
import sys
import pathlib
import typing as ty
import tempfile
import time
import adsk.core as ac
import adsk.fusion as af
import adsk

CURRENT_DIR = pathlib.Path(__file__).parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))
ap = CURRENT_DIR / 'app-packages'
if str(ap) not in sys.path:
    sys.path.append(str(ap))
del ap

# F360's Python doesn't reload modules. It is too bad while debugging.
import importlib
for i in list(sys.modules.keys()):
    if i.startswith('f360_insert_decal_rpa'):
        importlib.reload(sys.modules[i])

from f360_insert_decal_rpa import start as insert_decal_rpa_start
from f360_insert_decal_rpa import InsertDecalParameter, FALLBACK_MODE


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
    {'pointer_offset_x': 0.2, 'pointer_offset_y': 0.3, 'pointer_offset_z': 0.1},
]


def run(context):
    global WAIT_EVENT, WAIT_HANDLER, ERROR_EVENT, ERROR_HANDLER, DOC
    app: ac.Application = ac.Application.get()
    try:
        ui = app.userInterface
        ui.messageBox("This is a regression test of f360_insert_decal_rpa.\nDon't touch the mouse or keyboard until the next dialog box is shown.")  # noqa: E501

        # Prepare test fixture.
        DOC = app.documents.add(ac.DocumentTypes.FusionDesignDocumentType)
        root_comp: af.Component = app.activeProduct.rootComponent
        trans = ac.Matrix3D.create()
        src1_occ = root_comp.occurrences.addNewComponent(trans)
        src1_occ.component.name = 'Source Component Level 1'

        src_block_occ = src1_occ.component.occurrences.addNewComponent(trans)
        src_block_occ = src_block_occ.createForAssemblyContext(src1_occ)
        src_block_occ.component.name = 'Block Component Src'
        block_sketch = src_block_occ.component.sketches.add(src_block_occ.component.xYConstructionPlane)
        block_sketch.sketchCurves.sketchLines.addTwoPointRectangle(
            ac.Point3D.create(-1., -2., 0.), ac.Point3D.create(2., 1., 0.), )
        block_ext_in = src_block_occ.component.features.extrudeFeatures.createInput(
            block_sketch.profiles.item(0), af.FeatureOperations.NewBodyFeatureOperation)
        block_ext_in.setDistanceExtent(False, ac.ValueInput.createByReal(0.3))
        _ = src_block_occ.component.features.extrudeFeatures.add(block_ext_in)

        src2_occ = src1_occ.component.occurrences.addNewComponent(trans)
        src2_occ = src2_occ.createForAssemblyContext(src1_occ)
        src2_comp = src2_occ.component
        src2_occ.component.name = 'Source Component Level 2'
        src2_comp.sketches.add(src2_comp.xYConstructionPlane)
        sketch = src2_comp.sketches.add(src2_comp.xYConstructionPlane)
        sketch.sketchCurves.sketchLines.addTwoPointRectangle(
            ac.Point3D.create(-1., -1., 0.), ac.Point3D.create(1., 1., 0.), )
        ext_in = src2_comp.features.extrudeFeatures.createInput(
            sketch.profiles.item(0), af.FeatureOperations.NewBodyFeatureOperation)
        distance = ac.ValueInput.createByReal(0.2)
        ext_in.setDistanceExtent(False, distance)
        _ = src2_comp.features.extrudeFeatures.add(ext_in)
        acc1_occ = root_comp.occurrences.addNewComponent(trans)
        acc1_occ.component.name = 'Accommodate Component Level 1'

        acc_block_occ = acc1_occ.component.occurrences.addNewComponent(trans)
        acc_block_occ = acc_block_occ.createForAssemblyContext(acc1_occ)
        acc_block_occ.component.name = 'Block Component Acc'
        acc_block_sketch = acc_block_occ.component.sketches.add(acc_block_occ.component.xYConstructionPlane)
        acc_block_sketch.sketchCurves.sketchLines.addTwoPointRectangle(
            ac.Point3D.create(-2., -1., 0.), ac.Point3D.create(1., 2., 0.), )
        acc_block_ext_in = acc_block_occ.component.features.extrudeFeatures.createInput(
            acc_block_sketch.profiles.item(0), af.FeatureOperations.NewBodyFeatureOperation)
        acc_block_ext_in.setDistanceExtent(False, ac.ValueInput.createByReal(0.3))
        _ = acc_block_occ.component.features.extrudeFeatures.add(acc_block_ext_in)

        acc2_occ = acc1_occ.component.occurrences.addNewComponent(trans)
        acc2_occ = acc2_occ.createForAssemblyContext(acc1_occ)
        acc2_occ.component.name = 'Accommodate Component Level 2'

        params: ty.List[InsertDecalParameter] = []
        for i, p in enumerate(TEST_PARAMS):
            dif = CURRENT_DIR / 'test_data/decal_image' / f'{i % 10}.png'
            idp = InsertDecalParameter(src2_occ, acc2_occ, str(i), dif, **p)
            params.append(idp)

        # Prepare F360's custom events which will be fired when RPA finished / failed.
        WAIT_HANDLER = WaitRpaDoneEventHandler()
        ERROR_HANDLER = ErrorEventHandler()
        app.unregisterCustomEvent(WAIT_RPA_DONE_ID)  # In case of crash without cleanup while debugging.
        app.unregisterCustomEvent(ERROR_ID)  # In case of crash without cleanup while debugging.
        WAIT_EVENT = app.registerCustomEvent(WAIT_RPA_DONE_ID)
        ERROR_EVENT = app.registerCustomEvent(ERROR_ID)
        WAIT_EVENT.add(WAIT_HANDLER)
        ERROR_EVENT.add(ERROR_HANDLER)

        insert_decal_rpa_start(WAIT_RPA_DONE_ID, ERROR_ID, ac.ViewOrientations.TopViewOrientation, ac.Point3D.create(0., 0., 0.), params, True)

        # Without this, F360's custom event handlers never be called.
        adsk.autoTerminate(False)

    except Exception:
        msg = traceback.format_exc()
        print(msg)
        if ui is not None:
            ui.messageBox('Failed in run():\n{}'.format(msg))


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
        cleanup_handler(app)
        app.userInterface.messageBox(f'f360_insert_decal_rpa test failed.\n{args.additionalInfo}')  # noqa: E501
        adsk.terminate()


def do_many_events():
    for _ in range(100):
        adsk.doEvents()
        time.sleep(0.01)


class WaitRpaDoneEventHandler(ac.CustomEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        app = ac.Application.get()
        try:
            cleanup_handler(app)

            ui = app.userInterface

            # Adjust camera.
            root_comp: af.Component = app.activeProduct.rootComponent
            for o in root_comp.occurrences:
                if o.component.name == 'Source Component Level 1':
                    src1_occ = o
                o.isLightBulbOn = False
            src1_occ.isLightBulbOn = True
            for o in src1_occ.component.occurrences:
                if o.component.name == 'Source Component Level 2':
                    src2_occ = o
                o.isLightBulbOn = False
            src2_occ.isLightBulbOn = True

            do_many_events()
            camera: ac.Camera = app.activeViewport.camera
            camera.viewOrientation = ac.ViewOrientations.TopViewOrientation
            camera.isFitView = True
            camera.isSmoothTransition = False
            app.activeViewport.camera = camera
            do_many_events()

            camera: ac.Camera = app.activeViewport.camera
            camera.isFitView = True
            camera.isSmoothTransition = False
            app.activeViewport.camera = camera
            do_many_events()

            # Adjust light bulbs to capture viewport images of each results.
            for o in root_comp.occurrences:
                if o.component.name == 'Accommodate Component Level 1':
                    acc1_occ = o
                o.isLightBulbOn = False
            acc1_occ.isLightBulbOn = True
            for o in acc1_occ.component.occurrences:
                if o.component.name == 'Accommodate Component Level 2':
                    acc2_occ = o
                o.isLightBulbOn = False
            if len(acc2_occ.component.occurrences) != len(TEST_PARAMS):
                raise Exception("The number of accommodated components doesn't match.")
            acc2_occ.isLightBulbOn = True
            for o in acc2_occ.component.occurrences:
                o.isLightBulbOn = False

            if FALLBACK_MODE:
                ui.messageBox('The f360_insert_decal_rpa regression test has done.')
            else:
                from PIL import Image
                # Capture viewport images of each results and compare them with oracles.
                with tempfile.TemporaryDirectory() as tmp:
                    t = pathlib.Path(tmp)
                    for o in acc2_occ.component.occurrences:
                        o.isLightBulbOn = True
                        app.activeViewport.saveAsImageFile(str(t / f'{o.component.name}.png'), 200, 200)
                        o.isLightBulbOn = False
                    msg = 'Compare test result with test oracles by your eyes.\nLeft is oracle and right is result.\nComputer is not good enough at this job yet :-)'  # noqa: E501
                    ui.messageBox(msg)
                    # In detail:
                    # F360's window size affects test results subtly. I tried to find a good way to compare results with oracles
                    # like feature value (SIFT etc.), but in vain.
                    for o in acc2_occ.component.occurrences:
                        gen = Image.open(str(t / f'{o.component.name}.png'))
                        # gen.save(str(CURRENT_DIR / f'test_data/oracle/{o.component.name}.png'))  # Make oracle
                        oracle = Image.open(str(CURRENT_DIR / f'test_data/oracle/{o.component.name}.png'))
                        c = Image.new('RGB', (gen.width + oracle.width, max(gen.height, oracle.height)))
                        c.paste(oracle, (0, 0))
                        c.paste(gen, (oracle.width, 0))
                        c.show()

            DOC.close(False)
        except Exception:
            if ui is not None:
                ui.messageBox('Failed in WaitRpaDoneEventHandler.notify():\n{}'.format(traceback.format_exc()))
        adsk.terminate()
