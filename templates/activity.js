    var sheetActivityStatus = new Array();

    var sheetActivityTimerID = 0;

    {% for s in sheets %}
    {% if s.ip != "Unassigned" %}
    sheetActivityStatus[{{loop.index0}}] = {active:false, idle: false, alive:true, deadCnt:0};
    {% else  %}
    sheetActivityStatus[{{loop.index0}}] = {active:false, idle: false, alive:false, deadCnt:1000};
    {% endif %}
    {% endfor %}
    
    function startActivityCheckTimer(callback) {
       stopActivityCheckTimer();
       let clubStatus = clubClockStatus()
       for (let i = 0; i < peers.length; i++) {
          let s = sheetActivityStatus[i];
          callback(clubStatus, i, s)
       }

       sheetActivityTimerID = setInterval(sheetCheckActive, 1000, callback);
    }

    function stopActivityCheckTimer() {
       clearInterval(sheetActivityTimerID)
    }

    function triState(n, c) {
       if (c == 0) {
          return -1;
       }

       if (c == n) {
          return 1;
       }

       return 0;
    }
    
    // returns
    // -1 if all are inactive
    // 0 if some are active
    // 1 if all are active
    // same for idle
    function clubClockStatus() {
       let nActive = 0;
       let nIdle = 0;
       let nAlive = 0
       for (let i = 0; i < peers.length; i++) {
          if (sheetActivityStatus[i].alive) {
             nAlive += 1;
          }
          if (sheetActivityStatus[i].active) {
             nActive += 1;
          }
          if (sheetActivityStatus[i].idle) {
             nIdle += 1;
          }
       }
       
       return {active: triState(nAlive, nActive), idle: triState(nAlive, nIdle)};
    }

    function sheetCheckActive(callback) {
       for (let i = 0; i < peers.length; i++) {
          let p = peers[i][0];
          if (p!= "Unassigned") {
             let s = sheetActivityStatus[i]
             Status(p, "status")
                .done(function(res) {
                   s.deadCnt = 0;
                   if (!s.alive ||
                       s.active !== res.active ||
                       s.idle !== res.idle) {
                      s.alive = true;
                      s.active = res.active;
                      s.idle = res.idle;
                      callback(clubClockStatus(), i, s);
                   }
                })
                .fail(function() {
                   s.deadCnt++;

                   if ((s.alive && s.deadCnt >= 5 ) ||
                       s.active !== false  ||
                       s.idle !== true )  {
                      s.alive = false;
                      s.active = false;
                      s.idle = true;
                      callback(clubClockStatus(), i, s);
                   }
                })                   
          } 
       }
    }
    
