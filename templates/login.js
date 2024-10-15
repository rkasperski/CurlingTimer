    var loginInfo = null;
    function userInfoRecord() {
       let jsonStr = JSON.stringify(loginInfo)
       localStorage.setItem("logininfo", jsonStr)
    }       
    
    function logoutRecord() {
       loginInfo = null;
       userInfoRecord()
    }
    
    function loginRecordUser(user, isAdmin, accessTkn) {
       loginInfo = { accessToken: accessTkn,
                     user: user,
                     isAdmin: isAdmin,
                     pin: null,
                     pinSheetID: null,
                     pinSheetIP: null}

       accessToken = accessTkn;
       userInfoRecord()
    }

    function loginRecordPIN(accessTkn, sheetID, sheetIP) {
       loginInfo = {accessToken: accessTkn,
                    pinSheetID: sheetID,
                    pinSheetIP: sheetIP,
                    isAdmin: false,
                    user: null}
       
       accessToken = accessTkn;
       userInfoRecord()
    }


