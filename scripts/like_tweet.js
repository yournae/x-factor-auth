// Like a tweet — run after navigating to the tweet page
// DOM click-based action for CloakBrowser
(function() {
    var unlike = document.querySelector('[data-testid="unlike"]');
    if (unlike && unlike.offsetParent !== null) {
        return 'ALREADY_LIKED';
    }
    
    var like = document.querySelector('[data-testid="like"]');
    if (like) {
        like.click();
        return 'LIKED';
    }
    
    return 'NO_LIKE_BUTTON';
})()
