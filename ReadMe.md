# f360_insert_decal_rpa

f360_insert_decal_rpa is a Python library for Robotic Process Automation (RPA) of
Autodesk Fusion 360's **Insert -> Decal -> Insert from my computer** operation.
F360 doesn't have APIs to do it yet (7/9/2021). So I need to automate.

## Limitations

- Windows only. I don't have a Mac :-)
- Very slow.
- Not pixel-wise precise. F360 itself doesn't have much precision about decals.

## Installation and Usage

### Unit test

I recommend you to unit test first, because RPA easily corrupts for environmental changes.
F360 updates rapidly.

1. `git clone` this repository. 

2. Open terminal in the repository directory, and configure PATH env to F360's python.exe.

3. `python -m pip install -r test-requirements.txt -t app-packages`

4. In F360, open **Scripts and Ad-ins** dialog, click on "+" icon in **Script** tab,
and specify the repository directory.

5. Choose **InsertDecalRPA** and run it.

### Integrate to your script / add-in

1. `git clone` this repository. 

2. In your script / add-in directory, `python -m pip install {path to f360_insert_decal_rpa repository directory} -t app-packages`

3. Look at `InsertDecalRPA.py` and incorporate the usage to your script / add-in.

Don't forget to add `app-packages` directory to `sys.path` in your script / add-in.

## Misc.

### What is `_ctypes.pyd`?

Today (7/9/2021), F360's Python is 3.7.6. It has a bug in `ctypes`. It crashes `pywinauto`.
[https://stackoverflow.com/questions/62037461/getting-error-while-running-a-script-which-uses-pywinauto](https://stackoverflow.com/questions/62037461/getting-error-while-running-a-script-which-uses-pywinauto)

The bug is in `_ctypes.pyd`. So I decided to run `pywinauto` in a child process, and make it to load newer `_ctypes.pyd`.
