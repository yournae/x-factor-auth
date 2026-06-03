// Follow a user on X — run after navigating to their profile page
// DOM click-based action for CloakBrowser
(function() {
    // Check if already following
    var unfollow = document.querySelector('[data-testid$="-unfollow"]');
    if (unfollow && unfollow.offsetParent !== null) {
        return 'ALREADY_FOLLOWING';
    }
    
    var follow = document.querySelector('[data-testid$="-follow"]');
    if (follow) {
        follow.click();
        return 'FOLLOWED';
    }
    
    return 'NO_BUTTON_FOUND';
})()
