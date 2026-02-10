class Dequeue {
    constructor(n) {
        this.dequeue = [];
        this.n = n;
    }

    items() {
        return this.dequeue;
    }

    pushLeft(element) {
        if (this.length > this.n) {
            this.popRight();
        }
        this.dequeue.unshift(element);
    }

    pushRight(element) {
        if (this.length > this.n) {
            this.popLeft();
        }
        this.dequeue.push(element);
    }

    popLeft() {
        if (!this.isEmpty()) {
            return this.dequeue.shift();
        }
        return null;
    }

    popRight() {
        if (!this.isEmpty()) {
            return this.dequeue.pop();
        }
        return null;
    }

    left() {
        if (!this.isEmpty()) {
            return this.dequeue[0];
        }
        return null;
    }

    right() {
        if (!this.isEmpty()) {
            return this.dequeue[this.dequeue.length - 1];
        }
        return null;
    }

    isEmpty() {
        return this.dequeue.length === 0;
    }

    size() {
        return this.dequeue.length;
    }

    empty() {
        this.dequeue = [];
    }
}

var log_dequeue = new Dequeue(200);
var log_start = Date.now();

function dbg_print(...text){
    console.log(...text);
    log_dequeue.pushLeft([Date.now(), "log", ...text]); 
}
