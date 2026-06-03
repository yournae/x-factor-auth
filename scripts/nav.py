#!/usr/bin/env python3
"""
Navigate CloakBrowser to URL.
"""
import json
import websocket
import urllib.request
import sys
import time

from config.settings import log, CLOAKBROWSER_URL, CLOAKBROWSER_PROFILE_ID


def navigate(profile_id: str, url: str) -> str:
    """Navigate to URL and return page title."""
    try:
        tabs_url = f"{CLOAKBROWSER_URL}/api/profiles/{profile_id}/cdp/json/list"
        tabs = json.loads(urllib.request.urlopen(tabs_url, timeout=10).read())
        
        if not tabs:
            log.error("No tabs found")
            return None
        
        ws_url = tabs[0]["webSocketDebuggerUrl"]
        ws = websocket.create_connection(ws_url, timeout=30)
        
        # Enable page
        ws.send(json.dumps({"id": 1, "method": "Page.enable", "params": {}}))
        ws.recv()
        
        # Navigate
        ws.send(json.dumps({"id": 2, "method": "Page.navigate", "params": {"url": url}}))
        ws.recv()
        
        # Wait for load
        time.sleep(5)
        
        # Get title
        ws.send(json.dumps({
            "id": 3,
            "method": "Runtime.evaluate",
            "params": {"expression": "document.title", "returnByValue": True}
        }))
        
        for _ in range(50):
            r = json.loads(ws.recv())
            if r.get("id") == 3:
                title = r.get("result", {}).get("result", {}).get("value", "?")
                ws.close()
                return title
        
        ws.close()
        return None
    
    except Exception as e:
        log.error(f"Navigation failed: {e}")
        return None


if __name__ == '__main__':
    profile_id = sys.argv[1] if len(sys.argv) > 1 else CLOAKBROWSER_PROFILE_ID
    url = sys.argv[2] if len(sys.argv) > 2 else "https://x.com"
    
    title = navigate(profile_id, url)
    print(title if title else "Navigation failed")
