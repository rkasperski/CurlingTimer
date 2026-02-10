var global_timingStyle = "raw";
var sheetTraining_activeSensors = null
var sheetTraining_ws = null

class WSBreakTimerDisplay extends WSSocket {
    cmd_registered(msgData, cbData) {
        dbg_print("WSBreakTimerDisplay: cmd_registered:", this.url, msgData);
        this.registered = true;
    }

    cmd_event(msgData, cbData) {
        dbg_print("WSBreakTimerDisplay cmd_event:", this.url, msgData);
    }

    cmd_reset(msgData, cbData) {
        dbg_print("WSBreakTimerDisplay cmd_reset:", this.url, msgData);
    }

    socketClose(event, cbData) {
        dbg_print("WSBreakTimerDisplay: socketClose", this.url);
        this.registered = false;
    }

    connectionFailed() {
        dbg_print("WSBreakTimerDisplay: connectFailed", this.url);
        this.registered = false;
    }        

    socketOpen(event, cbData) {
        dbg_print("WSBreakTimerDisplay: socketOpen", this.url);
    
        this.sendMsg("register", {tkn: accessToken,
                                  id: global_id,
                                  sensors: cbData,
                                  style: global_timingStyle});
    }

    cmd_endsession(msgData, cbData) {
        dbg_print("WSBreakTimerDisplay: cmd_endsession", this.url, msgData);
        sheetTraining_clearSensors()
    }

    socketError(event, cbData) {
        dbg_print("WSBreakTimerDisplay: socketError", this.url, event);
    }

    reset(filterTime) {
        this.sendMsg("reset", {filterTime: filterTime})
    }
}
