from time import sleep
import sys
import pathlib
import pickle
import ctypes
from custom_event_ids import REPORT_ERROR_ID, WAIT_DECAL_DIALOG_ID, FILL_PARAMETER_DIALOG, START_NEXT_ID

# 'Insert from my computer...' dialog is slow.
SLEEP_AROUND_INSERT_FROM_MY_COMPUTER = 0.5

PACKAGES_DIR = pathlib.Path(__file__).parent.parent
if PACKAGES_DIR.name != 'app-packages':  # Running in the repository, not installed by pip.
    PACKAGES_DIR = PACKAGES_DIR / 'app-packages'


def append_syspath():
    for sp in ['', 'win32', 'win32/lib', 'pythonwin']:
        p = str(PACKAGES_DIR / sp)
        if p not in sys.path:
            sys.path.append(p)


append_syspath()
del append_syspath

ctypes.cdll.LoadLibrary(str(PACKAGES_DIR / 'pywin32_system32/pywintypes39.dll'))

# Check comtypes cache
try:
    import pywinauto
except Exception:
    # comtypes cache?
    import traceback
    traceback.print_exc(file=sys.stderr)
    import subprocess
    subprocess.run([sys.executable, 'clear_comtypes_cache.py', '-y'], cwd=str(PACKAGES_DIR / 'bin'))
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
        if args is None:
            ret = FUNC_DICT[func_name]()
        else:
            ret = FUNC_DICT[func_name](*args)
        byte_ret = pickle.dumps(ret)
        sys.stdout.buffer.write((str(len(byte_ret)) + '\n').encode())
        sys.stdout.buffer.write(byte_ret)
        sys.stdout.flush()


def minimize_maximize():
    tw = UIA.top_window()
    tw.minimize()
    tw.maximize()
    return (START_NEXT_ID, '')


def insert_from_my_computer(decal_image_file: pathlib.Path):
    try:
        sleep(SLEEP_AROUND_INSERT_FROM_MY_COMPUTER)
        ifm_elem = UIA.window(title='Insert').child_window(title='Insert from my computer...')
        sleep(SLEEP_AROUND_INSERT_FROM_MY_COMPUTER)
        ifm_elem.click_input()
    except Exception:
        return (REPORT_ERROR_ID, "I couldn't find 'Insert from my computer...' in the dialog.")

    try:
        file_edit = UIA.top_window().child_window(title='File name:', class_name='Edit')
        file_edit.set_edit_text(str(decal_image_file))
        file_edit.type_keys("{ENTER}")
    except Exception:
        return (REPORT_ERROR_ID, "I couldn't find 'File name:' edit box in the dialog.")

    return (WAIT_DECAL_DIALOG_ID, '')


def click(x: int, y: int):
    # Qt for Windows sometimes ignore simple automated click. Mimic human move.
    try:
        pywinauto.mouse.move(coords=(x - 2, y))
        pywinauto.mouse.move(coords=(x - 1, y))
        pywinauto.mouse.click(coords=(x, y))
        return (FILL_PARAMETER_DIALOG, '')
    except Exception:
        return (REPORT_ERROR_ID, "I couldn't move / click mouse.")


def move_mouse(x: int, y: int, next_id: str):
    try:
        pywinauto.mouse.move(coords=(x, y))
        return (next_id, '')
    except Exception:
        return (REPORT_ERROR_ID, "I couldn't move mouse.")


FUNC_DICT = {
    'insert_from_my_computer': insert_from_my_computer,
    'click': click,
    'minimize_maximize': minimize_maximize,
    'move_mouse': move_mouse,
}

if __name__ == '__main__':
    message_pump()
