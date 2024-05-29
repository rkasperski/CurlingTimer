function timer_secsToTime(secs) {
    return new Date(secs * 1000).toISOString().substring(11, 19).replace(/^(?:00:)?0?/, '');
}

function timer_tracker(ip, who, url, stateChangeCallback, up) {
    let timer_lastTimerSet = "";
    let timer_active = -1;
    let timer_firstResponse = true;
    let timer_localStartTime = 0;
    let timer_remoteStartTime = 0;
    let timer_markSeconds = 0
    let timer_activeSeconds = 0
    let timer_sumReponseTimes = 0;
    let timer_nResponses = 0;
    let timer_callTime = 0;
    let timer_direction = -1
    let timer_rounding = 0.99
    
    function timer_setTimer(who, curTime) {
        if (curTime != timer_lastTimerSet) {
            $(who).html(timer_secsToTime(curTime));
            timer_lastTimerSet = curTime;
        }
    }
    
    function timer_handleResponse(r) {
        timer_markSeconds = new Date().getTime() / 1000;
        timer_sumReponseTimes += timer_markSeconds - timer_callTime;
        timer_nResponses += 1

        if (timer_active != r.active) {
            timer_active = r.active;
            if (timer_active) {
                timer_localStartTime = timer_markSeconds;
                timer_remoteStartTime = r.seconds
            }
            
            stateChangeCallback(timer_active, r.seconds, r);
        }

        if (timer_active) {
            let remoteRunningTime = r.seconds - timer_remoteStartTime;
            let localRunningTime =  timer_markSeconds - timer_localStartTime;
            let tDiff = localRunningTime - remoteRunningTime
        }
        
        timer_activeSeconds = r.seconds;
    }
    
    function timer_intervalStatus() {
        timer_callTime =  new Date().getTime() / 1000
        Status(ip, url)
            .done(timer_handleResponse)
            .fail(function (output) {
	        timer_active = false;				
                return false;
            });
    }
    
    function timer_displayHandler() {
        if (timer_active === true) {
            let curTime = new Date().getTime() / 1000;
            let avgResponseTime = timer_sumReponseTimes / timer_nResponses;
            let localRunningTime = Math.max(0, timer_remoteStartTime + timer_direction * (curTime - timer_localStartTime) - avgResponseTime * 0.9);
            
            timer_setTimer(who, localRunningTime + timer_rounding);
        } else {
            timer_setTimer(who, timer_activeSeconds + timer_rounding);
        }
    }

    if (up) {
        timer_direction = 1
        timer_rounding = 0;
    }
    
    let intervalTimerID = setInterval(timer_intervalStatus, 1000);
    timer_intervalStatus()
    let displayTimerID = setInterval(timer_displayHandler, 100);

    return {intervalTimerID: intervalTimerID, displayTimerID: displayTimerID}
}

function timer_cancel(t) {
    clearInterval(t.displayTimerID)
    clearInterval(t.intervalTimerID)
}
