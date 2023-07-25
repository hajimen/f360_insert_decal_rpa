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

from f360_insert_decal_rpa.custom_event_ids import CLEANUP_ID, FILL_PARAMETER_DIALOG, LOOP_HEAD_ID, REPORT_ERROR_ID, WAIT_DECAL_DIALOG_ID


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
class _Parameters:
    next_event_id: str
    error_event_id: str
    i_insert_decal_parameters: int
    insert_decal_parameters: ty.List[InsertDecalParameter]
    click_point: ac.Point2D


class _EventHandler(ac.CustomEventHandler):
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
            _UI.messageBox('Failed:\n{}'.format(traceback.format_exc()))


_PARAMETERS: ty.Union[_Parameters, None] = None
_UI: ac.UserInterface
_APP: ac.Application

_MAX_WAIT_RETRY = 3
_I_WAIT_RETRY = 0

_EVENTS: ty.Dict[str, ac.CustomEvent] = {}
_HANDLERS: ty.Dict[str, _EventHandler] = {}

EXTERNAL_PROCESS: subprocess.Popen


def _launch_external_process(retry=False):
    global EXTERNAL_PROCESS
    cd = pathlib.Path(__file__).parent
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

    EXTERNAL_PROCESS = subprocess.Popen(
        [str(pd_path / 'python.exe'), '-c', "import external_process; external_process.message_pump()"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        cwd=str(cd))
    init_ret = EXTERNAL_PROCESS.stdout.readline().decode().strip()

    if init_ret == 'comtypes cache cleared':
        if retry:
            raise Exception('comtypes cache troubled twice. Something looks wrong.')
        _launch_external_process(retry=True)
        return

    if init_ret == 'ctypes bug':
        raise Exception("F360's Python's buggy _ctypes.pyd is loaded. I don't know why. Avoid it.")

    if init_ret != 'ready':
        raise Exception("external process is not ready.")


def _call_external_process(func_name: str, args: ty.Any):
    byte_args = pickle.dumps(args)
    EXTERNAL_PROCESS.stdin.write((func_name + "\n").encode())
    EXTERNAL_PROCESS.stdin.write((f"{str(len(byte_args))}\n").encode())
    EXTERNAL_PROCESS.stdin.write(byte_args)
    EXTERNAL_PROCESS.stdin.flush()
    ret_len = int(EXTERNAL_PROCESS.stdout.readline().decode().strip())
    byte_ret = EXTERNAL_PROCESS.stdout.read(ret_len)
    return pickle.loads(byte_ret)


def start(next_event_id: str, error_event_id: str, view_orientation: ac.ViewOrientations, target_point: ac.Point3D, insert_decal_parameters: ty.List[InsertDecalParameter]):  # noqa: E501
    global _PARAMETERS, _UI, _APP

    _APP = ac.Application.get()
    if _PARAMETERS is not None:
        _APP.fireCustomEvent(error_event_id, 'insert_decal_rpa is not re-entrant.')
        return
    if _APP.preferences.generalPreferences.userLanguage != ac.UserLanguages.EnglishLanguage:
        _APP.fireCustomEvent(error_event_id, 'insert_decal_rpa requires English as user language.')
        return
    _UI = _APP.userInterface

    camera: ac.Camera = _APP.activeViewport.camera
    camera.target = target_point
    camera.viewOrientation = view_orientation
    _APP.activeViewport.camera = camera
    click_point = _APP.activeViewport.viewToScreen(_APP.activeViewport.modelToViewSpace(target_point))

    for s, f in _EVENT_DIC.items():
        _APP.unregisterCustomEvent(s)
        event = _APP.registerCustomEvent(s)
        handler = _EventHandler(f)
        event.add(handler)
        _EVENTS[s] = event
        _HANDLERS[s] = handler

    _launch_external_process()

    _UI.messageBox("Insert Decal RPA is going to start now. Please click 'OK' and don't touch the mouse or keyboard until the next message.", 'Insert Decal RPA')  # noqa: E501

    _PARAMETERS = _Parameters(next_event_id, error_event_id, 0, insert_decal_parameters, click_point)

    _APP.fireCustomEvent(LOOP_HEAD_ID)


def _loop_head():
    if _PARAMETERS.i_insert_decal_parameters == len(_PARAMETERS.insert_decal_parameters):
        _APP.fireCustomEvent(CLEANUP_ID)
        return

    p = _PARAMETERS.insert_decal_parameters[_PARAMETERS.i_insert_decal_parameters]

    def exec(cmd, fail_object):
        result = _APP.executeTextCommand(cmd)
        if result != 'Ok':
            _APP.fireCustomEvent(REPORT_ERROR_ID,
                                 f"I failed to do {fail_object}.")
            return True
        return False

    # Paste New
    acs = _UI.activeSelections
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

    ic: af.Component = _APP.activeProduct.rootComponent
    for n in o.fullPathName.split('+'):
        for io in ic.occurrences:
            io.isLightBulbOn = False
        io = ic.occurrences.itemByName(n)
        io.isLightBulbOn = True
        ic = io.component

    # FusionAddDecalCommand will be executed when this custom event handler runs out.
    _UI.commandDefinitions.itemById('FusionAddDecalCommand').execute()

    global _I_WAIT_RETRY
    _I_WAIT_RETRY = 0
    event_id, msg = _call_external_process('insert_from_my_computer', None)
    _APP.fireCustomEvent(event_id, msg)


def _wait_decal_dialog():
    global _I_WAIT_RETRY
    if 'FusionAddDecalCommandPanel' in _APP.executeTextCommand('Toolkit.cmdDialog'):
        cp = _PARAMETERS.click_point
        event_id, msg = _call_external_process('click', (cp.x, cp.y))
        _APP.fireCustomEvent(event_id, msg)
    elif _I_WAIT_RETRY == _MAX_WAIT_RETRY:
        _APP.fireCustomEvent(REPORT_ERROR_ID,
                             "I couldn't find DECAL dialog.")
    else:
        time.sleep(1.)
        _I_WAIT_RETRY += 1
        _APP.fireCustomEvent(WAIT_DECAL_DIALOG_ID)


def _fill_parameter_dialog():
    p = _PARAMETERS.insert_decal_parameters[_PARAMETERS.i_insert_decal_parameters]

    def exec(cmd):
        result = _APP.executeTextCommand(cmd)
        if result != 'Ok':
            _APP.fireCustomEvent(REPORT_ERROR_ID,
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

    _PARAMETERS.i_insert_decal_parameters += 1

    _APP.fireCustomEvent(LOOP_HEAD_ID)


def _cleanup():
    global _PARAMETERS
    for s in _EVENT_DIC.keys():
        handler = _HANDLERS[s]
        _EVENTS[s].remove(handler)
        _APP.unregisterCustomEvent(s)

    next_event_id = _PARAMETERS.next_event_id
    _PARAMETERS = None
    _call_external_process('exit', None)

    _UI.messageBox("Insert Decal RPA has been done.", 'Insert Decal RPA')
    _APP.fireCustomEvent(next_event_id)


def _report_error(msg):
    global _PARAMETERS
    for s in _EVENT_DIC.keys():
        handler = _HANDLERS[s]
        _EVENTS[s].remove(handler)
        _APP.unregisterCustomEvent(s)

    error_event_id = _PARAMETERS.error_event_id
    _PARAMETERS = None
    _call_external_process('exit', None)

    _UI.messageBox(msg + "\nInsert Decal RPA might be corrupted for Fusion 360 updates.", 'Insert Decal RPA')
    _APP.fireCustomEvent(error_event_id, msg)


_EVENT_DIC = {
    LOOP_HEAD_ID: _loop_head,
    WAIT_DECAL_DIALOG_ID: _wait_decal_dialog,
    FILL_PARAMETER_DIALOG: _fill_parameter_dialog,
    CLEANUP_ID: _cleanup,
    REPORT_ERROR_ID: _report_error
}
