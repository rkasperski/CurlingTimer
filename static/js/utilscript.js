var accessToken = '';

var peers = [];
var ip = "";
var scheme = '';
var port = '';
var address = '';

function setMyAddress(prmIP, prmScheme, prmPort) {
    ip = prmIP;
    scheme = prmScheme;
    port = prmPort;

    address = `${scheme}://${ip}:${port}`
}

var origUrl = location.href;
var origSearch = window.location.search;
var splitUrl = location.href.split('?');
var newURL = splitUrl[0];
window.history.pushState('object', document.title, newURL);

var params={};
origSearch
    .replace(/[?&]+([^=&]+)=([^&]*)/gi, function(str,key,value) {
	params[key] = value;
    });

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

var ajaxTimeout = 5000;

var csrftoken = getCookie("csrftoken");

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        xhr.url = settings.url;
        xhr.funcName = settings.funcName;
        xhr.setRequestHeader("CC-Clock", accessToken);
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

var unauthorizedCallback = null;

$.ajax = (($oldAjax) => {
    // on fail, retry by creating a new Ajax deferred
    // prototyped for failure
    function check(jqXHR, status, errorThrown){
        let shouldRetry = status != 'success' && status != 'parsererror' && status != 'nocontent';
        if (shouldRetry) {
            if (errorThrown == "Forbidden") {
                if (unauthorizedCallback) {
                    if (unauthorizedCallback(jqXHR, status, errorThrown)) {
                        return
                    }
                }
            }
            this.retries--;
            if (this.retries > 0 ) {
	        // console.log("retry: ", status, this.retries, errorThrown);
                setTimeout(() => { $.ajax(this) }, this.retryInterval || 100);
            }
	}
    }

    return settings => $oldAjax(settings).always(check)
})($.ajax);

function standardFailLogger(jqXHR, textStatus, errorThrown) {
    console.log(jqXHR.funcName, ": failed to contact", jqXHR.url, textStatus, errorThrown);
    // alert(textStatus + errorThrown);
    return false
}

// good simple animation is "spinner".
// add a target with of allOfIt or
// set "ajaxAnimationTarget = <name, class, some jQuery selector. default is #allOfIt>" and then
// set of the selection element.
function jsonCall(funcName,
                  url=null,
                  data=null,
                  {method="POST",
                   contentType="application/json",
                   dataType="json",
                   animation=null,
                   timeout=ajaxTimeout,
                   retries=1,
                   async=true,
                   failLogger=standardFailLogger,
                   animationTarget="#allOfIt" }) {
    request = { type          : method,
                contentType   : contentType + "; charset=utf-8",
                timeout       : timeout,
                retries       : retries, 
                retryInterval : timeout,
                async         : async === null ? false : async,
              };

    if (method == "GET") {
        if (data) {
            url += "?" + $.param(data);
        }
    } else {
        if (!data) {
           data = {};
        }
        request.data = (dataType == "json") ? JSON.stringify(data) : data;
        request.dataType = dataType
    }

    request.url = url;
    request.funcName = funcName;

    if (animation) {
        request.animation = animation;
        request.animationTarget = animationTarget;
    }

    return $.ajax(request)
      	.fail(standardFailLogger);
}

function peerList() {
    let validPeers = peers.filter(p => p[0] != "Unassigned");
    let peerlist = validPeers.map(p => p[0]);
    let filteredPeerList = peers.filter(p => p[0] != "Unassigned").map(p => p[0]);

    return filteredPeerList
}

function zeroPad(i) {
    if (i < 10) {
	i = '0' + i;
    };
    
    return i;
}

// need to adjust for network latency.
// simple model is composed of set amount and dynamic amount
// need to skew in different directions depending upon whether the
// timers is counting up or counting down.
var skewAdjustment = 0.100;
var skewDirection = 1;
var timeOffset = 0;
var timeSkew = 0.040;
var timeSkewDecay = 0.9;

function clockTime(time, active, showHours, maxHours) {
    if (active) {
	time = time + (timeSkew + skewAdjustment) * skewDirection;
    }

    if (maxHours) {
	time = time % (maxHours * 3600);
    }

    time += timeOffset;
    
    let hours = Math.trunc(time / 3600);
    let minutes = zeroPad(Math.trunc((time % 3600) / 60));
    let seconds = zeroPad(Math.trunc(time) % 60);

    if (hours || showHours) {
	return `${hours}:${minutes}:${seconds}`;
    } else {
	return `${minutes}:${seconds}`;
    }
}

function Status(prmIp, url, data, async) {
    if (async !== false) {
        async = true;
    }
    statusStartTime = new Date().getTime();
    return jsonCall('Status', `${scheme}://${prmIp}:${port}/${url}`, data, {timeout:500, async: async})
	.done(function(response) {
            timeSkew = (new Date().getTime() - statusStartTime) / 1000.0;
	});
}

function secondsToStr(s, isTimeOnly) {
    days = '';
    if (s > 86400) {
	if (! isTimeOnly) {
            days = Math.trunc(s/86400.0) + ' day(s) ';
	}
    	s = s % 86400;
    }

    hrs = '';
    if (s > 3600) {
        hrs = Math.trunc(s/3600.0) + ':';
        s = s % 3600.0;
    }
        
    return days + hrs + Math.trunc(s / 60) + ':' + zeroPad(Math.trunc(s) % 60);
}

function strToSeconds(s) {
    timeLimit = s.split(':');
    seconds = parseFloat(timeLimit[timeLimit.length - 1]);
    if (timeLimit.length >= 2) {
        seconds += parseFloat(timeLimit[timeLimit.length - 2]) * 60;
        if (timeLimit.length >= 3) {
            seconds += parseFloat(timeLimit[timeLimit.length - 3]) * 3600;
	}
    }

    return seconds;
}

function WhoAreYou(prmIp) {
    return jsonCall('whoareyou',`${scheme}://${prmIp}:${port}/whoareyou`, {}, {method:"GET"});
}

function Message(prmIp, msg, colour) {
    if ( !colour) {
	colour = 'white';
    }
    
    return jsonCall('Message',
		    `${scheme}://${prmIp}:${port}/text`,
		    { text: msg,
		      colour: colour
		    },
                    {retries: 3, timeout: 500});
}

function MessageAll(msg, colour) {
    peerList().forEach(peer => Message(peer, msg, colour));
}

function Shutdown(prmIp) {
    return jsonCall('Shutdown', `${scheme}://${prmIp}:${port}/shutdown`, {}, {})
}

function ShutdownAll(msg) {
    peerList().forEach(peer => Shutdown(peer));
}

function Restart(prmIp) {
    return jsonCall('Restart',  `${scheme}://${prmIp}:${port}/restart`, {}, {})
}

function RestartAll(msg, colour) {
    peerList().forEach(peer => Restart(peer));
}

function Reboot(prmIp) {
    return jsonCall('Restart',  `${scheme}://${prmIp}:${port}/reboot`, {}, {timeout:300000})
}

function RebootAll(msg, colour) {
    peerList().forEach(peer => Reboot(peer));
}

function DisplayBlank(prmIp, blank) {
    if (blank === null) {
        blank = true;
    }
    
    return jsonCall('DisplayBlank',  `${scheme}://${prmIp}:${port}/blank`, {blank: blank}, {});
}

function DisplayBlankAll(blank) {
    peerList().forEach(peer => DisplayBlank(peer, blank));
}

function ClockShow(prmIp) {
    return jsonCall('ClockShow',  `${scheme}://${prmIp}:${port}/clock/show`, {}, {});
}

function ClockShowAll() {
    peerList().forEach(peer => ClockShow(peer));
}

function ElapsedShow(prmIp) {
    return jsonCall('ElapsedShow',  `${scheme}://${prmIp}:${port}/elapsed/show`, {}, {});
}

function ElapsedShowAll() {
    peerList().forEach(peer => ElapsedShow(peer));
}

function ElapsedStart(prmIp) {
    return jsonCall('ElapsedStart', `${scheme}://${prmIp}:${port}/elapsed/start`, {}, {retries: 3, timeout: 500})
}

function ElapsedStartAll() {
    peerList().forEach(peer => ElapsedStart(peer));
}
	     

function ElapsedResume(prmIp) {
    return jsonCall('ElapsedResume',  `${scheme}://${prmIp}:${port}/elapsed/resume`, {}, {retries: 3, timeout: 500});
 }

function ElapsedResumeAll() {
    peerList().forEach(peer => ElapsedResume(peer));
}
	     
function ElapsedPause(prmIp) {
    return jsonCall('ElapsedPause', `${scheme}://${prmIp}:${port}/elapsed/pause`, {} , {retries: 3, timeout: 500});
 }

function ElapsedPauseAll() {
    peerList().forEach(peer => ElapsedPause(peer));
}

function ElapsedSet(prmIp, startTime) {
    if (! startTime) {
	startTime = 0;
    }

    return jsonCall('ElapsedSet', `${scheme}://${prmIp}:${port}/elapsed/set`, {time: startTime }, {});
}

function ElapsedSetAll(startTime) {
    peerList().forEach(peer => ElapsedSet(peer, startTime));
}

function CountDownSetTime(prmIp, newTime, finishedMessage, finishedMessageColour, lastEndMessage, lastEndMessageColour) {
    return jsonCall('SetCountDownTime',
		    `${scheme}://${prmIp}:${port}/countdown/set`, 
		    { finishedMessage: finishedMessage,
		      finishedMessageColour: finishedMessageColour,
		      lastEndMessage: lastEndMessage,
		      lastEndMessageColour: lastEndMessageColour,
		      gameTime: newTime},
                    {});
}						
	 
function CountDownResume(prmIp) {
    return jsonCall('CountDownResume', `${scheme}://${prmIp}:${port}/countdown/resume`, {}, {retries: 3, timeout: 500});
}

function CountDownResumeAll(show) {
    peerList().forEach(peer => CountDownResume(peer));
}
function CountDownStart(prmIp) {
    return jsonCall('CountDownStart', `${scheme}://${prmIp}:${port}/countdown/start`, {}, {retries: 3, timeout: 500});
}

function CountDownStartAll(show) {
    peerList().forEach(peer => CountDownStart(peer));
}

function CountDownPause(prmIp) {
    return jsonCall('PauseCountDown', `${scheme}://${prmIp}:${port}/countdown/pause`, {}, {});
}

function CountDownPauseAll() {
    peerList().forEach(peer => CountDownPause(peer));
}

function CountDownShow(prmIp) {
    return jsonCall('CountDownShow', `${scheme}://${prmIp}:${port}/countdown/show`, {}, {});
}

function CountDownLastEnd(prmIp) {
    return jsonCall('CountDownLastEnd', `${scheme}://${prmIp}:${port}/countdown/lastend`, {}, {});
}

function CountDownSetup(prmIp, gameTime, finishedMessage, finishedMessageColour, lastEndMessage, lastEndMessageColour, teamColour, topTeam, bottomTeam) {
    if (!teamColour) {
	teamColour = 'default'
    }
    
    return jsonCall('CountDownSetup',
		    `${scheme}://${prmIp}:${port}/countdown/set`,
		    { team1: topTeam,
		      team2: bottomTeam,
		      gameTime: gameTime,
		      finishedMessage: finishedMessage,
		      finishedMessageColour: finishedMessageColour,
		      lastEndMessage: lastEndMessage,
		      lastEndMessageColour: lastEndMessageColour,
		      teamColour: teamColour},
                    {})
}
function CompetitionSetTime(prmIp, teamName, teamTime) {
    return jsonCall('CompetitionSetTime',
		   `${scheme}://${prmIp}:${port}/competition/settime`,
		    {
			team: teamName,
			time: teamTime
		    },
                    {});
}

function CompetitionStartBetweenEndTimer(prmIp, betweenEndTime) {
    return jsonCall('CompetitionStartBetweenEndTimer',
		   `${scheme}://${prmIp}:${port}/competition/betweenendtimer`,
		    {
			betweenEndTime: betweenEndTime
		    },
                    {});
}

function CompetitionResume(prmIp) {
    return jsonCall('CompetitionResume',`${scheme}://${prmIp}:${port}/competition/resume`, {}, {retries: 3, timeout: 500});
}

function CompetitionPause(prmIp) {
    return jsonCall('CompetitionPause',`${scheme}://${prmIp}:${port}/competition/pause`, {}, {retries: 3, timeout: 500});
}

function CompetitionShow(prmIp) {
    return jsonCall('CompetitionShow',`${scheme}://${prmIp}:${port}/competition/show`, {}, {});
}

function CompetitionTeam1Pause(prmIp) {
    return jsonCall('CompetitionTeam1Pause',`${scheme}://${prmIp}:${port}/competition/team1/pause`, {}, {retries: 3, timeout: 500});
}

function CompetitionTeam2Pause(prmIp) {
    return jsonCall('CompetitionTeam2Pause',`${scheme}://${prmIp}:${port}/competition/team2/pause`, {}, {retries: 3, timeout: 500});
}     

function CompetitionTeamExchange(prmIp) {
    return jsonCall('CompetitionTeamExchange',`${scheme}://${prmIp}:${port}/competition/team/exchange`, {}, {retries: 3, timeout: 500});
}

function CompetitionTeam1Resume(prmIp) {
    return jsonCall('CompetitionTeam2Resume',`${scheme}://${prmIp}:${port}/competition/team1/resume`, {}, {retries: 3, timeout: 500});
}

function CompetitionTeam2Resume(prmIp) {
    return jsonCall('CompetitionTeam2Resume',`${scheme}://${prmIp}:${port}/competition/team2/resume`, {}, {retries: 3, timeout: 500});
}      

function CompetitionSetup(prmIp, msg, perTeamTime, intermissionLength, teamColour, topTeam, bottomTeam) {
    return jsonCall('CompetitionSetup',
		   `${scheme}://${prmIp}:${port}/competition/setup`,
		    { welcomeMessage: msg,
                      teamColour: teamColour,
		      team1: topTeam,
		      team2: bottomTeam,
		      timeLimit: perTeamTime,
		      intermissionLength: intermissionLength
		    },
                    {});
}

function CompetitionTimeoutStart(prmIp, team) {
    return jsonCall('CompetitionTimeoutStart',
		   `${scheme}://${prmIp}:${port}/competition/timeout/start`,
		    { team: team },
                    {retries: 3, timeout: 500});
}

function TeamNamesShow(prmIp) {
    return jsonCall('TeamNamesShow',`${scheme}://${prmIp}:${port}/teamnames/show`, {}, {});
}

function TeamNamesGet(prmIp) {
    return jsonCall('TeamNamesGet',`${scheme}://${prmIp}:${port}/teamnames/get`, {}, {});
}

function TeamNamesSet(prmIp, team1, team2, colour) {
    return jsonCall('TeamNamesSet',
		   `${scheme}://${prmIp}:${port}/teamnames/set`,
		    {team1: team1,
		     team2: team2,
                     colour: colour
                    },
                    {});
}

function Flash(prmIp, colour) {
    return jsonCall('Flash',
                    `${scheme}://${prmIp}:${port}/flash`,
                    {colour: colour},
                    {});
}

function BreakTimerSelect(prmIp, sensors, checkSensor) {
    return jsonCall('BreakTimerSelect', 
		    `${scheme}://${prmIp}:${port}/breaktimer/select`,
		    {sensors: sensors,
		     checksensor: checkSensor},
                    {});
}

function BreakTimerDisplayStyle(prmIp, style) {
    return jsonCall('BreakTimerDisplayStyle', 
		    `${scheme}://${prmIp}:${port}/breaktimer/style`,
		    {style: style},
                    {});
}

function BreakTimerSetFilter(prmIp, filterTime) {
    return jsonCall("BreakTimerSetFilter", 
		    `${scheme}://${prmIp}:${port}/breaktimer/reset`, 
		    { reset:0,
		      filterTime: filterTime},
                    {});
}

function BreakTimerSensorFlash(prmIp, id, flashtime) {
    return jsonCall('BreakTimerSensorFlash',
		    `${scheme}://${prmIp}:${port}/sensor/flash`,
		    {id: id,
		     flashtime: flashtime},
                    {}
                   );
}

function BreakTimerDisplayTimes(prmIp) {
    return jsonCall("BreakTimerDisplayTimes",
                    `${scheme}://${prmIp}:${port}/breaktimer/display`,
                    {'clear': 1},
                    {});
}

function BreakTimerResetTimes(prmIp, filterTime) {
    let data = {}
    
    if (filterTime) {
	data = {filterTime: filterTime};
    }
    
    return jsonCall("BreakTimerResetTimes",
                    `${scheme}://${prmIp}:${port}/breaktimer/reset`,
                    data,
                    {});
}

function BreakTimerSetActive(prmIp, sensors, filterTime) {
    let data = {sensors: sensors};

    if (filterTime) {
	data.filterTime = filterTime;
    }
    
    return jsonCall("BreakTimerSetActive",
                    `${scheme}://${prmIp}:${port}/breaktimer/active`,
                    data,
                    {});
}

function BreakTimerGetTimes(prmIp, index, marker) {
    return jsonCall("BreakTimerGetTimes",
		    `${scheme}://${prmIp}:${port}/breaktimer/get`,
		    {index: index,
		     marker: marker},
                    {timeout: 2000});
}

function ListUpdates(prmIp) {
    return jsonCall("ListUpdates", `${scheme}://${prmIp}:${port}/update/list`, {}, {});
}

function RestartPTPD(prmIp) {
    return jsonCall("RestartPTZPD", `${scheme}://${prmIp}:${port}/ptpd/restart`, {}, {timeout:60000});
}

function CleanUpdates(prmIp, upd) {
    return jsonCall("CleanUpdates", `${scheme}://${prmIp}:${port}/update/clean`, {file: upd}, {});
}

function Kapow(prmIp, name) {
    return jsonCall("Kapow",
		    `${scheme}://${prmIp}:${port}/kapow`,
		    {kapow: name},
                    {});
}

function KapowAll(name) {
    peerList().forEach(peer => Kapow(peer, name));
}

function SetTimeDate(prmIp, time, date, timeZone, permanent) {
    if (permanent == null) {
        permanent = true;
    }
    return jsonCall("timedate",
		    `${scheme}://${prmIp}:${port}/timedate`,
		    {time:time,
                     date:date,
                     timeZone:timeZone,
                     permanent: permanent},
                    {timeout: 15000});
}

function toSeconds(hms) {
    sp = hms.split(':');
    seconds = parseInt(sp.pop());
    if (sp.length > 0) {
	seconds = seconds * 60 + parseInt(sp.pop());
	if (sp.length > 0) {
	    seconds = seconds * 60 + parseInt(sp.pop());
	}
    }
    
    return seconds;
}

function enableField(enable, target) {
    if (enable) {
	$(target).removeClass('disabled')
    } else {
	$(target).addClass('disabled')
    }
}

function checkField(rePat, input, allowEmpty) {
    input = $(input)
    
    let value = input.val();
    let isValid = rePat.test(value);

    if (allowEmpty) {
	if (!value) {
	    isValid = true
	}
    }

    return isValid;
}

function validField(isValid, input) {
    if (isValid) {
	input.removeClass('invalid').addClass('valid');
    } else {
	input.removeClass('valid').addClass('invalid');
    }
}

function verifyField(rePat, input, target, allowEmpty) {
    input = $(input)
    
    let value = input.val();
    let isValid = checkField(rePat, input, allowEmpty);
    
    validField(isValid, input);
    if (!target) {
        enableField(isValid, target);
    }

    return isValid;
}

function verifyTimeField(input, target, allowEmpty) {
    verifyField(/^[0-9]{1,2}(:[0-9][0-9]){0,2}$/, input, target, allowEmpty);
}

function verifyNoneEmpty(input, target) {
    verifyField(/./, input, target, false);
}

function verifyNumberField(input, target, allowEmpty) {
    verifyField(/^[0-9]+$/, input, target, allowEmpty);
}

function verifyUnique(inputSelector, target) {
    let input = $(inputSelector);
    
    if (!target) {
	target = '.submit-target';
    }

    let isValid = true;

    // not efficient but not much used either
    $(input).each(function(index) {
	let outer = this;
	$(input).each(function(index) {
	    if (outer != this && outer.value && this.value && outer.value == this.value) {
		isValid = false;
	    }
	});
    });

    if (isValid) {
	input.removeClass('invalid').addClass('valid');
    } else {
	input.removeClass('valid').addClass('invalid');
    }

    enableField(isValid, target);
}

function flip(a,b) {
    let va = $('#' + a).val();
    let vb = $('#' + b).val();
    
    $('#' + a).val(vb);
    $('#' + b).val(va);
}

function cmpColumn(a, b, col) {
    let A = $(a).children('td').eq(col[0]).text().toUpperCase();
    let B = $(b).children('td').eq(col[0]).text().toUpperCase();
    
    if(A < B) {
	return -col[1];
    }
    
    if(A > B) {
	return col[1];
    }
	    
    return 0;
}
// 1 for ascending, -1 for descending
function sortTable(myTable, col, dir){
    let rows = $(myTable + ' tbody  tr').get();
    if (!Array.isArray(col)) {
	col = [[col, dir]]
    }
    
    sortFunc = function(a, b) {
	for (c in col) {
	    cmp = cmpColumn(a, b, col[c], dir)
	    if (cmp != 0) {
		return cmp;
	    }
	}

	return 0;
    }
    rows.sort(sortFunc);
    
    $.each(rows, function(index, row) {
	$(myTable).children('tbody').append(row);
    });
}	 

Date.prototype.toDateInputValue = (function() {
    var local = new Date(this);
    local.setMinutes(this.getMinutes() - this.getTimezoneOffset());
    return local.toJSON().slice(0,10);
});

Date.prototype.toTimeInputValue = (function() {
    var local = new Date(this);
    local.setMinutes(this.getMinutes() - this.getTimezoneOffset());

    return local.toJSON().slice(11,16);
});

function checkNumber(itemsToCheckSelector, targetSelector, allowEmpty) {
    $(itemsToCheckSelector).on('input', function(e) {
	verifyNumberField(e.target, targetSelector, allowEmpty);
    });
    
    $(itemsToCheckSelector).on('keyup', function(e) {
	verifyNumberField(e.target, targetSelector, allowEmpty);
    });
}

function checkNoneEmpty(itemsToCheckSelector, targetSelector, allowEmpty) {
    $(itemsToCheckSelector).on('input', function(e) {
	verifyNoneEmpty(e.target, targetSelector, allowEmpty);
    });
    
    $(itemsToCheckSelector).on('keyup', function(e) {
	verifyNoneEmpty(e.target, targetSelector, allowEmpty);
    });
}
                     
function checkTime(itemsToCheckSelector, targetSelector, allowEmpty) {
    $(itemsToCheckSelector).on('input', function(e) {
	verifyTimeField(e.target, targetSelector, allowEmpty);
    });
    
    $(itemsToCheckSelector).on('keyup', function(e) {
	verifyTimeField(e.target, targetSelector, allowEmpty);
    });
}
                     
$(document).ready(function(){
    checkNumber('.check-number')
    checkNoneEmpty('.check-none-empty')
    checkTime('.check-time')
    
    $('.dropdown-submenu > a').on('click', function(e) {
	let submenu = $(this);
	$('.dropdown-submenu .dropdown-menu').removeClass('show');
	submenu.next('.dropdown-menu').addClass('show');
	e.stopPropagation();
    });
    
    $('.dropdown').on('hidden.bs.dropdown', function() {
	// hide any open menus when parent closes
	$('.dropdown-menu.show').removeClass('show');
    });

});

ajaxAnimationSpinner = {
  //none, rotateplane, stretch, orbit, roundBounce, win8,
  //win8_linear, ios, facebook, rotation, timer, pulse,
  //progressBar, bouncePulse or img
  effect: 'bounce',
  text: '' , //place text under the effect (string).
  bg: 'rgba(255,255,255,0.3)', //background for container (string).
  color: '#000', //color for background animation and text (string).
  maxSize: '',
  waitTime: -1, //wait time im ms to close
  source: "",
  textPos: 'vertical',
  fontSize: '',
  onClose: function() {// callback
  }
};

(function($) {
    $.ajaxPrefilter(function( options, _, jqXHR ) {
        if (options.animation && options.animationTarget) {
            function stopAnimation() {
                $(options.animationTarget).waitMe('hide');
            }
            $(options.animationTarget).waitMe(ajaxAnimationSpinner);
            jqXHR.then(stopAnimation, stopAnimation);
        }
    });
})( jQuery);

var utilHtmlEscapeCharMap = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': '&quot;',
  "'": '&#39;',
  "'": '&#39;',
  "/": '&#x2F;'
};

function htmlToText(toText) {
    if (!toText) {
	return "";
    }

    if (!(typeof toText === 'string' || toText instanceof String)) {
	toText = '' + toText;
    }
    
    return toText.replace(/[&<>"'\/]/g, function (s) {
        return utilHtmlEscapeCharMap[s];
    });
}

unauthorizedCallback = function(jqXHR,status,errorThrown) {
    console.log(jqXHR.url)
    alert(jqXHR.url)
    window.location.replace("/login");
}

