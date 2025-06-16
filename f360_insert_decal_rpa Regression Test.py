# Author-Hajime NAKAZATO
# Description-Backward compatible module for old RPA module. Fusion 360 API didn't have Decal function before June 2025.

# This file is just for testing. Run as a script to test.

import traceback
import sys
import pathlib
import typing as ty
import time
import tempfile
import adsk
import adsk.core as ac
import adsk.fusion as af

CURRENT_DIR = pathlib.Path(__file__).parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

# F360's Python doesn't reload modules. It is too bad while debugging.
import importlib
for i in list(sys.modules.keys()):
    if i.startswith('f360_insert_decal_rpa'):
        importlib.reload(sys.modules[i])

from f360_insert_decal_rpa import start_batch
from f360_insert_decal_rpa import InsertDecalParameter


# Global list to keep all event handlers in scope.
# This is only needed with Python.
HANDLERS = []

JOIN = False
GEN_IMG_PATH: pathlib.Path
ORACLE_IMG_PATH: pathlib.Path


TEST_PARAMS = [
    {'attributes': ('foo', 'bar', 'baz')},
    {'opacity': 50},
    {'x_distance': 0.1},
    {'y_distance': 0.1},
    {'z_angle': 0.1},
    {'scale_x': 1.4},
    {'scale_y': 1.4},
    {'scale_plane_xy': 2.4},
    {'chain_faces': False, 'scale_plane_xy': 2.4},
    {'pointer_offset_x': 0.2, 'pointer_offset_y': 0.3, 'pointer_offset_z': 0.1},
    {'z_angle': 0.1, 'scale_x': 1.4, 'y_distance': 0.1, 'pointer_offset_x': 0.2, 'pointer_offset_y': 0.3},
]


def run(context):
    global JOIN, GEN_IMG_PATH, ORACLE_IMG_PATH
    app: ac.Application = ac.Application.get()
    ui = app.userInterface
    try:
        # Prepare test fixture.
        doc = app.documents.add(ac.DocumentTypes.FusionDesignDocumentType)
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

        start_batch(ac.ViewOrientations.TopViewOrientation, ac.Point3D.create(0., 0., 0.), params)

        # Adjust camera.
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

        cmd_defs: ac.CommandDefinitions = ui.commandDefinitions
        cmd_id = 'ShowImageButtonId'
        cmd_def: ac.CommandDefinition | None = cmd_defs.itemById(cmd_id)
        if cmd_def is not None:
            cmd_def.deleteMe()
            cmd_def = cmd_defs.itemById(cmd_id)
            if cmd_def is not None:
                raise Exception(f'{cmd_id} deleteMe() failed.')
        cmd_def = cmd_defs.addButtonDefinition(cmd_id, 'ShowImage', 'tooltip')
        create_handler = ShowImageCommandCreatedEventHandler()
        cmd_def.commandCreated.add(create_handler)
        HANDLERS.append(create_handler)

        # Capture viewport images of each results and compare them with oracles.
        WH = 200
        with tempfile.TemporaryDirectory() as tmp:
            t = pathlib.Path(tmp)
            for o in acc2_occ.component.occurrences:
                o.isLightBulbOn = True
                app.activeViewport.saveAsImageFile(str(t / f'{o.component.name}.png'), WH, WH)
                o.isLightBulbOn = False
            msg = 'Compare test result with test oracles by your eyes.\nTop is oracle and bottom is result.\nComputer is not good enough at this job yet :-)'  # noqa: E501
            ui.messageBox(msg)
            # In detail:
            # With RPA, F360's window size affected test results subtly. I tried to find a good way to compare results with oracles
            # like feature value (SIFT etc.), but in vain.
            for o in acc2_occ.component.occurrences:
                # # Make oracle
                # from shutil import copy
                # copy(t / f'{o.component.name}.png', CURRENT_DIR / f'test_data/oracle/{o.component.name}.png')
                GEN_IMG_PATH = t / f'{o.component.name}.png'
                ORACLE_IMG_PATH = CURRENT_DIR / f'test_data/oracle/{o.component.name}.png'
                JOIN = False
                cmd_def.execute()
                while not JOIN:
                    adsk.doEvents()

        doc.close(False)
        cmd_def.deleteMe()
        HANDLERS.clear()

    except Exception:
        msg = traceback.format_exc()
        print(msg)
        if ui is not None:
            ui.messageBox('Failed in run():\n{}'.format(msg))


def do_many_events():
    from_time = time.time()
    while time.time() - from_time < 1:
        adsk.doEvents()


# Event handler for the commandCreated event.
class ShowImageCommandCreatedEventHandler(ac.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        cmd = ac.CommandCreatedEventArgs.cast(args).command

        on_destroy = ShowImageCommandDestroyHandler()
        cmd.destroy.add(on_destroy)
        HANDLERS.append(on_destroy)

        inputs = cmd.commandInputs
        oracle_in = inputs.addImageCommandInput('ID_ORACLE', 'Oracle', str(ORACLE_IMG_PATH))
        oracle_in.isFullWidth = True
        test_img_in = inputs.addImageCommandInput('ID_RESULT', 'Test', str(GEN_IMG_PATH))
        test_img_in.isFullWidth = True


# Event handler for the destroy event.
class ShowImageCommandDestroyHandler(ac.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        global JOIN
        JOIN = True
