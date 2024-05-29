var global_timingStyle = "raw";

class WSBreakTimerDisplay extends WSSocket {
    cmd_registered(msgData, cbData) {
        console.log(`registered: ${msgData}`);
    }

    cmd_event(msgData, cbData) {
        console.log(`event: ${msgData}`);
    }

    cmd_reset(msgData, cbData) {
        console.log(`reset: ${msgData}`);
    }

    socketClose(event, cbData) {
        console.log("breakTimeDisplay_close");
    }

    socketOpen(event, cbData) {
        console.log("breakTimeDisplay_open");
    
        this.sendMsg("register", {tkn: accessToken,
                                  id: global_id,
                                  sensors: cbData,
                                  style: global_timingStyle});
    }

    socketError(event, cbData) {
        console.log("breakTimeDisplay_error");
    }
}

function connectToBreakTimerDisplay(ip, sensors) {
    let ws = new WSBreakTimerDisplay();
    ws.connect(`ws://${ip}:80/ws/breaktimerdisplay`, sensors);
    return ws;
}
 
