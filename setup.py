"""
py2app build config.
Run via:  python setup.py py2app
(build.sh handles the venv + this call automatically)
"""
from setuptools import setup

APP     = ["run.py"]
OPTIONS = {
    "argv_emulation": False,
    "packages": ["rumps", "AppKit", "Foundation"],
    "plist": {
        "CFBundleName":             "LidLight",
        "CFBundleIdentifier":       "com.lidlight.LidLight",
        "CFBundleShortVersionString": "1.0",
        "LSUIElement":              True,    # hide from Dock
        "NSHighResolutionCapable":  True,
    },
}

setup(
    name="LidLight",
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
