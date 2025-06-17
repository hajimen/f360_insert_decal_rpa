from dataclasses import dataclass
from collections.abc import Iterable
import pathlib
import time

import adsk
import adsk.core as ac
import adsk.fusion as af


Z_AXIS = ac.Vector3D.create(0, 0, 1)
ORIGIN_P = ac.Point3D.create(0, 0, 0)


@dataclass
class InsertDecalParameter:
    '''
    Attributes and constructor's args
    ----------
    source_occurrence:
        The subject of Copy -> Paste-New operation.
    accommodate_occurrence:
        The destination place of Paste-New operation.
    new_name:
        The Paste-New-generated component's name.
    decal_image_file:
        PNG file.

    About the parameters below, leave them None when you leave as default.

    attributes:
        F360's component attributes set to the Paste-New-generated component.
    opacity:
        Same with the DECAL dialog. 0-100.
    [xy]_distance:
        centimeter
    z_angle:
        radian
    scale_[xy], scale_plane_xy, chain_faces:
        Same with the DECAL dialog.
    pointer_offset_[xyz]:
        Backward compatibility feature.
        In some cases, DECAL dialog result can be unstable if just the origin point was clicked.
        Offsetting from the origin point can cure it. The unit is centimeter.
    '''
    source_occurrence: af.Occurrence
    accommodate_occurrence: af.Occurrence
    new_name: str
    decal_image_file: pathlib.Path
    attributes: Iterable[tuple[str, str, str]] | None = None
    opacity: int | None = None
    x_distance: float | None = None
    y_distance: float | None = None
    z_angle: float | None = None
    scale_x: float | None = None
    scale_y: float | None = None
    scale_plane_xy: float | None = None
    chain_faces: bool | None = None
    pointer_offset_x: float | None = None
    pointer_offset_y: float | None = None
    pointer_offset_z: float | None = None


def start_batch(view_orientation: ac.ViewOrientations, target_point: ac.Point3D, insert_decal_parameters: Iterable[InsertDecalParameter]):  # noqa: E501
    '''Runs a batch of InsertDecalParameter list.

    Parameters
    ----------
    view_orientation:
        Usually ac.ViewOrientations.TopViewOrientation is a good choice. But if you need to insert
        a decal on the back side of the component, ac.ViewOrientations.BottomViewOrientation will be
        your choice.
    target_point:
        The location where mouse clicks while selecting the surface to insert a decal. Usually ac.Point3D.create(0., 0., 0.).
    insert_decal_parameters:
        You can process multiple source / decal image / dialog parameter set in a call.
    '''
    global APP
    APP = ac.Application.get()
    camera: ac.Camera = APP.activeViewport.camera
    camera.target = target_point
    camera.viewOrientation = view_orientation
    camera.isSmoothTransition = False
    last_camera = APP.activeViewport.camera
    APP.activeViewport.camera = camera

    last_dt = APP.activeProduct.designType
    APP.activeProduct.designType = af.DesignTypes.ParametricDesignType  # Now (2025-06-15) Decal API cannot work in DirectDesignType.

    # wait for camera transition
    from_time = time.time()
    while time.time() - from_time < 1.:
        adsk.doEvents()

    eye_point = APP.activeViewport.camera.eye

    for i, p in enumerate(insert_decal_parameters):
        if insert_decal(p, eye_point, target_point):
            raise Exception(f'f360_insert_decal_rpa error: #{i} of insert_decal_parameters looks wrong.')

    APP.activeViewport.camera = last_camera
    APP.activeProduct.designType = last_dt


def insert_decal(p: InsertDecalParameter, eye_point: ac.Point3D, target_point: ac.Point3D) -> bool:
    if paste_new(p):
        return True

    po_x = 0. if p.pointer_offset_x is None else p.pointer_offset_x
    po_y = 0. if p.pointer_offset_y is None else p.pointer_offset_y
    po_z = 0. if p.pointer_offset_z is None else p.pointer_offset_z
    v_po = ac.Vector3D.create(po_x, po_y, po_z)
    tp = target_point.copy()
    tp.translateBy(v_po)

    rc: af.Component = APP.activeProduct.rootComponent

    # find face to insert decal
    hit_points: ac.ObjectCollectionT[ac.Point3D] = ac.ObjectCollection.create()
    faces: ac.ObjectCollectionT[af.BRepFace] = rc.findBRepUsingRay(
        eye_point,
        eye_point.vectorTo(tp),
        af.BRepEntityTypes.BRepFaceEntityType,
        -1,
        True,
        hit_points
    )
    if len(faces) == 0:
        return True
    f = faces[0]
    tp = hit_points[0]
    decal_center_v = tp.asVector()

    # build transform Matrix3D
    mt = ac.Matrix3D.create()
    mt.setToIdentity()
    if p.scale_x is not None:
        mt.setCell(0, 0, p.scale_x)
    if p.scale_y is not None:
        mt.setCell(1, 1, p.scale_y)
    if p.scale_plane_xy is not None:
        x = mt.getCell(0, 0) * p.scale_plane_xy
        y = mt.getCell(1, 1) * p.scale_plane_xy
        mt.setCell(0, 0, x)
        mt.setCell(1, 1, y)

    # call API
    base_feature = rc.features.baseFeatures.add()
    if not base_feature.startEdit():
        raise Exception('BaseFeatures.startEdit() failed.')
    di = rc.decals.createInput(str(p.decal_image_file), [f], tp)
    dit = di.transform.copy()
    dit.invert()
    ta = dit.asArray()

    d_x = 0. if p.x_distance is None else p.x_distance
    d_y = 0. if p.y_distance is None else p.y_distance
    if d_x != 0. or d_y != 0.:
        xv = ac.Vector3D.create(*ta[0:3])
        xv.normalize()
        xv.scaleBy(d_x)
        yv = ac.Vector3D.create(*ta[4:7])
        yv.normalize()
        yv.scaleBy(d_y)
        dv = xv.copy()
        dv.add(yv)
        tp.translateBy(dv)
        hit_points.clear()
        faces: ac.ObjectCollectionT[af.BRepFace] = rc.findBRepUsingRay(
            eye_point,
            eye_point.vectorTo(tp),
            af.BRepEntityTypes.BRepFaceEntityType,
            -1,
            True,
            hit_points
        )
        for ff, hp in zip(faces, hit_points):
            if f == ff:
                decal_center_v = hp.asVector()
                break

    mr = ac.Matrix3D.create()
    mr.setToIdentity()
    if p.z_angle is not None:
        zv = ac.Vector3D.create(*ta[8:11])
        zv.normalize()
        mr.setToRotation(p.z_angle, zv, ORIGIN_P)

    mt.transformBy(di.transform)
    mt.transformBy(mr)
    mt.translation = decal_center_v
    di.transform = mt
    di.targetBaseFeature = base_feature
    if p.chain_faces is not None:
        di.isChainFaces = p.chain_faces
    if p.opacity is not None:
        di.opacity = p.opacity / 100
    if not base_feature.finishEdit():
        raise Exception('BaseFeatures.finishEdit() failed.')
    _ = rc.decals.add(di)

    return False


def paste_new(p: InsertDecalParameter) -> bool:
    rc: af.Component = APP.activeProduct.rootComponent

    def choose_light_bulb(os: Iterable[af.Occurrence]):
        acos = [rc.allOccurrencesByComponent(o.component)[0] for o in os]
        for aco in acos:
            ic = rc
            for n in aco.fullPathName.split('+'):
                for io in ic.occurrences:
                    io.isLightBulbOn = False
                io = ic.occurrences.itemByName(n)
                if io is None:
                    raise Exception('Occurrence.fullPathName seems wrong. Fusion 360 API broken?')
                ic = io.component
        for aco in acos:
            ic = rc
            for n in aco.fullPathName.split('+'):
                io = ic.occurrences.itemByName(n)
                if io is None:
                    raise Exception('Occurrence.fullPathName seems wrong. Fusion 360 API broken?')
                io.isLightBulbOn = True
                ic = io.component

    choose_light_bulb([p.source_occurrence, p.accommodate_occurrence])
    m = ac.Matrix3D.create()
    m.setToIdentity()
    o = p.accommodate_occurrence.component.occurrences.addNewComponentCopy(p.source_occurrence.component, m)
    if o is None:
        return True
    o.component.name = p.new_name

    if p.attributes is not None:
        for a in p.attributes:
            o.component.attributes.add(*a)

    o = o.createForAssemblyContext(p.accommodate_occurrence)
    choose_light_bulb([o])
    return False


def start(next_event_id: str, error_event_id: str, view_orientation: ac.ViewOrientations, target_point: ac.Point3D, insert_decal_parameters: list[InsertDecalParameter], silent=False):  # noqa: E501
    '''This is for backward compatibility. Use start_batch().

    Parameters
    ----------
    next_event_id:
        F360's custom event id. When the batch finishes successfully, the event will be fired.
    error_event_id:
        F360's custom event id. When the batch fails, the event will be fired.
        Error message is in args.additionalInfo of notify(self, args: ac.CustomEventArgs).
    view_orientation:
        See start_batch().
    target_point:
        See start_batch().
    insert_decal_parameters:
        See start_batch().
    silent:
        Just for backward compatibility. Always silent.
    '''
    app = ac.Application.get()
    try:
        start_batch(view_orientation, target_point, insert_decal_parameters)
        app.fireCustomEvent(next_event_id)
    except Exception as e:
        app.fireCustomEvent(error_event_id, 'f360_insert_decal_rpa Error:\n' + str(e))
