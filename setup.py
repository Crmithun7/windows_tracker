from setuptools import setup, find_packages

setup(
    name="ENYARD",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "pywinctl",
        "pyautogui",
        "fastapi",
        "uvicorn",
    ],
    entry_points={
        "console_scripts": [
            "windows_tracker = ENYARD.core:monitor_active_window"
        ]
    }
)
