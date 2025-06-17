# Changelog

## [0.3.2] - 2025-06-17

- Bug fix: now it can handle all direction of the decal.
- Better reproduction of alignment.

## [0.3.1] - 2025-06-16

- Now it uses Decal API instead of PRA. Now it offers just backward compatibility.
- Drops `h_flip` and `v_flip` features.
- Drops all dependencies.

## [0.2.1] - 2025-01-29

- Now it uses new API replacing copy/paste.
- Changelog style has been changed.

## [0.1.13] - 2024-10-01

- Now it runs on Python 3.12. Latest F360 requires it.

## [0.1.12] - 2024-04-14

- Now it is much more robust to the display scale variation.

## [0.1.11] - 2024-04-13

- Now it can run on non-English Windows and Fusion 360.

## [0.1.10] - 2023-11-08

- Followed Fusion 360 Python update to 3.11.

## [0.1.9] - 2023-07-27

- To integrate, directory name `app-packages` is not mandatory now. You can name as you like in your F360 script / add-in.

## [0.1.8] - 2023-07-26

- Follows the change of Fusion 360 2.0.16753 for Mac.
- Fix the issue that `python -m build --wheel` made a huge whl file.

## [0.1.7] - 2023-07-25

- Follows the change of High DPI behavior in Fusion 360 2.0.16753.

## [0.1.6] - 2023-07-24

- Fallback mode for Mac.
- Better test oracles / results for regression test.

## [0.1.5] - 2022-06-09

- The `pointer_offset_[xy]` becomes `pointer_offset_[xyz]` and the unit becomes centimeter.

## [0.1.4] - 2022-06-01

- `minimize_maximize()` fails in scaling screen (high resolution display). Now it just `set_focus()`.
- Sometimes RPA fails before clicking `Insert from my computer`. Now waits longer.

## [0.1.3] - 2022-05-20

- `pointer_offset_[xy]` has been added to cure the instability of DECAL command result.

## [0.1.2] - 2022-04-06

- Bug fix: Now it works fine while debugging.

## [0.1.1] - 2022-04-02

- Follows the update of Fusion 360, especially Python 3.9.7.

## [0.0.2] - 2021-07-21

- Bug fix: Now it works fine on non top-level components.

## [0.0.1] - 2021-07-09

- Initial release
