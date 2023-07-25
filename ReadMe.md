# f360_insert_decal_rpa

f360_insert_decal_rpa is a Python library for Robotic Process Automation (RPA) of
Autodesk Fusion 360's **Insert -> Decal -> Insert from my computer** operation.
F360 doesn't have APIs to do it yet (7/24/2023). So I need to automate.

## Limitations

- Windows only. I'm not familiar with Mac. But you can use it as a stub (no decals).
- Very slow.
- Not pixel-wise precise. F360 itself doesn't have much precision about decals.

## Installation and Usage

### Regression test (Windows)

I recommend you to do Regression test first, because RPA easily corrupts for environmental changes.
F360 updates rapidly.

1. `git clone` this repository. 

2. Open terminal in the repository directory, and configure PATH env to F360's embedded python.exe.

3. `python -m pip install .[dev] -t app-packages`

4. In F360, open **Scripts and Ad-ins** dialog, click on "+" icon in **Script** tab,
and specify the repository directory.

5. Choose **f360_insert_decal_rpa Regression Test** and run it.

### Regression test (Mac)

1. `git clone` this repository, and open terminal in the repository directory.

2. `mkdir app-packages`

3. In F360, open **Scripts and Ad-ins** dialog, click on "+" icon in **Script** tab,
and specify the repository directory.

4. Choose **f360_insert_decal_rpa Regression Test** and run it.

It is just a smoke test.

### Integrate to your script / add-in (Windows)

1. `git clone` this repository. 

2. In your script / add-in directory, `python -m pip install {path to f360_insert_decal_rpa repository directory} -t app-packages`

Use embedded python in F360.

3. Look at `f360_insert_decal_rpa Regression Test.py` and incorporate the usage to your script / add-in.

Don't forget to add `app-packages` directory to `sys.path` in your script / add-in.

### Integrate to your script / add-in (Mac)

1. `git clone` this repository. 

2. In your script / add-in directory, `pip3.9 install {path to f360_insert_decal_rpa repository directory} -t app-packages`

Use x86-64 python 3.9 for Mac. Why not embedded python in F360? F360 for Mac doesn't have `pip` module in its embedded python.
Why x86-64? F360 uses it now (2023/7/24).

3. Look at `f360_insert_decal_rpa Regression Test.py` and incorporate the usage to your script / add-in.

Don't forget to add `app-packages` directory to `sys.path` in your script / add-in.
