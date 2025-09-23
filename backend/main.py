import pywinctl as pwc
import pyautogui
import os
import time
import re
import threading
from queue import Queue
from folder import folders_to_monitor  # comes from folder.py

# ---------- NEW: helpers to resolve + display folders ----------
def resolve_folder(path: str) -> str:
    """Expand ~ and %VARS%, return absolute normalized path."""
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))

def display_folders(folders):
    print("\n[folder.py] Folders to monitor:")
    for i, f in enumerate(folders, 1):
        print(f"  {i}. {f}")
    print()  # blank line
# ---------------------------------------------------------------

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def get_active_window_title():
    win = pwc.getActiveWindow()
    if win:
        return sanitize_filename(win.title)
    return "UnknownWindow"

def screenshot_saver(folder, task_queue, stop_event):
    log_file = os.path.join(folder, "log.txt")
    os.makedirs(folder, exist_ok=True)

    while not stop_event.is_set():
        try:
            filepath = task_queue.get(timeout=1)
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(filepath + "\n")
            print(f"[{folder}] Screenshot saved: {filepath}")
            task_queue.task_done()
        except Exception:
            # Timeout or other error, ignore and continue loop
            pass

def monitor_active_window(folders):
    last_windows = {folder: None for folder in folders}
    queues = {folder: Queue() for folder in folders}
    stop_events = {folder: threading.Event() for folder in folders}
    
    # Start saver threads, one per folder
    threads = []
    for folder in folders:
        t = threading.Thread(target=screenshot_saver, args=(folder, queues[folder], stop_events[folder]), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
            current_window = get_active_window_title()
            for folder in folders:
                if current_window != last_windows[folder] and current_window != "":
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{current_window}.png"
                    filepath = os.path.join(folder, filename)
                    queues[folder].put(filepath)
                    last_windows[folder] = current_window
    except KeyboardInterrupt:
        # Signal threads to stop
        for ev in stop_events.values():
            ev.set()
        # Wait for all threads to finish current tasks
        for q in queues.values():
            q.join()
        print("Stopped monitoring.")

if __name__ == "__main__":
    # Resolve and display folder list fetched from folder.py
    folders_resolved = [resolve_folder(p) for p in folders_to_monitor]
    display_folders(folders_resolved)

    # Start monitoring using the resolved paths
    monitor_active_window(folders_resolved)
