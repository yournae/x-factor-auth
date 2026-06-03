#!/usr/bin/env python3
"""
X Actions — Core X/Twitter API client.
All secrets from .env, no hardcoded creds.
"""
import requests
import json
import time
import random
import re
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from config.settings import (
    log, load_accounts, QID, FEATURES, BEARER_TOKEN_FALLBACK,
    MIN_DELAY_SECONDS, MAX_POSTS_PER_DAY, WARMUP_MESSAGES,
    REMOTE_VPS_HOST, REMOTE_VPS_USER, REMOTE_VPS_KEY_PATH,
    CLOAKBROWSER_URL, CLOAKBROWSER_PROFILE_ID,
)
from utils.helpers import (
    retry, sanitize_shell_arg, sanitize_tweet_text,
    parse_tweet_id, parse_user_handle, is_rate_limited,
)


class XActions:
    """
    X/Twitter automation client with multi-account rotation and XActions fallback.
    """
    
    def __init__(self):
        self.accounts = load_accounts()
        self.current_idx = 0
        self._bearer_cache = None
        
        if not self.accounts:
            log.error("❌ No X accounts configured in .env")
            raise ValueError("No X accounts configured. Copy .env.example to .env and add your credentials.")
        
        log.info(f"✅ Loaded {len(self.accounts)} account(s)")
    
    # ===================== HELPERS =====================
    
    def get_bearer(self) -> str:
        """Extract bearer token from x.com, with fallback."""
        if self._bearer_cache:
            return self._bearer_cache
        
        try:
            r = requests.get('https://x.com', headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            scripts = re.findall(r'src="(https://abs\.twimg\.com/responsive-web/client-web[^"]+\.js)"', r.text)
            for url in scripts[:5]:
                r2 = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                m = re.search(r'Bearer ([A-Za-z0-9%_=/+]+)', r2.text)
                if m:
                    self._bearer_cache = m.group(1)
                    return self._bearer_cache
        except Exception as e:
            log.warning(f"Could not extract bearer token: {e}")
        
        self._bearer_cache = BEARER_TOKEN_FALLBACK
        return self._bearer_cache
    
    def _headers(self, acc: Dict[str, Any]) -> Dict[str, str]:
        """Build request headers for account."""
        return {
            'authorization': f'Bearer {self.get_bearer()}',
            'x-csrf-token': acc['ct0'],
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': 'en',
            'cookie': f"auth_token={acc['auth_token']}; ct0={acc['ct0']}"
        }
    
    # ===================== ACCOUNT MANAGEMENT =====================
    
    def get_available_account(self) -> Dict[str, Any]:
        """Get next available account for a NEW garapan."""
        now = datetime.now()
        
        for i in range(len(self.accounts)):
            idx = (self.current_idx + i) % len(self.accounts)
            acc = self.accounts[idx]
            
            # Skip if rate-limited
            if acc['limited_until'] and now < acc['limited_until']:
                log.debug(f"⏭ {acc['name']} limited until {acc['limited_until'].strftime('%H:%M')}")
                continue
            
            # Skip if too soon since last post
            if acc['last_post']:
                elapsed = (now - acc['last_post']).total_seconds()
                if elapsed < MIN_DELAY_SECONDS:
                    wait = MIN_DELAY_SECONDS - elapsed
                    log.debug(f"⏳ {acc['name']} waiting {wait:.0f}s")
                    continue
            
            # Skip if hit daily soft limit
            if acc['posts_today'] >= MAX_POSTS_PER_DAY:
                log.debug(f"⏭ {acc['name']} hit {MAX_POSTS_PER_DAY} posts today")
                acc['limited_until'] = now + timedelta(hours=4)
                continue
            
            self.current_idx = (idx + 1) % len(self.accounts)
            return acc
        
        # All limited — find soonest reset
        soonest = min(
            (a['limited_until'] for a in self.accounts if a['limited_until']),
            default=None
        )
        if soonest:
            wait = (soonest - now).total_seconds()
            if wait > 0:
                log.info(f"⏳ All accounts limited. Waiting {wait:.0f}s for soonest reset...")
                time.sleep(min(wait + 5, 300))
                return self.get_available_account()
        
        # Fallback: use account with oldest last_post
        acc = min(self.accounts, key=lambda a: a['last_post'] or datetime.min)
        return acc
    
    def get_account_by_name(self, name: str) -> Dict[str, Any]:
        """Get specific account by name."""
        return next((a for a in self.accounts if a['name'] == name), self.accounts[0])
    
    def mark_success(self, acc: Dict[str, Any]):
        """Mark successful post."""
        acc['last_post'] = datetime.now()
        acc['posts_today'] += 1
        acc['warm'] = True
        log.info(f"✅ {acc['name']} post #{acc['posts_today']} OK")
    
    def mark_limited(self, acc: Dict[str, Any], hours: int = 2):
        """Mark account as rate-limited."""
        acc['limited_until'] = datetime.now() + timedelta(hours=hours)
        log.warning(f"🚫 {acc['name']} limited for {hours}h")
    
    def status(self) -> Dict[str, Any]:
        """Print and return status of all accounts."""
        result = {}
        for acc in self.accounts:
            lim = acc['limited_until'].strftime('%H:%M') if acc['limited_until'] else 'OK'
            last = acc['last_post'].strftime('%H:%M:%S') if acc['last_post'] else 'never'
            result[acc['name']] = {
                'posts_today': acc['posts_today'],
                'limited_until': lim,
                'last_post': last,
            }
            log.info(f"  {acc['name']}: posts={acc['posts_today']}, limited={lim}, last={last}")
        return result
    
    # ===================== XACTIONS FALLBACK =====================
    
    def xactions_available(self) -> bool:
        """Check if remote VPS with CloakBrowser is reachable."""
        if not REMOTE_VPS_HOST:
            return False
        
        key_path = REMOTE_VPS_KEY_PATH.replace('~', '/root')
        try:
            r = subprocess.run(
                ['ssh', '-i', key_path, '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=no',
                 f'{REMOTE_VPS_USER}@{REMOTE_VPS_HOST}', 'echo ok'],
                capture_output=True, text=True, timeout=10
            )
            return r.returncode == 0 and 'ok' in r.stdout
        except Exception:
            return False
    
    def xactions_fallback(self, action: str, url: Optional[str] = None, text: Optional[str] = None, acc_name: str = 'main') -> Dict[str, Any]:
        """
        Execute X action via CloakBrowser XActions (browser DOM click).
        Only runs if REMOTE_VPS_HOST is configured.
        """
        if not REMOTE_VPS_HOST:
            return {'error': 'xactions_not_configured', 'message': 'Set REMOTE_VPS_HOST in .env to enable browser fallback'}
        
        acc = self.get_account_by_name(acc_name)
        log.info(f"🌐 XActions fallback: {action} via {acc_name} (browser DOM)")
        
        # Sanitize all inputs
        safe_action = sanitize_shell_arg(action)
        safe_url = sanitize_shell_arg(url) if url else ''
        safe_text = sanitize_shell_arg(text) if text else ''
        
        key_path = REMOTE_VPS_KEY_PATH.replace('~', '/root')
        
        # Step 1: Login with account cookies
        login_cmd = [
            'ssh', '-i', key_path, '-o', 'StrictHostKeyChecking=no',
            f'{REMOTE_VPS_USER}@{REMOTE_VPS_HOST}',
            f'sudo docker exec cloakbrowser python3 /data/xactions-scripts/login_x.py '
            f'--auth-token "{acc["auth_token"]}" --ct0 "{acc["ct0"]}"'
        ]
        
        try:
            r = subprocess.run(login_cmd, capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                return {'error': 'xactions_login_failed', 'details': r.stderr[:200]}
        except subprocess.TimeoutExpired:
            return {'error': 'xactions_login_timeout'}
        
        # Step 2: Execute action
        cmd_parts = [
            'ssh', '-i', key_path, '-o', 'StrictHostKeyChecking=no',
            f'{REMOTE_VPS_USER}@{REMOTE_VPS_HOST}',
            f'sudo docker exec cloakbrowser python3 /data/xactions-scripts/xactions_v2.py {safe_action} "{safe_url}"'
        ]
        if safe_text:
            cmd_parts[-1] += f' "{safe_text}"'
        
        try:
            r = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=60)
            output = r.stdout.strip()
            
            if r.returncode != 0:
                return {'error': 'xactions_exec_failed', 'details': r.stderr[:200]}
            
            if 'SUCCESS' in output or 'OK' in output or 'success' in output.lower():
                log.info(f"✅ XActions {action} success via {acc_name}")
                return {'ok': True, 'method': 'xactions', 'account': acc_name}
            elif 'ALREADY' in output:
                log.info(f"ℹ️ XActions {action} already done via {acc_name}")
                return {'ok': True, 'method': 'xactions', 'account': acc_name, 'already': True}
            else:
                return {'error': 'xactions_unknown', 'output': output[:200], 'account': acc_name}
        
        except subprocess.TimeoutExpired:
            return {'error': 'xactions_timeout', 'account': acc_name}
    
    # ===================== API CALLS =====================
    
    @retry(max_attempts=3, base_delay=2.0)
    def _api_post(self, acc: Dict[str, Any], endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make API call with retry."""
        r = requests.post(
            f'https://x.com/i/api/graphql/{endpoint}',
            headers={**self._headers(acc), 'content-type': 'application/json'},
            data=json.dumps(payload),
            timeout=15
        )
        
        if r.status_code == 200:
            data = r.json()
            errors = data.get('errors', [])
            if errors:
                code = errors[0].get('code', 0)
                msg = errors[0].get('message', '')
                if code == 344:
                    self.mark_limited(acc, hours=2)
                    return {'error': 'rate_limited', 'code': 344, 'account': acc['name']}
                return {'error': msg, 'code': code, 'account': acc['name']}
            return {'ok': True, 'data': data, 'account': acc['name']}
        
        if r.status_code == 429:
            self.mark_limited(acc, hours=1)
            return {'error': 'rate_limited_429', 'account': acc['name']}
        
        if r.status_code in (226, 403):
            return {'error': 'anti_automation', 'code': r.status_code, 'account': acc['name']}
        
        return {'error': str(r.status_code), 'msg': r.text[:300], 'account': acc['name']}
    
    # ===================== READ ACTIONS =====================
    
    def user_lookup(self, username: str) -> Dict[str, Any]:
        """Look up user by screen name."""
        acc = self.accounts[0]
        username = parse_user_handle(username)
        
        try:
            r = requests.get(
                f'https://x.com/i/api/graphql/{QID["UserByScreenName"]}/UserByScreenName',
                params={
                    'variables': json.dumps({"screen_name": username, "withSafetyModeUserFields": True}),
                    'features': json.dumps(FEATURES)
                },
                headers=self._headers(acc)
            )
            if r.status_code == 200 and r.text:
                data = r.json()
                user = data.get('data', {}).get('user', {}).get('result', {}).get('legacy', {})
                rest_id = data.get('data', {}).get('user', {}).get('result', {}).get('rest_id', '')
                return {
                    'ok': True, 'id': rest_id, 'name': user.get('name'),
                    'screen_name': user.get('screen_name'),
                    'followers': user.get('followers_count'),
                    'following': user.get('friends_count'),
                    'statuses': user.get('statuses_count'),
                    'description': user.get('description', '')[:100]
                }
            return {'error': str(r.status_code), 'msg': r.text[:200]}
        except Exception as e:
            return {'error': 'exception', 'msg': str(e)[:200]}
    
    # ===================== WRITE ACTIONS =====================
    
    def like(self, tweet_id: str, acc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Like a tweet."""
        if not acc:
            acc = self.accounts[0]
        
        try:
            r = requests.post(
                f'https://x.com/i/api/graphql/{QID["FavoriteTweet"]}/FavoriteTweet',
                headers={**self._headers(acc), 'content-type': 'application/json'},
                data=json.dumps({'variables': {'tweet_id': str(tweet_id)}})
            )
            if r.status_code == 200:
                data = r.json()
                if not data.get('errors'):
                    return {'ok': True, 'id': tweet_id, 'account': acc['name']}
                code = data['errors'][0].get('code', 0)
                if code == 344:
                    self.mark_limited(acc)
                if code in (344, 226):
                    return self.xactions_fallback('like', f"https://x.com/i/status/{tweet_id}", acc_name=acc['name'])
                return {'error': data['errors'][0].get('message', ''), 'code': code, 'account': acc['name']}
            
            if r.status_code in (344, 226, 404, 405):
                log.warning(f"⚠️ {acc['name']} like API failed ({r.status_code}), trying XActions...")
                return self.xactions_fallback('like', f"https://x.com/i/status/{tweet_id}", acc_name=acc['name'])
            
            return {'error': str(r.status_code), 'msg': r.text[:300], 'account': acc['name']}
        except Exception as e:
            return {'error': 'exception', 'msg': str(e)[:200], 'account': acc['name']}
    
    def retweet(self, tweet_id: str, acc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retweet."""
        if not acc:
            acc = self.accounts[0]
        
        result = self._api_post(acc, QID['CreateRetweet'], {
            'variables': {'tweet_id': str(tweet_id), 'dark_request': False},
            'features': FEATURES
        })
        
        if result.get('ok'):
            self.mark_success(acc)
            return result
        
        if result.get('code') in (344, 226) or result.get('error') in ('rate_limited', 'anti_automation', 'rate_limited_429'):
            log.warning(f"⚠️ {acc['name']} RT API failed, trying XActions...")
            return self.xactions_fallback('retweet', f"https://x.com/i/status/{tweet_id}", acc_name=acc['name'])
        
        return result
    
    def post(self, text: str, acc: Optional[Dict[str, Any]] = None, use_xactions: bool = True) -> Dict[str, Any]:
        """Post a tweet."""
        if not acc:
            acc = self.accounts[0]
        
        text = sanitize_tweet_text(text)
        
        # Warm-up if needed
        if not acc['warm']:
            log.info(f"🔥 Warming up {acc['name']}...")
            warmup = random.choice(WARMUP_MESSAGES)
            r = self._api_post(acc, QID['CreateTweet'], {
                'variables': {'tweet_text': warmup, 'dark_request': False},
                'features': FEATURES
            })
            if r.get('ok'):
                log.info(f"🔥 Warm-up posted: {warmup}")
                acc['warm'] = True
                time.sleep(random.randint(30, 60))
        
        result = self._api_post(acc, QID['CreateTweet'], {
            'variables': {'tweet_text': text, 'dark_request': False},
            'features': FEATURES
        })
        
        if result.get('ok'):
            tid = result['data'].get('data', {}).get('create_tweet', {}).get('tweet_results', {}).get('result', {}).get('rest_id')
            self.mark_success(acc)
            return {'ok': True, 'tweet_id': tid, 'account': acc['name']}
        
        if use_xactions and result.get('code') in (344, 226):
            log.warning(f"⚠️ {acc['name']} post API failed, trying XActions...")
            return self.xactions_fallback('post', None, text=text, acc_name=acc['name'])
        
        return result
    
    def quote_tweet(self, tweet_id: str, text: str, acc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Quote tweet."""
        if not acc:
            acc = self.accounts[0]
        
        text = sanitize_tweet_text(text)
        
        result = self._api_post(acc, QID['CreateTweet'], {
            'variables': {
                'tweet_text': text,
                'attachment_url': f'https://x.com/i/status/{tweet_id}',
                'dark_request': False
            },
            'features': FEATURES
        })
        
        if result.get('ok'):
            tid = result['data'].get('data', {}).get('create_tweet', {}).get('tweet_results', {}).get('result', {}).get('rest_id')
            self.mark_success(acc)
            return {'ok': True, 'tweet_id': tid, 'account': acc['name']}
        
        if result.get('code') in (344, 226):
            log.warning(f"⚠️ {acc['name']} quote API failed, trying XActions...")
            return self.xactions_fallback('quote', f"https://x.com/i/status/{tweet_id}", text=text, acc_name=acc['name'])
        
        return result
    
    def reply(self, tweet_id: str, text: str, acc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Reply to a tweet."""
        if not acc:
            acc = self.accounts[0]
        
        text = sanitize_tweet_text(text)
        
        result = self._api_post(acc, QID['CreateTweet'], {
            'variables': {
                'tweet_text': text,
                'reply': {'in_reply_to_tweet_id': str(tweet_id)},
                'dark_request': False
            },
            'features': FEATURES
        })
        
        if result.get('ok'):
            tid = result['data'].get('data', {}).get('create_tweet', {}).get('tweet_results', {}).get('result', {}).get('rest_id')
            self.mark_success(acc)
            return {'ok': True, 'tweet_id': tid, 'account': acc['name']}
        
        if result.get('code') in (344, 226):
            log.warning(f"⚠️ {acc['name']} reply API failed, trying XActions...")
            return self.xactions_fallback('reply', f"https://x.com/i/status/{tweet_id}", text=text, acc_name=acc['name'])
        
        return result
    
    def follow(self, user_id: str, acc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Follow a user by ID."""
        if not acc:
            acc = self.accounts[0]
        
        try:
            r = requests.post(
                'https://x.com/i/api/1.1/friendships/create.json',
                data={'user_id': user_id},
                headers={**self._headers(acc), 'content-type': 'application/x-www-form-urlencoded'}
            )
            if r.status_code == 200:
                d = r.json()
                return {'ok': True, 'screen_name': d.get('screen_name'), 'following': d.get('following'), 'account': acc['name']}
            
            if r.status_code in (403, 429, 404, 405):
                log.warning(f"⚠️ {acc['name']} follow API failed ({r.status_code}), trying XActions...")
                info = self.user_lookup_by_id(user_id)
                if info.get('screen_name'):
                    return self.xactions_fallback('follow', f"https://x.com/{info['screen_name']}", acc_name=acc['name'])
            
            return {'error': str(r.status_code), 'msg': r.text[:200], 'account': acc['name']}
        except Exception as e:
            return {'error': 'exception', 'msg': str(e)[:200], 'account': acc['name']}
    
    def user_lookup_by_id(self, user_id: str) -> Dict[str, Any]:
        """Look up user by ID."""
        acc = self.accounts[0]
        try:
            r = requests.get(
                'https://x.com/i/api/1.1/users/show.json',
                params={'user_id': user_id},
                headers=self._headers(acc)
            )
            if r.status_code == 200:
                d = r.json()
                return {'ok': True, 'id': d.get('id_str'), 'screen_name': d.get('screen_name'), 'name': d.get('name')}
            return {'error': str(r.status_code)}
        except Exception as e:
            return {'error': 'exception', 'msg': str(e)[:200]}
    
    # ===================== AIRDROP HELPERS =====================
    
    def garap_full(self, handle: str, tweet_id: Optional[str] = None, acc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Full airdrop garapan: follow + like + RT + quote.
        ALL on the SAME account.
        """
        if not acc:
            acc = self.get_available_account()
        
        handle = parse_user_handle(handle)
        log.info(f"🎯 Starting garap_full for @{handle} with account {acc['name']}")
        
        results = {'handle': handle, 'account': acc['name'], 'tasks': {}}
        
        # Follow
        r = self.follow(handle, acc=acc)
        results['tasks']['follow'] = '✅' if r.get('ok') else f"❌ {r.get('error', '?')}"
        if r.get('method') == 'xactions':
            results['tasks']['follow'] += ' (browser)'
        
        if tweet_id:
            tid = parse_tweet_id(tweet_id)
            if not tid:
                results['tasks']['like'] = '❌ invalid_tweet_id'
                results['tasks']['retweet'] = '❌ invalid_tweet_id'
                results['tasks']['quote'] = '❌ invalid_tweet_id'
                return results
            
            time.sleep(random.randint(5, 15))
            
            # Like
            r = self.like(tid, acc=acc)
            results['tasks']['like'] = '✅' if r.get('ok') else f"❌ {r.get('error', '?')}"
            if r.get('method') == 'xactions':
                results['tasks']['like'] += ' (browser)'
            
            time.sleep(random.randint(5, 15))
            
            # Retweet
            r = self.retweet(tid, acc=acc)
            results['tasks']['retweet'] = '✅' if r.get('ok') else f"❌ {r.get('error', '?')}"
            if r.get('method') == 'xactions':
                results['tasks']['retweet'] += ' (browser)'
            
            time.sleep(random.randint(30, 90))
            
            # Quote
            r = self.quote_tweet(tid, '', acc=acc)
            results['tasks']['quote'] = '✅' if r.get('ok') else f"❌ {r.get('error', '?')}"
            if r.get('method') == 'xactions':
                results['tasks']['quote'] += ' (browser)'
            if r.get('ok'):
                results['quote_tweet_id'] = r.get('tweet_id')
                results['quote_account'] = r.get('account')
        
        return results
