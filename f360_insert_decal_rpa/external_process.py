import sys
import typing as ty
import time
import pathlib
import pickle

from f360_insert_decal_rpa.custom_event_ids import REPORT_ERROR_ID, WAIT_DECAL_DIALOG_ID, FILL_PARAMETER_DIALOG


MAX_WAIT_RETRY = 3
CURRENT_DIR = pathlib.Path(__file__).parent
SYS_PATHS = ['app-packages', 'app-packages/win32', 'app-packages/win32/lib', 'app-packages/pythonwin']


def append_syspath():
    for sp in SYS_PATHS:
        p = str(CURRENT_DIR / sp)
        if p not in sys.path:
            sys.path.append(p)


append_syspath()
del append_syspath


import ctypes
ctypes.cdll.LoadLibrary(str(CURRENT_DIR / 'app-packages/pywin32_system32/pywintypes37.dll'))

import warnings
warnings.simplefilter("ignore", UserWarning)

# print(str(sys.modules['_ctypes']), file=sys.stderr)  # This line crashes VSCode Python debugger. I don't know why.

try:
    import pywinauto
except TypeError:  # Python 3.7.6's ctypes bug. Load fixed _ctypes.pyd.
    sys.stdout.buffer.write('ctypes bug\n'.encode())
    sys.stdout.flush()
    exit()
except Exception:  # comtypes cache?
    import traceback
    traceback.print_exc(file=sys.stderr)
    import subprocess
    subprocess.run([sys.executable, 'clear_comtypes_cache.py', '-y'], cwd=str(CURRENT_DIR / 'app-packages/bin'))
    sys.stdout.buffer.write('comtypes cache cleared\n'.encode())
    sys.stdout.flush()
    exit()

sys.stdout.buffer.write('ready\n'.encode())
sys.stdout.flush()

import pywinauto.mouse

UIA: pywinauto.Application = pywinauto.Application(backend='uia').connect(path='Fusion360.exe')


def message_pump():
    for line in iter(sys.stdin.buffer.readline, b''):
        func_name = line.decode().rstrip()
        if func_name == 'exit':
            byte_ret = pickle.dumps(None)
            sys.stdout.buffer.write((str(len(byte_ret)) + '\n').encode())
            sys.stdout.buffer.write(byte_ret)
            sys.stdout.flush()
            return
        arg_len = int(sys.stdin.buffer.readline().decode().strip())
        args = pickle.loads(sys.stdin.buffer.read(arg_len))
        ret = FUNC_DICT[func_name](*args)
        byte_ret = pickle.dumps(ret)
        sys.stdout.buffer.write((str(len(byte_ret)) + '\n').encode())
        sys.stdout.buffer.write(byte_ret)
        sys.stdout.flush()


def insert_from_my_computer(decal_image_path: pathlib.Path):
    ifm_elem = None
    for _ in range(MAX_WAIT_RETRY):
        time.sleep(0.5)
        ifms = UIA.top_window().descendants(title='Insert from my computer...')
        if len(ifms) == 0:
            time.sleep(2.)
            continue
        else:
            ifm_elem = ifms[0]
            break
    if ifm_elem is None:
        return (REPORT_ERROR_ID,
                "I couldn't find 'Insert from my computer...' in the dialog.")

    ifm_elem.click_input()
    time.sleep(0.5)

    file_edit = None
    for _ in range(MAX_WAIT_RETRY):
        time.sleep(0.5)
        fes = UIA.top_window().descendants(title='File name:', class_name='Edit')
        if len(fes) == 0:
            time.sleep(2.)
            continue
        else:
            file_edit = fes[0]
            break
    if file_edit is None:
        return (REPORT_ERROR_ID,
                "I couldn't find 'File name:' in the dialog.")

    file_edit.set_edit_text(str(decal_image_path))
    file_edit.type_keys("{ENTER}")

    return (WAIT_DECAL_DIALOG_ID, '')


def click(x: int, y: int):
    pywinauto.mouse.click(coords=(x, y))
    return (FILL_PARAMETER_DIALOG, '')


def echo(*args: ty.Any):
    return args


FUNC_DICT = {
    'insert_from_my_computer': insert_from_my_computer,
    'click': click,
    'echo': echo
}

if __name__ == '__main__':
    message_pump()
