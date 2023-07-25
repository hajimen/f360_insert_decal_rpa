import typing as ty
from dataclasses import dataclass
import pathlib
import traceback
import time
import pickle
import subprocess
import sys

import adsk.core as ac
import adsk.fusion as af

from .custom_event_ids import CLEANUP_ID, FILL_PARAMETER_DIALOG, LOOP_HEAD_ID, REPORT_ERROR_ID, WAIT_DECAL_DIALOG_ID


@dataclass
class InsertDecalParameter:
    source_occurrence: af.Occurrence
    accommodate_occurrence: af.Occurrence
    new_name: str
    decal_image_path: pathlib.Path
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


@dataclass
class Parameters:
    next_event_id: str
    error_event_id: str
    i_insert_decal_parameters: int
    insert_decal_parameters: ty.List[InsertDecalParameter]
    click_point: ac.Point2D


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
    cd = pathlib.Path(__file__).parent.parent
    for i in sys.path:
        if r'Autodesk\webdeploy' in i:
            ip = pathlib.Path(i)
            if ip.name == 'Python':
                pd_path = ip
            elif len(ip.name) > 30:
                pd_path = ip / 'Python'
            break

    # This is a bug workaround of Python 3.7.6. There is a long story here.
    # There is an esoteric behavior in VSCode's Python debugger. The subprocess python.exe loads parent's _ctypes.pyd
    # when launched by "python.exe foo.py" format. I don't know why.
    # F360's Python's _ctypes.pyd has a bug which crashes pywinauto.
    # https://stackoverflow.com/questions/62037461/getting-error-while-running-a-script-which-uses-pywinauto
    # By launching "python.exe -c import foo; foo.main()" format, Python loads _ctypes.pyd which placed on current dir.

    module_root = '.'.join(__name__.split('.')[:-1])
    EXTERNAL_PROCESS = subprocess.Popen(
        [str(pd_path / 'python.exe'), '-c', f"import {module_root}.external_process as ep; ep.message_pump()"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        cwd=str(cd))
    init_ret = EXTERNAL_PROCESS.stdout.readline().decode().strip()

    if init_ret == 'comtypes cache cleared':
        if retry:
            raise Exception('comtypes cache troubled twice. Something looks wrong.')
        launch_external_process(retry=True)
        return

    if init_ret == 'ctypes bug':
        raise Exception("F360's Python's buggy _ctypes.pyd is loaded. I don't know why. Avoid it.")

    if init_ret != 'ready':
        raise Exception("external process is not ready.")


def call_external_process(func_name: str, args: ty.Any):
    byte_args = pickle.dumps(args)
    EXTERNAL_PROCESS.stdin.write((func_name + "\n").encode())
    EXTERNAL_PROCESS.stdin.write((f"{str(len(byte_args))}\n").encode())
    EXTERNAL_PROCESS.stdin.write(byte_args)
    EXTERNAL_PROCESS.stdin.flush()
    ret_len = int(EXTERNAL_PROCESS.stdout.readline().decode().strip())
    byte_ret = EXTERNAL_PROCESS.stdout.read(ret_len)
    return pickle.loads(byte_ret)


def start(next_event_id: str, error_event_id: str, view_orientation: ac.ViewOrientations, target_point: ac.Point3D, insert_decal_parameters: ty.List[InsertDecalParameter]):  # noqa: E501
    global PARAMETERS, UI, APP

    APP = ac.Application.get()
    if PARAMETERS is not None:
        APP.fireCustomEvent(error_event_id, 'insert_decal_rpa is not re-entrant.')
        return
    if APP.preferences.generalPreferences.userLanguage != ac.UserLanguages.EnglishLanguage:
        APP.fireCustomEvent(error_event_id, 'insert_decal_rpa requires English as user language.')
        return
    UI = APP.userInterface

    camera: ac.Camera = APP.activeViewport.camera
    camera.target = target_point
    camera.viewOrientation = view_orientation
    APP.activeViewport.camera = camera
    click_point = APP.activeViewport.viewToScreen(APP.activeViewport.modelToViewSpace(target_point))

    for s, f in EVENT_DIC.items():
        APP.unregisterCustomEvent(s)
        event = APP.registerCustomEvent(s)
        handler = EventHandler(f)
        event.add(handler)
        EVENTS[s] = event
        HANDLERS[s] = handler

    launch_external_process()

    UI.messageBox("Insert Decal RPA is going to start now. Please click 'OK' and don't touch the mouse or keyboard until the next message.", 'Insert Decal RPA')  # noqa: E501

    PARAMETERS = Parameters(next_event_id, error_event_id, 0, insert_decal_parameters, click_point)

    APP.fireCustomEvent(LOOP_HEAD_ID)


def loop_head():
    if PARAMETERS.i_insert_decal_parameters == len(PARAMETERS.insert_decal_parameters):
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
    if exec('NuCommand.CommitCmd', 'OK in the dialog'):
        return
    acs.clear()
    current_names = {o.name for o in p.accommodate_occurrence.component.occurrences}
    temp_name = (current_names - existing_names).pop()
    o = p.accommodate_occurrence.component.occurrences.itemByName(temp_name)
    o.component.name = p.new_name

    if p.attributes is not None:
        for a in p.attributes:
            o.component.attributes.add(*a)

    ic: af.Component = APP.activeProduct.rootComponent
    for n in o.fullPathName.split('+'):
        for io in ic.occurrences:
            io.isLightBulbOn = False
        io = ic.occurrences.itemByName(n)
        io.isLightBulbOn = True
        ic = io.component

    # FusionAddDecalCommand will be executed when this custom event handler runs out.
    UI.commandDefinitions.itemById('FusionAddDecalCommand').execute()

    global I_WAIT_RETRY
    I_WAIT_RETRY = 0
    event_id, msg = call_external_process('insert_from_my_computer', None)
    APP.fireCustomEvent(event_id, msg)


def wait_decal_dialog():
    global I_WAIT_RETRY
    if 'FusionAddDecalCommandPanel' in APP.executeTextCommand('Toolkit.cmdDialog'):
        cp = PARAMETERS.click_point
        event_id, msg = call_external_process('click', (int(cp.x), int(cp.y)))
        APP.fireCustomEvent(event_id, msg)
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
            if exec(f'Commands.SetDoubleValue {n} {v}'):
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


def cleanup():
    global PARAMETERS
    for s in EVENT_DIC.keys():
        handler = HANDLERS[s]
        EVENTS[s].remove(handler)
        APP.unregisterCustomEvent(s)

    next_event_id = PARAMETERS.next_event_id
    PARAMETERS = None
    call_external_process('exit', None)

    UI.messageBox("Insert Decal RPA has been done.", 'Insert Decal RPA')
    APP.fireCustomEvent(next_event_id)


def report_error(msg):
    global PARAMETERS
    for s in EVENT_DIC.keys():
        handler = HANDLERS[s]
        EVENTS[s].remove(handler)
        APP.unregisterCustomEvent(s)

    error_event_id = PARAMETERS.error_event_id
    PARAMETERS = None
    call_external_process('exit', None)

    UI.messageBox(msg + "\nInsert Decal RPA might be corrupted for Fusion 360 updates.", 'Insert Decal RPA')
    APP.fireCustomEvent(error_event_id, msg)


EVENT_DIC = {
    LOOP_HEAD_ID: loop_head,
    WAIT_DECAL_DIALOG_ID: wait_decal_dialog,
    FILL_PARAMETER_DIALOG: fill_parameter_dialog,
    CLEANUP_ID: cleanup,
    REPORT_ERROR_ID: report_error
}
