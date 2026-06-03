# X Actions 🐦

X/Twitter automation toolkit — API-based + browser-based (CDP).

## Features

**API Mode** (`x_actions.py`):
- Like tweets
- Retweet / Quote tweet
- Follow users
- Post tweets
- Multi-account rotation
- Auto-retry on rate limits
- Exponential backoff

**Browser Mode** (`scripts/`):
- CDP injection via CloakBrowser
- DOM click-based actions (bypasses API limits)
- Works when API returns 344/226 errors

## Setup

```bash
# 1. Clone
git clone <repo>
cd x-actions

# 2. Install deps
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env with your X cookies

# 4. Run
python3 cli.py status
```

## Getting X Cookies

1. Open x.com in browser
2. Login → F12 → Application → Cookies → x.com
3. Copy `auth_token` and `ct0` values
4. Paste into `.env`

## API vs Browser

| Feature | API (`x_actions.py`) | Browser (`scripts/`) |
|---|---|---|
| Speed | Fast (~1s) | Slow (~3-5s) |
| Daily limit | 344 actions/day | No limit |
| Anti-bot | Can get 226/344 | Bypasses via DOM |
| Setup | Cookies only | CloakBrowser needed |

**Recommendation**: Use API for speed, switch to browser when hitting limits.

## Files

```
x_actions.py        # Main API automation module
cli.py              # Command-line interface
config/
    settings.py     # Configuration (loads from .env)
utils/
    helpers.py      # Retry, sanitization, helpers
scripts/
    inject.py       # CDP injection helper
    login_x.py      # Cookie-based X login via CDP
    nav.py          # Navigation helper
    follow_user.js  # Follow user action
    retweet_tweet.js # Retweet action
    like_tweet.js   # Like action
    quote_tweet.js  # Quote tweet action
```

## Usage Examples

```python
from x_actions import XActions

client = XActions()

# Like a tweet
client.like("2056799898205368350")

# Retweet
client.retweet("2056799898205368350")

# Follow user (needs user ID, not handle)
client.follow("2057327940183232512")

# Post tweet
client.post("Hello from X Actions! 🚀")

# Full airdrop garapan
client.garap_full("@ProjectX", "2056799898205368350")
```

## Security

- All secrets in `.env` (gitignored)
- No hardcoded credentials
- Input sanitization on all user inputs
- Shell argument escaping
- Proper logging with rotation

## Notes

- Cookies expire after ~2 weeks — refresh from browser
- `auth_token` and `ct0` are session-bound
- Don't mix actions across accounts in one session
- Browser mode needs CloakBrowser running with a profile
