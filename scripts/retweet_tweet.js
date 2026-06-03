// Retweet a tweet — run after navigating to the tweet page
// DOM click-based action for CloakBrowser
// Handles the two-step retweet flow (click → confirm)
(function() {
    // Check if already retweeted
    var unretweet = document.querySelector('[data-testid="unretweet"]');
    if (unretweet && unretweet.offsetParent !== null) {
        return 'ALREADY_RETWEETED';
    }
    
    var retweet = document.querySelector('[data-testid="retweet"]');
    if (retweet) {
        retweet.click();
        
        // Wait for confirm button to appear, then click
        // Use MutationObserver for reliable DOM detection
        return new Promise(function(resolve) {
            setTimeout(function() {
                var confirm = document.querySelector('[data-testid="retweetConfirm"]');
                if (confirm) {
                    confirm.click();
                    resolve('RETWEETED');
                } else {
                    resolve('RETWEET_MENU_CLICKED_NO_CONFIRM');
                }
            }, 1500);
        });
    }
    
    return 'NO_RETWEET_BUTTON';
})()
