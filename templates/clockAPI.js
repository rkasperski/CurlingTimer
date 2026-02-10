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

function getSheets() {
    return jsonCall('getSheets', 
                    `{{scheme}}://${ip}:{{port}}/ajax/sheets`,
                    {},
                    {method: "GET"});
}

function setSheets(clubName, nSheets, sheets, clockServer , drawServer) {
    return jsonCall('setSheets', 
                    `{{scheme}}://${ip}:{{port}}/ajax/sheets`,
                    {clubName: clubName,
                     nSheets: nSheets,
                     sheets: sheets,
                     clockServer: clockServer,
                     drawServer: drawServer},
                    {method: "POST"});
}

function breakTimerSelect(ip, sensors, checkSensor) {
    return jsonCall('breakTimerSelect', 
                    `{{scheme}}://${ip}:{{port}}/breaktimer/select`,
                    {sensors: sensors,
                     checksensor: checkSensor},
                    {method: "POST"});
}

function getActiveBreakTimers(ip) {
    return jsonCall("getActiveBreakTimers",
                    `{{scheme}}://${ip}:{{port}}/ajax/breaktimer/active`,
                    {},
                    {method: "GET"});
}

function getDefaultsAjax(ip, async) {
    return jsonCall("getDefaultsAjax",
                    `{{scheme}}://{{ip}}:{{port}}/ajax/defaults`,
                    {},
                    {method: "GET",
                     async: async});
}

function getOrganization() {
    return jsonCall("getOrganization",
                    `{{scheme}}://{{ip}}:{{port}}/ajax/organization`,
                    {},
                    {method: "GET"});
}

function setOrganization(settings) {
    return jsonCall("getOrganization",
                    `{{scheme}}://{{ip}}:{{port}}/ajax/organization`,
                    {data: settings},
                    {method: "POST"});
}

function getDevicesAjax() {
    return jsonCall("getDevicesAjax",
                    "{{scheme}}://{{ip}}:{{port}}/ajax/devices",
                    {},
                    {method: "GET"});
}

function loginUser(user, password) {
    return jsonCall("loginUser",
                    "{{scheme}}://{{ip}}:{{port}}/ajax/login",
                    {user:user,
                     password:password},
                    {method: "POST"});
}

function getTime(ip) {
    return jsonCall("getTime",
                    `{{scheme}}://${ip}:{{port}}/ajax/time`,
                    {},
                    {method: "GET"});
}

function loginWithPIN(pin) {
    return jsonCall("loginUser",
                    "{{scheme}}://{{ip}}:{{port}}/ajax/login/pin",
                    {pin:pin},
                    {method: "POST"});
}

function getUsers() {
    return jsonCall("getUsers",
                    "{{scheme}}://{{ip}}:{{port}}/ajax/users",
                    {},
                    {method: "GET"});
}

function updateUsers(data) {
    return jsonCall("updateUsers",
                    "{{scheme}}://{{ip}}:{{port}}/ajax/users",
                    {data: data},
                    {method: "POST"});
}

function getUser() {
    return jsonCall("getUser",
                    "{{scheme}}://{{ip}}:{{port}}/ajax/user",
                    {},
                    {method: "GET"});
}

function getColours() {
    return jsonCall("getColours",
                    "{{scheme}}://{{ip}}:{{port}}/ajax/colours",
                    {},
                    {method: "GET"});
}

function saveColours(colours) {
    return jsonCall("saveColours",
                    "{{scheme}}://{{ip}}:{{port}}/ajax/colours",
                    {colours: colours},
                    {method: "POST"});
}

function setDefaultsAjax(values) {
    return jsonCall("setDefaultsAjax",
                    "{{scheme}}://{{ip}}:{{port}}/ajax/defaults",
                    {values},
                    {method: "POST"});
}

function getHardwareSettingsAjax(ip) {
    return jsonCall("getHardwareSettingsAjax",
                    `{{scheme}}://${ip}:{{port}}/ajax/hardware`,
                    {},
                    {method: "GET"});
}

function setPassword(user, password) {
    return jsonCall("setPassword",
                    `{{scheme}}://${ip}:{{port}}/ajax/password`,
                    {user: user,
                     password: password},
                    {method: "POST"});
}

function setSecretKey(ip, secretKey) {
    return jsonCall("setPassword",
                    `{{scheme}}://${ip}:{{port}}/ajax/secret/set`,
                    {secret: secretKey},
                    {method: "POST",
                     timeout: 20000});
}

function getTeamNames(prmIp, async) {
    return jsonCall('TeamNamesGet',`${scheme}://${prmIp}:${port}/teamnames/get`, {}, {async:async});
}

function startCompetitionTimeout(prmIp, team) {
    return jsonCall('CompetitionTimeoutStart',
                    `${scheme}://${prmIp}:${port}/competition/timeout/start`,
                    {team: team},
                    {retries: 3, timeout: 500});
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
		              `${scheme}:/${prmIp}:${port}/competition/timeout/start`,
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
