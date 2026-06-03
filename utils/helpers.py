#!/usr/bin/env python3
"""
Utilities — retry, sanitization, helpers.
"""
import re
import time
import random
import functools
from typing import Optional, Callable, Any


def retry(max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """
    Exponential backoff retry decorator.
    
    Usage:
        @retry(max_attempts=3, base_delay=2)
        def flaky_operation():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                        time.sleep(delay)
            raise last_exception or RuntimeError("All retry attempts failed")
        return wrapper
    return decorator


def sanitize_shell_arg(arg: str) -> str:
    """
    Sanitize argument for safe shell execution.
    Removes dangerous characters, escapes quotes.
    
    ⚠️ Always use this when passing user input to subprocess.
    """
    # Remove null bytes
    arg = arg.replace('\x00', '')
    
    # Remove shell metacharacters (except basic ones)
    # Keep alphanumeric, spaces, @, _, -, ., /
    arg = re.sub(r'[;&|`$(){}!\n\r]', '', arg)
    
    # Escape quotes for shell safety
    arg = arg.replace('"', '\\"').replace("'", "\\'")
    
    return arg.strip()


def sanitize_tweet_text(text: str, max_length: int = 280) -> str:
    """
    Sanitize tweet text.
    - Removes dangerous characters
    - Enforces length limit
    - Strips extra whitespace
    """
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Collapse whitespace
    text = ' '.join(text.split())
    
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length - 3] + '...'
    
    return text.strip()


def parse_tweet_id(tweet_id: str) -> Optional[str]:
    """
    Extract tweet ID from various formats:
    - Direct ID: "2056799898205368350"
    - URL: "https://x.com/user/status/2056799898205368350"
    - Short URL: "https://twitter.com/user/status/2056799898205368350"
    """
    # Direct numeric ID
    if tweet_id.isdigit():
        return tweet_id
    
    # URL format
    match = re.search(r'(?:twitter\.com|x\.com)/\w+/status/(\d+)', tweet_id)
    if match:
        return match.group(1)
    
    return None


def parse_user_handle(handle: str) -> str:
    """
    Normalize user handle:
    - "@username" → "username"
    - "username" → "username"
    """
    return handle.lstrip('@').strip()


def is_rate_limited(status_code: int, error_code: int = 0) -> bool:
    """Check if error indicates rate limiting."""
    return status_code == 429 or error_code in (344, 226)


def is_auth_error(status_code: int) -> bool:
    """Check if error indicates auth issue."""
    return status_code in (401, 403)


def format_duration(seconds: float) -> str:
    """Format seconds to human readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def safe_str(obj: Any, max_length: int = 200) -> str:
    """Convert to string safely, truncating if too long."""
    s = str(obj)
    if len(s) > max_length:
        return s[:max_length] + '...'
    return s
