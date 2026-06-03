#!/usr/bin/env python3
"""
CLI interface for X Actions.
"""
import sys
import json
from x_actions import XActions


def main():
    if len(sys.argv) < 2:
        print("X/Twitter Automation — Secure Edition")
        print()
        print("Commands:")
        print("  status                          - Account status")
        print("  user @handle                    - Look up user")
        print("  like <tweet_id>                 - Like")
        print("  retweet <tweet_id>              - Retweet")
        print("  post <text>                     - Post")
        print("  quote <tweet_id> <text>         - Quote tweet")
        print("  reply <tweet_id> <text>         - Reply")
        print("  follow <user_id>                - Follow by ID")
        print("  garap <@handle> [tweet_id]      - Full airdrop garapan")
        print("  xactions_check                  - Check XActions availability")
        sys.exit(0)
    
    try:
        client = XActions()
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'status':
        print(json.dumps(client.status(), indent=2))
    
    elif cmd == 'user':
        print(json.dumps(client.user_lookup(sys.argv[2]), indent=2))
    
    elif cmd == 'like':
        print(json.dumps(client.like(sys.argv[2]), indent=2))
    
    elif cmd == 'retweet':
        print(json.dumps(client.retweet(sys.argv[2]), indent=2))
    
    elif cmd == 'post':
        print(json.dumps(client.post(sys.argv[2]), indent=2))
    
    elif cmd == 'quote':
        print(json.dumps(client.quote_tweet(sys.argv[2], sys.argv[3]), indent=2))
    
    elif cmd == 'reply':
        print(json.dumps(client.reply(sys.argv[2], sys.argv[3]), indent=2))
    
    elif cmd == 'follow':
        print(json.dumps(client.follow(sys.argv[2]), indent=2))
    
    elif cmd == 'garap':
        handle = sys.argv[2]
        tweet_id = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(client.garap_full(handle, tweet_id), indent=2))
    
    elif cmd == 'xactions_check':
        available = client.xactions_available()
        print(f"XActions available: {available}")
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == '__main__':
    main()
