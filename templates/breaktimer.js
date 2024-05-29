var global_id = Math.random() * 100000000000000000;

class WSBreakTimer extends WSSocket {
    cmd_registered(msgData, cbData) {
        console.log(`registered: ${msgData}`);
    }

    cmd_time(time, cbData) {
        this.newTime(cbData, time);
        this.updateDisplay();    
    }

    cmd_times(times, cbData) {
        times.forEach(time => this.appendTime(cbData, time));
        this.updateDisplay();
        this.updateEvents();
    }

    cmd_reset(msgData, cbData) {
        console.log(`reset: ${msgData}`);
    }

    socketClose(event, cbData) {
        console.log("getBreakTimes_close");
    }

    socketOpen(event, cbData) {
        console.log("getBreakTimes_open");
    
        this.sendMsg("register", {tkn: accessToken,
                                  id: global_id,
                                  name: cbData.name});
    }

    socketError(event, cbData) {
        console.log("getBreakTimes_error");
    }
}
 
