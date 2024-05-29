function panelNavigateEv(obj, isBackNav) {
    let navTo = null;
    if ("navtofunction" in obj.dataset) {
        let navToFunctionName = obj.dataset.navtofunction;
        if (navToFunctionName in window) {
            navTo = window[navToFunctionName];
        }
    } else if ("navto" in obj.dataset) {
        navTo = obj.dataset.navto
    }
    
    panelNavigate(navTo, null, isBackNav);
}

var showFromTo_currentPanel = null;

function panelNavigate(to, navData, isBackNav) {
    let from = showFromTo_currentPanel;
    
    if (to instanceof Function) {
        to = to(navData);

        if (to === null) {
            to = $(`#${from} .nav-back`).data("navto");
        }
    } 
    
    let exitFuncName = `${from}_exit`;
    let enterFuncName = `${to}_enter`;

    if (exitFuncName in window) {
        console.log("exit", exitFuncName);
        window[exitFuncName]();
    }
    
    if (enterFuncName in window) {
        console.log("enter", enterFuncName);
        window[enterFuncName](navData);
    }
    
    console.log("hide", from);

    $(`#${from}`).addClass("d-none");

    console.log("show", to);
    
    let toDiv = $(`#${to}`);

    showFromTo_currentPanel = to;
    
    toDiv.removeClass("d-none");

    if (!isBackNav) {
        let newBack =  toDiv.find(".nav-back");
        if (newBack.length) {
            newBack[0].dataset.navto = from;
        }
    }
}

function goto(path) {
    window.location.assign(path);
}

var overlay_embeddedShow = 0;
var overlay_hideActive = 0;

function overlayShow(overlay, data, key) {
    let overlayShowFuncName = `${overlay}_show`;
    let hideFuncName = `${showFromTo_currentPanel}_hideDueToOverlay`;

    if (overlay_hideActive > 0) {
        overlay_embeddedShow++;
    }
    
    if (hideFuncName in window) {
        console.log("hide", hideFuncName);
        window[hideFuncName]();
    }
    
    if (overlayShowFuncName in window) {
        console.log("overlay show", overlayShowFuncName);
        window[overlayShowFuncName](data);
    }

    console.log("hide", showFromTo_currentPanel);
    $(`#${showFromTo_currentPanel}`).addClass("d-none");

    console.log("show", overlay);
    let overlayDiv = $(`#${overlay}`);
    if (key) {
        overlayDiv.data("key", key)
    }
    
    overlayDiv.removeClass("d-none");
}

function overlayHide(overlay, data) {
    let hideFuncName = `${overlay}_hide`;
    let showFuncName = `${showFromTo_currentPanel}_showFromOverlay`;
    let showFuncNameSpecific = `${showFromTo_currentPanel}_showFromOverlay_${overlay}`;

    overlay_hideActive++;

    let origEmbeddedShow = overlay_embeddedShow;
    
    if (hideFuncName in window) {
        console.log("overlay hide", hideFuncName);
        window[hideFuncName]();
    }

    if (showFuncNameSpecific in window) {
        console.log("show", showFuncNameSpecific);
        window[showFuncNameSpecific](data);
    }

    let overlayDiv = $(`#${overlay}`);
    if (showFuncName in window) {
        if (data === null) {
            let overlayDataFuncName = `${overlay}_data`;
            if (overlayDataFuncName in window) {
                console.log("overalay data", overlayDataFuncName);
                data = window[overlayDataFuncName]();
            }
        }

        let key = overlayDiv.data("key")
        if (key) {
            if (data) {
                data.key = key;
            } else {
                data = {key: key}
            }
        }
        
        console.log("show", showFuncName);
        window[showFuncName](data);
    }
    
    console.log("hide", overlay);
    overlayDiv.addClass("d-none");

    if (overlay_embeddedShow <= 0) {
        console.log("show", overlay);

        $(`#${showFromTo_currentPanel}`).removeClass("d-none");
    } else if (overlay_embeddedShow != origEmbeddedShow) {
        overlay_embeddedShow--;
    }

    overlay_hideActive--;    
}
