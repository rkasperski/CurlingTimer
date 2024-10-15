class WSSocket {
    constructor() {
        this.socket = null;
        this.cbData = null;
        this.commandTable = new Map()
        this.lastPingTime = new Date().getTime() / 1000;
        this.pingDelay = 10;
        this.lastPongTime = new Date().getTime() / 1000;
        this.waitOnPongTimerID = null;
        this.sendPingTimerID = null;
    }

    connect(url, cbData) {
        this.socket = new WebSocket(url);
        this.socket.owner = this;
        this.cbData = cbData;

        this.socket.onerror = function(event) {
            this.owner.socketError(event, this.owner.cbData);
        }
    
        this.socket.onopen = function(event) {
            this.owner.socketOpen(event, this.owner.cbData);
            this.owner.waitOnPongTimerID = setInterval(this.owner.waitOnPong, this.owner.pingDelay * 1.5, this.owner);      
            this.owner.sendPingTimerID = setInterval(this.owner.sendPing, this.owner.pingDelay, this.owner);
            this.owner.sendPing(this.owner);
        }
        
        this.socket.onclose = function(event) {
            this.owner.killPingPongTimers();
	    this.owner.socketClose(event, this.owner.cbData)
        }

        this.socket.onmessage = function(event) {
            if (event.data == "close") {
                this.close()
            } else if (event.data == "ping") {
                this.owner.lastPingTime = new Date().getTime() / 1000;
                this.send("pong");                
            } else if (event.data == "pong") {
                this.owner.lastPongTime = new Date().getTime() / 1000;
            } else {
	        let data = JSON.parse(event.data);
                
                this.owner[`cmd_${data.cmd}`](data.data, this.owner.cbData);
            }
        }
    }

    sendPing(owningSocket) {
        owningSocket.socket.send("ping")
        owningSocket.lastPingTime = new Date().getTime() / 1000;        
    }

    waitOnPong(owningSocket) {
        let curTime = new Date().getTime() / 1000;
        if (curTime > (owningSocket.lastPongTime + (owningSocket.pingDelay* 1.5))) {
            owningSocket.close();
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

    killPingPongTimers() {
        if (this.waitOnPongTimerID) {
            clearInterval(this.waitOnPongTimerID);
            this.waitOnPongTimerID = 0;
        }
        if (this.sendPingTimerID) {
            clearInterval(this.sendPingTimerID);
            this.sendPingTimerID = 0;
        }
    }

    close() {
        this.killPingPongTimers();
        if (this.socket) {
            this.socket.send("close");                
            this.socket.close();
        }
    }
}
