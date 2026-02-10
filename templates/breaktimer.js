var global_id = Math.random() * 100000000000000000;

class WSBreakTimer extends WSSocket {
    cmd_registered(msgData, cbData) {
        dbg_print("WSBreakTimer: cmd_registered:", this.url, msgData);
        this.registered = true;
    }

    connectionFailed() {
        dbg_print("WSBreakTimer: connectionFailed:", this.url);
        this.registered = false;
    }        

    cmd_time(time, cbData) {
        dbg_print("WSBreakTimer: cmd_time:", this.url, time);
        this.newTime(cbData, time);
        this.updateDisplay();    
    }

    cmd_times(times, cbData) {
        dbg_print("WSBreakTimer: cmd_times:", this.url, times);
        times.forEach(time => this.appendTime(cbData, time));
        this.updateDisplay();
        this.updateEvents();
    }

    cmd_reset(msgData, cbData) {
        dbg_print(`WSBreakTimer: cmd_reset: ${msgData}`);
    }

    socketClose(event, cbData) {
        dbg_print("WSBreakTimer: socketClose:", this.url);
        this.registered = false;
    }

    socketOpen(event, cbData) {
        dbg_print("WSBreakTimer: socketOpen:", this.url);
    
        this.sendMsg("register", {tkn: accessToken,
                                  id: global_id,
                                  name: cbData.name});
    }

    socketError(event, cbData) {
        dbg_print("WSBreakTimer: socketError",  this.url, event);
    }

    reset(filterTime) {
        this.sendMsg("reset", {filterTime, filterTime})
    }
}
