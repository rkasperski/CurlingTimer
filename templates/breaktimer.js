var global_id = Math.random() * 100000000000000000;

class WSBreakTimer extends WSSocket {
    cmd_registered(msgData, cbData) {
        console.log("WSBreakTimer: cmd_registered:", this.url, msgData);
        this.registered = true;
    }

    connectionFailed() {
        console.log("WSBreakTimer: connectionFailed:", this.url);
        this.registered = false;
    }        

    cmd_time(time, cbData) {
        console.log("WSBreakTimer: cmd_time:", this.url, time);
        this.newTime(cbData, time);
        this.updateDisplay();    
    }

    cmd_times(times, cbData) {
        console.log("WSBreakTimer: cmd_times:", this.url, times);
        times.forEach(time => this.appendTime(cbData, time));
        this.updateDisplay();
        this.updateEvents();
    }

    cmd_reset(msgData, cbData) {
        console.log(`WSBreakTimer: cmd_reset: ${msgData}`);
    }

    socketClose(event, cbData) {
        console.log("WSBreakTimer: socketClose:", this.url);
        this.registered = false;
    }

    socketOpen(event, cbData) {
        console.log("WSBreakTimer: socketOpen:", this.url);
    
        this.sendMsg("register", {tkn: accessToken,
                                  id: global_id,
                                  name: cbData.name});
    }

    socketError(event, cbData) {
        console.log("WSBreakTimer: socketError",  this.url, event);
    }

    reset(filterTime) {
        this.sendMsg("reset", {filterTime, filterTime})
    }
}
