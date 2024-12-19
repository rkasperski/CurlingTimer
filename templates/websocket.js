class WSSocket {
    constructor() {
        this.socket = null;
        this.cbData = null;
        this.commandTable = new Map()
        this.lastPingTime = Date.now();
        this.pingInterval = 1000;
        this.pingResponseInterval = 5000;
        this.lastPongTime = Date.now();
        this.waitOnPongTimerID = null;
        this.sendPingTimerID = null;
        this.url = null;
    }

    connect(url, cbData) {
        console.log("WS: connect", this.url, cbData)
        this.socket = new WebSocket(url);

        this.socket.owner = this;
        this.cbData = cbData;
        this.url = url
        this.lastPingTime = Date.now();
        this.lastPongTime = Date.now();

        this.socket.onerror = function(event) {
            console.log("WS: socket onerror", this.owner.url, event);
            console.log(new Error())
            this.owner.socketError(event, this.owner.cbData);
        }
    
        this.socket.onopen = function(event) {
            this.owner.socketOpen(event, this.owner.cbData);
            this.owner.waitOnPongTimerID = setInterval(this.owner.waitOnPong, this.owner.pingResponseInterval, this.owner);      
            this.owner.sendPingTimerID = setInterval(this.owner.sendPing, this.owner.pingInterval, this.owner);
            this.owner.sendPing(this.owner);
        }
        
        this.socket.onclose = function(event) {
            this.owner.killPingPongTimers();
            this.owner.socket = null;
	    console.log("WS: socket onclose", this.owner.url, event);
            console.log(new Error())
            this.owner.socketClose(event, this.owner.cbData);
            this.owner = null;
        }

        this.socket.onmessage = function(event) {
            if (event.data == "error") {
                console.log("WS: msg-error", this.url, event)
            } else if (event.data == "ping") {
                this.owner.lastPingTime = Date.now();
                this.send("pong");                
            } else if (event.data == "pong") {
                this.owner.lastPongTime = Date.now();
            } else {
	            let data = JSON.parse(event.data);

                if (data.hasOwnProperty("cmd")) {
                    this.owner[`cmd_${data.cmd}`](data.data, this.owner.cbData);
                }
            }
        }
    }

    getState() {
        if (!this.socket) {
            return 3;
        }

        return this.socket.readyState;
    }

    connectionFailed() {
    }

    sendPing(owningSocket) {
        owningSocket.socket.send("ping")
        owningSocket.lastPingTime = Date.now();        
    }

    waitOnPong(owningSocket) {
        let curTime = Date.now();
        if (curTime > (owningSocket.lastPongTime + (owningSocket.pingResponseTime))) {
            console.log("WS: closing; missed pong")
            console.log(new Error())
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
        console.log(`ws socket: closing ${this.url}`)
        console.log(new Error())
        this.killPingPongTimers();

        if (this.socket) {
            this.socket.close();
        }
    }
}
