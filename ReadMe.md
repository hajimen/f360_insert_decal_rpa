# f360_insert_decal_rpa

**f360_insert_decal_rpa** was a Python library for Robotic Process Automation (RPA) of
Autodesk Fusion (f.k.a. Fusion 360)'s **Insert -> Decal -> Insert from my computer** operation.
Before June 2025, F360 didn't have (functional) Decal APIs to do it. So I needed to automate.

Now F360 have (functional) Decal APIs. Now f360_insert_decal_rpa offers just backward compatibility.

## Backward incompatibility from 0.2.1

- Lacks `h_flip` and `v_flip`. I cannot reproduce the behavior of them in Decal dialog by Decal APIs.
It might be a bug of the API. But who requires the feature?

- The decal location can be misaligned.

## Installation and usage

### Regression test

1. `git clone` this repository. 

2. In F360, open **Scripts and Ad-ins** dialog, click on "+" icon, choose "Script or add-in from device",
and specify the repository directory.

3. Choose **f360_insert_decal_rpa Regression Test** and run it.

### Integrate to your script / add-in

1. `git clone` this repository. 

2. Look at `f360_insert_decal_rpa Regression Test.py` and incorporate the usage to your script / add-in.

## License

MIT license.
