#!/usr/bin/env python3
"""
CDP JS injection — execute JS in CloakBrowser tab.
"""
import json
import websocket
import urllib.request
import sys

from config.settings import log, CLOAKBROWSER_URL, CLOAKBROWSER_PROFILE_ID


def inject_js(profile_id: str, js_file: str = None, js_code: str = None):
    """Inject and execute JavaScript in CloakBrowser tab."""
    if not js_file and not js_code:
        log.error("Usage: inject.py <profile_id> <js_file> OR inject.py <profile_id> -e <js_code>")
        return None
    
    # Get tabs
    try:
        tabs_url = f"{CLOAKBROWSER_URL}/api/profiles/{profile_id}/cdp/json/list"
        tabs = json.loads(urllib.request.urlopen(tabs_url, timeout=10).read())
    except Exception as e:
        log.error(f"Failed to get tabs: {e}")
        return None
    
    # Find suitable tab (skip service workers)
    ws_url = None
    for t in tabs:
        if "sw.js" not in t.get("url", ""):
            ws_url = t["webSocketDebuggerUrl"]
            break
    
    if not ws_url:
        log.error("No suitable tab found")
        return None
    
    # Load JS code from file
    if js_file:
        try:
            with open(js_file) as f:
                js_code = f.read()
        except Exception as e:
            log.error(f"Failed to read JS file: {e}")
            return None
    
    # Execute via WebSocket
    try:
        ws = websocket.create_connection(ws_url, timeout=30)
        ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code, "returnByValue": True}
        }))
        
        for _ in range(50):
            r = json.loads(ws.recv())
            if r.get("id") == 1:
                result = r.get("result", {}).get("result", {}).get("value", "?")
                ws.close()
                return result
        
        ws.close()
        return None
    
    except Exception as e:
        log.error(f"WebSocket error: {e}")
        return None


if __name__ == '__main__':
    profile_id = sys.argv[1] if len(sys.argv) > 1 else CLOAKBROWSER_PROFILE_ID
    js_file = sys.argv[2] if len(sys.argv) > 2 else None
    js_code = sys.argv[3] if len(sys.argv) > 3 else None
    
    result = inject_js(profile_id, js_file, js_code)
    if result:
        print(result)
