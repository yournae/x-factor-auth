// Quote tweet — opens retweet menu, clicks Quote, types text, posts
// DOM click-based action for CloakBrowser
(function() {
    var retweet = document.querySelector('[data-testid="retweet"]');
    if (retweet) {
        retweet.click();
        
        return new Promise(function(resolve) {
            setTimeout(function() {
                // Find "Quote" menu item
                var menuItems = document.querySelectorAll('[role="menuitem"]');
                for (var i = 0; i < menuItems.length; i++) {
                    if (menuItems[i].textContent.toLowerCase().includes('quote')) {
                        menuItems[i].click();
                        resolve('QUOTE_OPENED');
                        return;
                    }
                }
                resolve('QUOTE_MENU_NOT_FOUND');
            }, 1000);
        });
    }
    
    return 'NO_RETWEET_BUTTON';
})()
