#!/usr/bin/env python3
"""
Configuration module — loads from .env, no secrets in code.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / '.env')

# === Logging Setup ===
def setup_logging(log_level: str = 'INFO') -> logging.Logger:
    """Configure structured logging."""
    logger = logging.getLogger('x_actions')
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s %(message)s',
        datefmt='%H:%M:%S'
    ))
    
    # File handler (rotating)
    from logging.handlers import RotatingFileHandler
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_dir / 'x_actions.log',
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s: %(message)s'
    ))
    
    logger.addHandler(console)
    logger.addHandler(file_handler)
    
    return logger

log = setup_logging()

# === Account Configuration ===
def load_accounts() -> list:
    """Load X accounts from env vars — filter out missing creds."""
    accounts = []
    
    # Main account
    auth_token = os.getenv('X_AUTH_TOKEN')
    ct0 = os.getenv('X_CT0')
    if auth_token and ct0:
        accounts.append({
            'name': 'main',
            'auth_token': auth_token,
            'ct0': ct0,
            'limited_until': None,
            'last_post': None,
            'posts_today': 0,
            'warm': False,
        })
    
    # Additional accounts (X2_, X3_, etc.)
    for i in range(2, 10):
        prefix = f'X{i}_'
        auth_token = os.getenv(f'{prefix}AUTH_TOKEN')
        ct0 = os.getenv(f'{prefix}CT0')
        if auth_token and ct0:
            accounts.append({
                'name': f'x{i}',
                'auth_token': auth_token,
                'ct0': ct0,
                'limited_until': None,
                'last_post': None,
                'posts_today': 0,
                'warm': False,
            })
    
    return accounts

# === Rate Limit Config ===
MIN_DELAY_SECONDS = int(os.getenv('MIN_DELAY_SECONDS', '150'))
MAX_POSTS_PER_DAY = int(os.getenv('MAX_POSTS_PER_DAY', '25'))
MAX_RETWEETS_PER_DAY = int(os.getenv('MAX_RETWEETS_PER_DAY', '50'))
MAX_LIKES_PER_DAY = int(os.getenv('MAX_LIKES_PER_DAY', '100'))

# === CloakBrowser Config ===
CLOAKBROWSER_URL = os.getenv('CLOAKBROWSER_URL', 'http://localhost:8080')
CLOAKBROWSER_PROFILE_ID = os.getenv('CLOAKBROWSER_PROFILE_ID', '')

# === Remote VPS Config (for XActions fallback) ===
REMOTE_VPS_HOST = os.getenv('REMOTE_VPS_HOST', '')
REMOTE_VPS_USER = os.getenv('REMOTE_VPS_USER', 'root')
REMOTE_VPS_KEY_PATH = os.getenv('REMOTE_VPS_KEY_PATH', '~/.ssh/id_rsa')

# === GraphQL Query IDs ===
# Updated periodically — move to config if these change frequently
QID = {
    'CreateTweet': 'H-t2v_HvFR07ZBP9aOeKoA',
    'FavoriteTweet': 'lI07N6Otwv1PhnEgXILM7A',
    'UnfavoriteTweet': 'ZYKSe-w7KEslx3JhSIk5LA',
    'CreateRetweet': 'mbRO74GrOvSfRcJnlMapnQ',
    'DeleteRetweet': 'ZyZigVsNiFO6v1dEks1eWg',
    'UserByScreenName': 'IGgvgiOx4QZndDHuD3x9TQ',
    'HomeTimeline': '7zlnp2TxC044W4C1ZUJMHw',
    'SearchTimeline': 'Yw6L66Pw54NHKuq4Dp7b4Q',
}

# === GraphQL Features ===
FEATURES = {
    'rweb_tipjar_consumption_enabled': True,
    'responsive_web_graphql_exclude_directive_enabled': True,
    'verified_phone_label_enabled': False,
    'responsive_web_graphql_timeline_navigation_enabled': True,
}

# === Bearer Token ===
# Auto-extracted from x.com, fallback to known default
BEARER_TOKEN_FALLBACK = 'AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA'

# === Warmup Messages ===
WARMUP_MESSAGES = [
    "gm ☀️", "wagmi 🤝", "building in silence 🔨",
    "on-chain vibes today", "web3 never sleeps 💤",
    "bullish on builders 📈", "early bird gets the airdrop 🐦",
]

# === Airdrop Templates ===
AIRDROP_QUOTE_TEMPLATES = [
    "Excited for this! 🚀 {handle} is building something amazing",
    "Bullish on {handle} 🔥 Early adopters always win",
    "Don't sleep on {handle} 💤 The future is here",
    "Just joined the {handle} community 🤝 Are you in?",
    "{handle} caught my eye 👀 Big things coming",
]

AIRDROP_REPLY_TEMPLATES = [
    "Great project! Looking forward to the launch 🚀",
    "This is going to be huge! Count me in 🔥",
    "Amazing work by the team! Bullish 📈",
    "Early supporters always win. Let's go! 🤝",
    "The future of web3 right here 👀",
]
