#!/usr/bin/env python3
"""
Login to X via cookie injection in CloakBrowser.
"""
import json
import websocket
import urllib.request
import sys
import time

from config.settings import log, CLOAKBROWSER_URL, CLOAKBROWSER_PROFILE_ID


def login_x(profile_id: str, auth_token: str, ct0: str) -> bool:
    """
    Inject cookies into CloakBrowser and navigate to x.com.
    
    Returns True on success.
    """
    try:
        # Get tabs
        tabs_url = f"{CLOAKBROWSER_URL}/api/profiles/{profile_id}/cdp/json/list"
        tabs = json.loads(urllib.request.urlopen(tabs_url, timeout=10).read())
        
        if not tabs:
            log.error("No tabs found")
            return False
        
        ws_url = tabs[0]["webSocketDebuggerUrl"]
        ws = websocket.create_connection(ws_url, timeout=30)
        
        # Enable network
        ws.send(json.dumps({"id": 1, "method": "Network.enable", "params": {}}))
        ws.recv()
        
        # Set cookies
        for cookie in [
            {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/", "httpOnly": True, "secure": True},
            {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/", "httpOnly": True, "secure": True},
        ]:
            ws.send(json.dumps({"id": 2, "method": "Network.setCookie", "params": cookie}))
            ws.recv()
        
        # Navigate to x.com
        ws.send(json.dumps({"id": 3, "method": "Page.enable", "params": {}}))
        ws.recv()
        ws.send(json.dumps({"id": 4, "method": "Page.navigate", "params": {"url": "https://x.com/home"}}))
        ws.recv()
        
        # Wait for page load
        time.sleep(8)
        
        # Check title
        ws.send(json.dumps({
            "id": 5,
            "method": "Runtime.evaluate",
            "params": {"expression": "document.title", "returnByValue": True}
        }))
        
        for _ in range(50):
            r = json.loads(ws.recv())
            if r.get("id") == 5:
                title = r.get("result", {}).get("result", {}).get("value", "?")
                ws.close()
                log.info(f"Page title: {title}")
                return "x" in title.lower() or "twitter" in title.lower()
        
        ws.close()
        return False
    
    except Exception as e:
        log.error(f"Login failed: {e}")
        return False


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: login_x.py <profile_id> <auth_token> <ct0>")
        print("  OR: login_x.py <profile_id>  (reads from .env)")
        sys.exit(1)
    
    profile_id = sys.argv[1]
    
    # If only profile_id provided, read from env
    if len(sys.argv) == 2:
        from config.settings import load_accounts
        accounts = load_accounts()
        if not accounts:
            log.error("No accounts in .env")
            sys.exit(1)
        acc = accounts[0]
        auth_token = acc['auth_token']
        ct0 = acc['ct0']
    else:
        auth_token = sys.argv[2]
        ct0 = sys.argv[3] if len(sys.argv) > 3 else ""
    
    success = login_x(profile_id, auth_token, ct0)
    print("X LOGIN OK" if success else "X LOGIN FAILED")
