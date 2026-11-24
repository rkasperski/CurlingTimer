function Status(prmIp, url, data, async) {
   if (async !== false) {
      async = true;
   }
   statusStartTime = new Date().getTime();
   return json_call(`${scheme}://${prmIp}:${port}/${url}`, "POST", data, {timeout:500, async: async})
	   .done(function(response) {
         timeSkew = (new Date().getTime() - statusStartTime) / 1000.0;
	   });
}

function getSheets() {
   return json_call(`{{scheme}}://${ip}:{{port}}/ajax/sheets`, "GET");
}

function setSheets(clubName, nSheets, sheets, clockServer , drawServer) {
   return json_call(`{{scheme}}://${ip}:{{port}}/ajax/sheets`, "POST",
                    {clubName: clubName,
                     nSheets: nSheets,
                     sheets: sheets,
                     clockServer: clockServer,
                     drawServer: drawServer});
}

function breakTimerSelect(ip, sensors, checkSensor) {
   return json_call(`{{scheme}}://${ip}:{{port}}/breaktimer/select`, "POST", 
                    {sensors: sensors,
                     checksensor: checkSensor})
}

function getActiveBreakTimers(ip) {
   return json_call(`{{scheme}}://${ip}:{{port}}/ajax/breaktimer/active`, "GET");
}

function getDefaultsAjax(ip, async) {
   return json_call(`{{scheme}}://{{ip}}:{{port}}/ajax/defaults`, "GET", 
                    {},
                    {async: async});
}

function getOrganization() {
   return json_call(`{{scheme}}://{{ip}}:{{port}}/ajax/organization`, "GET");
}

function setOrganization(settings) {
   return json_call(`{{scheme}}://{{ip}}:{{port}}/ajax/organization`, "POST", 
                    {data: settings});
}

function getDevicesAjax() {
   return json_call("{{scheme}}://{{ip}}:{{port}}/ajax/devices", "GET");
}

function loginUser(user, password) {
   return json_call("{{scheme}}://{{ip}}:{{port}}/ajax/login", "POST", 
                    {user:user,
                     password:password})
}

function getTime(ip) {
   return json_call(`{{scheme}}://${ip}:{{port}}/ajax/time`, "GET");
}

function loginWithPIN(ip, pin) {
   return json_call(`{{scheme}}://${ip}:{{port}}/ajax/login/pin`, "POST", 
                    {pin:pin})
}

function getUsers() {
   return json_call("{{scheme}}://{{ip}}:{{port}}/ajax/users", "GET");
}

function updateUsers(data) {
    return json_call("{{scheme}}://{{ip}}:{{port}}/ajax/users", "POST",
                     {data: data});
}

function getUser() {
   return json_call("{{scheme}}://{{ip}}:{{port}}/ajax/user", "GET");
}

function getColours() {
   return json_call("{{scheme}}://{{ip}}:{{port}}/ajax/colours", "GET");
}

function saveColours(colours) {
   return json_call("{{scheme}}://{{ip}}:{{port}}/ajax/colours", "POST",
                    {colours: colours});
}

function setDefaultsAjax(values) {
    return json_call("{{scheme}}://{{ip}}:{{port}}/ajax/defaults", "POST",
                     {values});
}

function getHardwareSettingsAjax(ip) {
   return json_call(`{{scheme}}://${ip}:{{port}}/ajax/hardware`, "GET");
}

function setPassword(user, password) {
   return json_call(`{{scheme}}://${ip}:{{port}}/ajax/password`, "POST",
                    {user: user,
                     password: password});
}

function setSecretKey(ip, secretKey) {
   return json_call(`{{scheme}}://${ip}:{{port}}/ajax/secret/set`, "POST",
                    {secret: secretKey},
                    {timeout: 20000});
}

function getTeamNames(prmIp, async) {
    return json_call(`${scheme}://${prmIp}:${port}/teamnames/get`, "POST", {}, {async:async});
}

function startCompetitionTimeout(prmIp, team) {
   return json_call(`${scheme}://${prmIp}:${port}/competition/timeout/start`, "POST", 
                    {team: team},
                    {retries: 3, timeout: 500});
}

function WhoAreYou(prmIp) {
    return json_call(`${scheme}://${prmIp}:${port}/whoareyou`, "GET");
}

function Message(prmIp, msg, colour) {
   if ( !colour) {
	   colour = 'white';
   }

   return json_call(`${scheme}://${prmIp}:${port}/text`, "POST", 
		              { text: msg,
		                colour: colour
		              },
                    {retries: 3, timeout: 500});
}

function MessageAll(msg, colour) {
   peerList().forEach(peer => Message(peer, msg, colour));
}

function Shutdown(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/shutdown`, "POST")
}

function ShutdownAll(msg) {
   peerList().forEach(peer => Shutdown(peer));
}

function Restart(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/restart`, "POST")
}

function RestartAll(msg, colour) {
   peerList().forEach(peer => Restart(peer));
}

function Reboot(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/reboot`, "POST", {}, {timeout:300000})
}

function RebootAll(msg, colour) {
   peerList().forEach(peer => Reboot(peer));
}

function DisplayBlank(prmIp, blank) {
   if (blank === null) {
      blank = true;
   }

   return json_call(`${scheme}://${prmIp}:${port}/blank`, "POST", {blank: blank});
}

function DisplayBlankAll(blank) {
   peerList().forEach(peer => DisplayBlank(peer, blank));
}

function ClockShow(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/clock/show`, "POST");
}

function ClockShowAll() {
   peerList().forEach(peer => ClockShow(peer));
}

function ElapsedShow(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/elapsed/show`, "POST");
}

function ElapsedShowAll() {
   peerList().forEach(peer => ElapsedShow(peer));
}

function ElapsedStart(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/elapsed/start`, "POST", {}, {retries: 3, timeout: 500})
}

function ElapsedStartAll() {
   peerList().forEach(peer => ElapsedStart(peer));
}

function ElapsedResume(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/elapsed/resume`, "POST", {}, {retries: 3, timeout: 500});
 }

function ElapsedResumeAll() {
   peerList().forEach(peer => ElapsedResume(peer));
}

function ElapsedPause(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/elapsed/pause`, "POST", {} , {retries: 3, timeout: 500});
 }

   function ElapsedPauseAll() {
    peerList().forEach(peer => ElapsedPause(peer));
}

function ElapsedSet(prmIp, startTime) {
   if (! startTime) {
	   startTime = 0;
   }

   return json_call(`${scheme}://${prmIp}:${port}/elapsed/set`, "POST", {time: startTime});
}

function ElapsedSetAll(startTime) {
   peerList().forEach(peer => ElapsedSet(peer, startTime));
}

function CountDownStatus(prmIp, run_async) {
   run_async = (run_async !== false);
   return json_call(`${scheme}://${prmIp}:${port}/countdown/status`, "POST", null, {async: run_async}); 
}

function CountDownSetTime(prmIp, newTime, finishedMessage, finishedMessageColour, lastEndMessage, lastEndMessageColour) {
   return json_call(`${scheme}://${prmIp}:${port}/countdown/set`, "POST", 
		              {finishedMessage: finishedMessage,
		               finishedMessageColour: finishedMessageColour,
		               lastEndMessage: lastEndMessage,
		               lastEndMessageColour: lastEndMessageColour,
		               gameTime: newTime},
                    {async: false});
}

function CountDownResume(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/countdown/resume`, "POST", {}, {retries: 3, timeout: 500});
}

function CountDownResumeAll(show) {
   peerList().forEach(peer => CountDownResume(peer));
}
function CountDownStart(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/countdown/start`, "POST", {}, {retries: 3, timeout: 500});
}

function CountDownStartAll(show) {
   peerList().forEach(peer => CountDownStart(peer));
}

function CountDownPause(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/countdown/pause`, "POST");
}

function CountDownPauseAll() {
   peerList().forEach(peer => CountDownPause(peer));
}

function CountDownShow(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/countdown/show`, "POST");
}

function CountDownLastEnd(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/countdown/lastend`, "POST");
}

function CountDownSetup(prmIp, gameTime, finishedMessage, finishedMessageColour, lastEndMessage, lastEndMessageColour, teamColour, topTeam, bottomTeam) {
   if (!teamColour) {
	   teamColour = 'default'
   }

   return json_call(`${scheme}://${prmIp}:${port}/countdown/set`, "POST", 
		              {team1: topTeam,
		               team2: bottomTeam,
		               gameTime: gameTime,
		               finishedMessage: finishedMessage,
		               finishedMessageColour: finishedMessageColour,
		               lastEndMessage: lastEndMessage,
		               lastEndMessageColour: lastEndMessageColour,
		               teamColour: teamColour});
}
   
function CompetitionSetTime(prmIp, teamName, teamTime) {
   return json_call(`${scheme}://${prmIp}:${port}/competition/settime`, "POST",
		              {team: teamName,
			            time: teamTime
		              });
}

function CompetitionStartBetweenEndTimer(prmIp, betweenEndTime) {
   return json_call(`${scheme}://${prmIp}:${port}/competition/betweenendtimer`, "POST", 
		              {betweenEndTime: betweenEndTime});
}

function CompetitionResume(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/competition/resume`, "POST", {}, {retries: 3, timeout: 500});
}

function CompetitionPause(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/competition/pause`, "POST", {}, {retries: 3, timeout: 500});
}

function CompetitionShow(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/competition/show`, "POST");
}

function CompetitionTeam1Pause(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/competition/team1/pause`, "POST", {}, {retries: 3, timeout: 500});
}

function CompetitionTeam2Pause(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/competition/team2/pause`, "POST", {}, {retries: 3, timeout: 500});
}

function CompetitionTeamExchange(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/competition/team/exchange`, "POST", {}, {retries: 3, timeout: 500});
}

function CompetitionTeam1Resume(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/competition/team1/resume`, "POST", {}, {retries: 3, timeout: 500});
}

function CompetitionTeam2Resume(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/competition/team2/resume`, "POST", {}, {retries: 3, timeout: 500});
}

function CompetitionSetup(prmIp, msg, perTeamTime, intermissionLength, teamColour, topTeam, bottomTeam) {
   return json_call(`${scheme}://${prmIp}:${port}/competition/setup`, "POST",
		              {welcomeMessage: msg,
                     teamColour: teamColour,
		               team1: topTeam,
		               team2: bottomTeam,
		               timeLimit: perTeamTime,
		               intermissionLength: intermissionLength
		              });
}

function CompetitionTimeoutStart(prmIp, team) {
   return json_call(`${scheme}:/${prmIp}:${port}/competition/timeout/start`, "POST",
		              {team: team },
                    {retries: 3, timeout: 500});
}

function TeamNamesShow(prmIp, clock) {
   return json_call(`${scheme}://${prmIp}:${port}/teamnames/show/${clock}`, "POST");
}

function TeamNamesGet(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/teamnames/get`, "POST");
}

function TeamNamesSet(prmIp, team1, team2, colour) {
   return json_call(`${scheme}://${prmIp}:${port}/teamnames/set`, "POST",
		              {team1: team1,
		               team2: team2,
                     colour: colour
                    });
}

function Flash(prmIp, colour) {
   return json_call(`${scheme}://${prmIp}:${port}/flash`, "POST",
                    {colour: colour})
}

function BreakTimerSelect(prmIp, sensors, checkSensor) {
   return json_call(`${scheme}://${prmIp}:${port}/breaktimer/select`, "POST",
		              {sensors: sensors,
		               checksensor: checkSensor});
}

function BreakTimerDisplayStyle(prmIp, style) {
   return json_call(`${scheme}://${prmIp}:${port}/breaktimer/style`, "POST",
		              {style: style});
}

function BreakTimerSetFilter(prmIp, filterTime) {
   return json_call(`${scheme}://${prmIp}:${port}/breaktimer/reset`, "POST",
		              {reset:0,
		               filterTime: filterTime});
}

function BreakTimerSensorFlash(prmIp, id, flashtime) {
   return json_call(`${scheme}://${prmIp}:${port}/sensor/flash`, "POST",
		              {id: id,
		               flashtime: flashtime});
}

function BreakTimerResetTimes(prmIp, filterTime) {
   let data = {}

   if (filterTime) {
	   data = {filterTime: filterTime};
   }

   return json_call(`${scheme}://${prmIp}:${port}/breaktimer/reset`, "POST", data);
}

function BreakTimerSetActive(prmIp, sensors, filterTime) {
   let data = {sensors: sensors};

   if (filterTime) {
	   data.filterTime = filterTime;
   }

   return json_call(`${scheme}://${prmIp}:${port}/breaktimer/active`, "POST", data);
}

function BreakTimerGetTimes(prmIp, index, marker) {
   return json_call(`${scheme}://${prmIp}:${port}/breaktimer/get`, "POST", 
		              {index: index,
		               marker: marker},
                    {timeout: 2000});
}

function ListUpdates(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/update/list`, "POST");
}

function RestartPTPD(prmIp) {
   return json_call(`${scheme}://${prmIp}:${port}/ptpd/restart`, "POST", {}, {timeout:60000});
}

function CleanUpdates(prmIp, upd) {
   return json_call(`${scheme}://${prmIp}:${port}/update/clean`, "POST", {file: upd});
}

function Kapow(prmIp, name) {
   return json_call(`${scheme}://${prmIp}:${port}/kapow`, "POST", {kapow: name});
}

function KapowAll(name) {
   peerList().forEach(peer => Kapow(peer, name));
}

function SetTimeDate(prmIp, time, date, timeZone, permanent) {
   if (permanent == null) {
      permanent = true;
   }
   
   return json_call(`${scheme}://${prmIp}:${port}/timedate`, "POST", 
		              {time:time,
                     date:date,
                     timeZone:timeZone,
                     permanent: permanent},
                    {timeout: 15000});
}
