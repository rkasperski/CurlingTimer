function getSheets() {
    return jsonCall('getSheets', 
		    `{{scheme}}://${ip}:{{port}}/ajax/sheets`,
		    {},
                    {method: "GET"});
}

function setSheets(nSheets, sheets, clockServer , drawServer) {
    return jsonCall('setSheets', 
		    `{{scheme}}://${ip}:{{port}}/ajax/sheets`,
		    {nSheets: nSheets,
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

function getDefaultsAjax(async) {
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
    return jsonCall("getDefaultsAjax",
                    "{{scheme}}://{{ip}}:{{port}}/ajax/defaults",
                    {values},
                    {method: "POST"});
}

function getHardwareSettingsAjax(ip) {
    return jsonCall("getDefaultsAjax",
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
