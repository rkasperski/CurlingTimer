class WSSocket {
    constructor() {
        this.socket = null;
        this.sbData = null;
        this.commandTable = new Map()
        this.lastPingTime = new Date().getTime() / 1000;
        this.pingDelay = 10;
        this.pingTimerID = null;
    }

    connect(url, cbData) {
        this.pingTimerID = setInterval(this.waitOnPing, 10000, this);      
        this.socket = new WebSocket(url);
        this.socket.owner = this;
        this.cbData = cbData;

        this.socket.onerror = function(event) {
            this.owner.socketError(event, this.owner.cbData);
        }
    
        this.socket.onopen = function(event) {
            this.owner.socketOpen(event, this.owner.cbData);
        }
        
        this.socket.onclose = function(event) {
            this.owner.killPingTimer();
	    this.owner.socketClose(event, this.owner.cbData)
        }

        this.socket.onmessage = function(event) {
            if (event.data == "close") {
                this.close()
            } else if (event.data == "ping") {
                this.owner.lastPingTime = new Date().getTime() / 1000;
                this.send("pong");                
            } else {
	        let data = JSON.parse(event.data);
                
                this.owner[`cmd_${data.cmd}`](data.data, this.owner.cbData);
            }
        }
    }

    waitOnPing(cbData) {
        let curTime = new Date().getTime() / 1000;
        if (curTime > (cbData.lastPingTime + (cbData.pingDelay* 1.5))) {
            cbData.close();
        }
    }

    socketError(event, cbData) {
    }
    
    socketOpen(event, cbData) {
    }
    
    socketClose(event, cbData) {
    }
    
    sendMsg(cmd, data) {
        return this.socket.send(JSON.stringify({cmd: cmd, data: data}));
    }

    killPingTimer() {
        if (this.pingTimerID) {
            clearInterval(this.pingTimerID);
            this.pingTimerID = 0;
        }
    }

    close() {
        this.killPingTimer();
        if (this.socket) {
            this.socket.send("close");                
            this.socket.close();
        }
    }
}
