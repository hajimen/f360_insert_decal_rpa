# f360_insert_decal_rpa

f360_insert_decal_rpa is a Python library for Robotic Process Automation (RPA) of
Autodesk Fusion (f.k.a. Fusion 360)'s **Insert -> Decal -> Insert from my computer** operation.
Before Oct. 2024, F360 didn't have Decal APIs to do it. So I needed to automate.
Now F360 have it, but it doesn't work in direct modeling mode yet (10/2/2024).
See: [Decal API in direct modeling mode raises "RuntimeError: 2 : InternalValidationError : timelineObj"](https://forums.autodesk.com/t5/fusion-api-and-scripts/decal-api-in-direct-modeling-mode-raises-quot-runtimeerror-2/td-p/13056509)

## Limitations

- Windows only. I'm not familiar with Mac. But you can use it as a stub (no decals) for compatibility.
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

Don't forget to add `app-packages` directory to `sys.path` in your script / add-in. The name `app-packages` is just an example. 
You can name `app-packages` as you like.

### Integrate to your script / add-in (Mac)

1. `git clone` this repository. 

2. In your script / add-in directory, `pip3.12 install {path to f360_insert_decal_rpa repository directory} -t app-packages`

Use python 3.12 for Mac distributed by python.org or Homebrew. Why not embedded python in F360? F360 for Mac has a bug (wrong PYTHONPATH for 
Edit button -> VSCode -> terminal) and it makes troublesome to use embedded python.

3. Look at `f360_insert_decal_rpa Regression Test.py` and incorporate the usage to your script / add-in.

Don't forget to add `app-packages` directory to `sys.path` in your script / add-in. The name `app-packages` is just an example. 
You can name `app-packages` as you like.
