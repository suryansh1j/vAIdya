"""
Startup script for vAIdya.
Run this instead of using uvicorn directly:  python run.py

On startup it prints a clickable local URL and opens the app in Chrome.
Set NO_BROWSER=1 to skip auto-opening the browser.
"""
import os
import threading
import webbrowser

import uvicorn


def find_chrome():
    """Return the path to Chrome if installed in a common location, else None."""
    candidates = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    ]
    return next((p for p in candidates if p and os.path.isfile(p)), None)


def open_browser(url):
    """Open the app in Chrome; fall back to the OS default browser.

    Never let a browser-launch failure crash server startup.
    """
    try:
        chrome = find_chrome()
        if chrome:
            webbrowser.register("vaidya-chrome", None, webbrowser.BackgroundBrowser(chrome))
            webbrowser.get("vaidya-chrome").open_new(url)
        else:
            webbrowser.open_new(url)
    except Exception:
        pass


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    # uvicorn logs the bind address (e.g. 0.0.0.0), which browsers can't open.
    # Print a clickable local URL so Ctrl/Cmd+click works in the terminal.
    display_host = "localhost" if host in ("0.0.0.0", "127.0.0.1", "") else host
    url = f"http://{display_host}:{port}"
    print(f"\n  vAIdya is running ->  {url}\n")

    if os.getenv("NO_BROWSER", "").lower() not in ("1", "true", "yes"):
        # Delay slightly so the server is accepting connections when Chrome opens.
        threading.Timer(1.5, open_browser, args=(url,)).start()

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )
