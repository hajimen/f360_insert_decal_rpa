# Changelog

## Initial Release: Version 0.0.1 : 2021/7/9

## Version 0.0.2 : 2021/7/21

- Bug fix: Now it works fine on non top-level components.

## Version 0.1.1 : 2022/4/2

- Follows the update of Fusion 360, especially Python 3.9.7.

## Version 0.1.2 : 2022/4/6

- Bug fix: Now it works fine while debugging.

## Version 0.1.3 : 2022/5/20

- `pointer_offset_[xy]` has been added to cure the instability of DECAL command result.

## Version 0.1.4 : 2022/6/1

- `minimize_maximize()` fails in scaling screen (high resolution display). Now it just `set_focus()`.
- Sometimes RPA fails before clicking `Insert from my computer`. Now waits longer.

## Version 0.1.5 : 2022/6/9

- The `pointer_offset_[xy]` becomes `pointer_offset_[xyz]` and the unit becomes centimeter.

## Version 0.1.6 : 2023/7/24

- Fallback mode for Mac.
- Better test oracles / results for regression test.

## Version 0.1.7 : 2023/7/25

- Follows the change of High DPI behavior in Fusion 360 2.0.16753.

## Version 0.1.8 : 2023/7/26

- Follows the change of Fusion 360 2.0.16753 for Mac.
- Fix the issue that `python -m build --wheel` made a huge whl file.

## Version 0.1.9 : 2023/7/27

- To integrate, directory name `app-packages` is not mandatory now. You can name as you like in your F360 script / add-in.

## Version 0.1.10 : 2023/11/8

- Followed Fusion 360 Python update to 3.11.

## Version 0.1.11 : 2024/4/13

- Now it can run on non-English Windows and Fusion 360.

## Version 0.1.12 : 2024/4/14

- Now it is much more robust to the display scale variation.

## Version 0.1.13 : 2024/10/1

- Now it runs on Python 3.12. Latest F360 requires it.
