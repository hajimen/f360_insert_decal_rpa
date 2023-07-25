import typing as ty
from dataclasses import dataclass
import pathlib
import traceback
import time
import pickle
import subprocess
import sys
import threading

import adsk.core as ac
import adsk.fusion as af

# enable here while debugging
cei = '.'.join(__name__.split('.')[:-1] + ['custom_event_ids'])
if cei in sys.modules:
    import importlib
    importlib.reload(sys.modules[cei])
del cei

from .custom_event_ids import CLEANUP_ID, FILL_PARAMETER_DIALOG, LOOP_HEAD_ID, REPORT_ERROR_ID, WAIT_DECAL_DIALOG_ID, START_NEXT_ID


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
    scale_[xy], scale_plane_xy, [hv]_flip, chain_faces:
        Same with the DECAL dialog.
    pointer_offset_[xy]:
        In some cases, DECAL dialog result can be unstable if just the origin point was clicked.
        Offsetting from the origin point can cure it.
    '''
    source_occurrence: af.Occurrence
    accommodate_occurrence: af.Occurrence
    new_name: str
    decal_image_file: pathlib.Path
    attributes: ty.Union[ty.List[ty.Tuple[str, str, str]], None] = None
    opacity: ty.Union[int, None] = None
    x_distance: ty.Union[float, None] = None
    y_distance: ty.Union[float, None] = None
    z_angle: ty.Union[float, None] = None
    scale_x: ty.Union[float, None] = None
    scale_y: ty.Union[float, None] = None
    scale_plane_xy: ty.Union[float, None] = None
    h_flip: ty.Union[bool, None] = None
    v_flip: ty.Union[bool, None] = None
    chain_faces: ty.Union[bool, None] = None
    pointer_offset_x: ty.Union[int, int, None] = None
    pointer_offset_y: ty.Union[int, int, None] = None


@dataclass
class Parameters:
    next_event_id: str
    error_event_id: str
    i_insert_decal_parameters: int
    insert_decal_parameters: ty.List[InsertDecalParameter]
    click_point: ty.Union[ac.Point2D, None]
    target_point: ac.Point3D
    view_orientation: ac.ViewOrientations
    silent: bool


class EventHandler(ac.CustomEventHandler):
    def __init__(self, func):
        super().__init__()
        self.func = func

    def notify(self, args: ac.CustomEventArgs):
        try:
            if args.additionalInfo == '':
                self.func()
            else:
                self.func(args.additionalInfo)
        except Exception:
            print(traceback.format_exc(), file=sys.stderr)
            UI.messageBox('Failed:\n{}'.format(traceback.format_exc()))


PARAMETERS: ty.Union[Parameters, None] = None
UI: ac.UserInterface
APP: ac.Application

MAX_WAIT_RETRY = 3
I_WAIT_RETRY = 0

EVENTS: ty.Dict[str, ac.CustomEvent] = {}
HANDLERS: ty.Dict[str, EventHandler] = {}

EXTERNAL_PROCESS: subprocess.Popen


def launch_external_process(retry=False):
    global EXTERNAL_PROCESS

    for i in sys.path:
        if r'Autodesk\webdeploy' in i:
            ip = pathlib.Path(i)
            if ip.name == 'Python':
                pd_path = ip
            elif len(ip.name) > 30:
                pd_path = ip / 'Python'
            break

    # This was a bug workaround of Python 3.7.6 which was embedded in old Fusion 360. There is a long story here.
    # I'm tired to remove the workaround.

    EXTERNAL_PROCESS = subprocess.Popen(
        [str(pd_path / 'python.exe'), "external_process.py"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=str(pathlib.Path(__file__).parent))
    init_ret = EXTERNAL_PROCESS.stdout.readline().decode().strip()

    if init_ret == 'comtypes cache cleared':
        if retry:
            raise Exception('comtypes cache troubled twice. Something looks wrong.')
        launch_external_process(retry=True)
        return

    if init_ret != 'ready':
        err_str = EXTERNAL_PROCESS.stderr.read().decode()
        raise Exception(f"external process is not ready.\nError message from the process: {init_ret}\nstderr:\n{err_str}")


def call_external_process(func_name: str, args: ty.Any):
    byte_args = pickle.dumps(args)
    EXTERNAL_PROCESS.stdin.write((func_name + "\n").encode())
    EXTERNAL_PROCESS.stdin.write((f"{str(len(byte_args))}\n").encode())
    EXTERNAL_PROCESS.stdin.write(byte_args)
    EXTERNAL_PROCESS.stdin.flush()
    threading.Thread(target=call_external_process_receive).start()


def call_external_process_receive():
    # An worker thread to an wait response from the external process.
    ret_len = int(EXTERNAL_PROCESS.stdout.readline().decode().strip())
    byte_ret = EXTERNAL_PROCESS.stdout.read(ret_len)
    ret = pickle.loads(byte_ret)
    if ret is None:  # exit
        return
    event_id, msg = ret
    APP.fireCustomEvent(event_id, msg)


def start(next_event_id: str, error_event_id: str, view_orientation: ac.ViewOrientations, target_point: ac.Point3D, insert_decal_parameters: ty.List[InsertDecalParameter], silent=False):  # noqa: E501
    '''Start RPA.

    Parameters
    ----------
    next_event_id:
        F360's custom event id. When RPA finishes successfully, the event will be fired.
    error_event_id:
        F360's custom event id. When RPA fails, the event will be fired.
        Error message is in args.additionalInfo of notify(self, args: ac.CustomEventArgs).
    view_orientation:
        Usually ac.ViewOrientations.TopViewOrientation is a good choice. But if you need to insert
        a decal on the back side of the component, ac.ViewOrientations.BottomViewOrientation will be
        your choice.
    target_point:
        The location where mouse clicks while selecting the surface to insert a decal. Usually ac.Point3D.create(0., 0., 0.).
    insert_decal_parameters:
        RPA is a batch. You can process multiple source / decal image / dialog parameter set in a call.
    silent:
        You can suppress RPA start / finish / failure message boxes.
    '''
    global PARAMETERS, UI, APP

    APP = ac.Application.get()
    if PARAMETERS is not None:
        APP.fireCustomEvent(error_event_id, 'insert_decal_rpa is not re-entrant.')
        return
    if APP.preferences.generalPreferences.userLanguage != ac.UserLanguages.EnglishLanguage:
        APP.fireCustomEvent(error_event_id, 'insert_decal_rpa requires English as user language.')
        return
    UI = APP.userInterface

    for s, f in EVENT_DIC.items():
        APP.unregisterCustomEvent(s)
        event = APP.registerCustomEvent(s)
        handler = EventHandler(f)
        event.add(handler)
        EVENTS[s] = event
        HANDLERS[s] = handler

    launch_external_process()
    PARAMETERS = Parameters(next_event_id, error_event_id, 0, insert_decal_parameters, None, target_point, view_orientation, silent)
    call_external_process('set_focus', None)


def start_next():
    camera: ac.Camera = APP.activeViewport.camera
    camera.target = PARAMETERS.target_point
    camera.viewOrientation = PARAMETERS.view_orientation
    APP.activeViewport.camera = camera
    PARAMETERS.click_point = APP.activeViewport.viewToScreen(APP.activeViewport.modelToViewSpace(PARAMETERS.target_point))

    if not PARAMETERS.silent:
        UI.messageBox("Insert Decal RPA is going to start now. Please click 'OK' and don't touch the mouse or keyboard until the next message.", 'Insert Decal RPA')  # noqa: E501

    APP.fireCustomEvent(LOOP_HEAD_ID)


def loop_head():
    if PARAMETERS.i_insert_decal_parameters == len(PARAMETERS.insert_decal_parameters):
        if PARAMETERS.silent:
            # mouse pointer on main window often disturbs unit test.
            call_external_process('move_mouse', (0, 0, CLEANUP_ID))
        else:
            APP.fireCustomEvent(CLEANUP_ID)
        return

    p = PARAMETERS.insert_decal_parameters[PARAMETERS.i_insert_decal_parameters]

    def exec(cmd, fail_object):
        result = APP.executeTextCommand(cmd)
        if result != 'Ok':
            APP.fireCustomEvent(REPORT_ERROR_ID,
                                f"I failed to do {fail_object}.")
            return True
        return False

    # Paste New
    rc: af.Component = APP.activeProduct.rootComponent

    def choose_light_bulb(os: ty.List[af.Occurrence]):
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

    acs = UI.activeSelections
    acs.clear()
    acs.add(p.source_occurrence)
    if exec('Commands.Start CopyCommand', 'Ctrl-C copy'):
        return
    acs.clear()
    existing_names = {o.name for o in p.accommodate_occurrence.component.occurrences}
    acs.add(p.accommodate_occurrence)

    if exec('Commands.Start FusionPasteNewCommand', '"Paste New"'):
        return
    if exec('NuCommands.CommitCmd', 'OK in the dialog'):
        return
    acs.clear()
    current_names = {o.name for o in p.accommodate_occurrence.component.occurrences}
    temp_name = (current_names - existing_names).pop()
    o = p.accommodate_occurrence.component.occurrences.itemByName(temp_name)
    o.component.name = p.new_name

    if p.attributes is not None:
        for a in p.attributes:
            o.component.attributes.add(*a)

    o = o.createForAssemblyContext(p.accommodate_occurrence)
    choose_light_bulb([o])

    # FusionAddDecalCommand will be executed when this custom event handler has been finished.
    UI.commandDefinitions.itemById('FusionAddDecalCommand').execute()

    global I_WAIT_RETRY
    I_WAIT_RETRY = 0
    call_external_process('insert_from_my_computer', (p.decal_image_file, ))


def wait_decal_dialog():
    global I_WAIT_RETRY
    if 'FusionAddDecalCommandPanel' in APP.executeTextCommand('Toolkit.cmdDialog'):
        p: InsertDecalParameter = PARAMETERS.insert_decal_parameters[PARAMETERS.i_insert_decal_parameters]
        po_x = 0 if p.pointer_offset_x is None else p.pointer_offset_x
        po_y = 0 if p.pointer_offset_y is None else p.pointer_offset_y
        cp = PARAMETERS.click_point
        call_external_process('click', (int(cp.x) + po_x, int(cp.y) + po_y))
    elif I_WAIT_RETRY == MAX_WAIT_RETRY:
        APP.fireCustomEvent(REPORT_ERROR_ID,
                            "I couldn't find DECAL dialog.")
    else:
        time.sleep(1.)
        I_WAIT_RETRY += 1
        APP.fireCustomEvent(WAIT_DECAL_DIALOG_ID)


def fill_parameter_dialog():
    p = PARAMETERS.insert_decal_parameters[PARAMETERS.i_insert_decal_parameters]

    def exec(cmd):
        result = APP.executeTextCommand(cmd)
        if result != 'Ok':
            APP.fireCustomEvent(REPORT_ERROR_ID,
                                "I couldn't control DECAL dialog.")
            return True
        return False

    if p.opacity is not None:
        if exec(f'Commands.SetIntValue DecalOpacityInput {p.opacity}'):
            return
    dv_dict = {
        'x_distance': 'AxisX',
        'y_distance': 'AxisY',
        'z_angle': 'RotateZ',
        'scale_x': 'ScaleX',
        'scale_y': 'ScaleY',
        'scale_plane_xy': 'ScalePlaneXY'
    }
    for a, n in dv_dict.items():
        v = getattr(p, a)
        if v is not None:
            if exec(f'Commands.SetDouble {n} {v}'):
                return
    bv_dict = {
        'h_flip': 'HorizonalFlip',  # The 'Horizonal' is F360's spell.
        'v_flip': 'VerticalFlip',
        'chain_faces': 'DecalChainFaces'
    }
    for a, n in bv_dict.items():
        v = getattr(p, a)
        if v is not None:
            if exec(f'Commands.SetBool {n} {"1" if v else "0"}'):
                return

    if exec('NuCommands.CommitCmd'):
        return

    PARAMETERS.i_insert_decal_parameters += 1

    APP.fireCustomEvent(LOOP_HEAD_ID)


def cleanup_common():
    global PARAMETERS
    for s in EVENT_DIC.keys():
        handler = HANDLERS[s]
        EVENTS[s].remove(handler)
        APP.unregisterCustomEvent(s)
    PARAMETERS = None
    call_external_process('exit', None)


def cleanup():
    next_event_id = PARAMETERS.next_event_id
    silent = PARAMETERS.silent

    cleanup_common()

    if not silent:
        UI.messageBox("Insert Decal RPA has been done.", 'Insert Decal RPA')
    APP.fireCustomEvent(next_event_id)


def report_error(msg):
    error_event_id = PARAMETERS.error_event_id
    silent = PARAMETERS.silent

    cleanup_common()

    if not silent:
        UI.messageBox('Insert Decal RPA Runtime Error:\n' + msg + "\nInsert Decal RPA might be corrupted for Fusion 360 updates.", 'Insert Decal RPA')
    APP.fireCustomEvent(error_event_id, msg)


EVENT_DIC = {
    START_NEXT_ID: start_next,
    LOOP_HEAD_ID: loop_head,
    WAIT_DECAL_DIALOG_ID: wait_decal_dialog,
    FILL_PARAMETER_DIALOG: fill_parameter_dialog,
    CLEANUP_ID: cleanup,
    REPORT_ERROR_ID: report_error
}
