"""Post a real CoreGraphics mouse click at screen coordinates.

Needed because Draft Dominator's custom (Xojo-style) UI ignores System Events
synthetic clicks. Used only to drive the provider's own app during the
FBG horizon dynamic selector trace. Read-only with respect to the repository.

Usage: ui_click_claude_v1.py <x> <y> [--move-only]
"""
from __future__ import annotations

import ctypes
import ctypes.util
import sys
import time

K_MOVED, K_DOWN, K_UP = 5, 1, 2
K_LEFT_BUTTON = 0
K_HID_TAP = 0


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


def _libs():
    cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
    lib = ctypes.util.find_library("CoreGraphics") or ctypes.util.find_library(
        "ApplicationServices"
    )
    cg = ctypes.cdll.LoadLibrary(lib)
    cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p
    cg.CGEventCreateMouseEvent.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        CGPoint,
        ctypes.c_uint32,
    ]
    cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
    cf.CFRelease.argtypes = [ctypes.c_void_p]
    return cf, cg


def post(cf, cg, event_type: int, x: float, y: float) -> None:
    event = cg.CGEventCreateMouseEvent(None, event_type, CGPoint(x, y), K_LEFT_BUTTON)
    cg.CGEventPost(K_HID_TAP, event)
    cf.CFRelease(event)


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: ui_click_claude_v1.py <x> <y> [--move-only]", file=sys.stderr)
        return 2
    x, y = float(sys.argv[1]), float(sys.argv[2])
    cf, cg = _libs()
    post(cf, cg, K_MOVED, x, y)
    time.sleep(0.12)
    if "--move-only" not in sys.argv:
        post(cf, cg, K_DOWN, x, y)
        time.sleep(0.09)
        post(cf, cg, K_UP, x, y)
    print(f"clicked {x},{y}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
