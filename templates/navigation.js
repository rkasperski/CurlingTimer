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

var showFromTo_current_panel = null;
var showFromTo_next_panel = null;

function panelNavigate(to, navData, isBackNav) {
   let from = showFromTo_current_panel;
    
   if (to instanceof Function) {
      to = to(navData);
      
      if (to === null) {
         to = $(`#${from} .nav-back`).data("navto");
      }
   }

   showFromTo_next_panel = to;   
    
   let exitFuncName = `${from}_exit`;
   let enterFuncName = `${to}_enter`;

   if (exitFuncName in window) {
      dbg_print("exit", exitFuncName);
      window[exitFuncName]();
   }
    
   if (enterFuncName in window) {
      dbg_print("enter", enterFuncName);
      window[enterFuncName](navData);
   }
    
   dbg_print("hide", from);

   $(`#${from}`).addClass("d-none");

   dbg_print("show", to);
    
   let toDiv = $(`#${to}`);

   if (showFromTo_next_panel != to) {
      return;
   }

   showFromTo_current_panel = to;
    
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
    let hideFuncName = `${showFromTo_current_panel}_hideDueToOverlay`;

    if (overlay_hideActive > 0) {
        overlay_embeddedShow++;
    }
    
    if (hideFuncName in window) {
        dbg_print("hide", hideFuncName);
        window[hideFuncName]();
    }
    
    if (overlayShowFuncName in window) {
        dbg_print("overlay show", overlayShowFuncName);
        window[overlayShowFuncName](data);
    }

    dbg_print("hide", showFromTo_current_panel);
    $(`#${showFromTo_current_panel}`).addClass("d-none");

    dbg_print("show", overlay);
    let overlayDiv = $(`#${overlay}`);
    if (key) {
        overlayDiv.data("key", key)
    }
    
    overlayDiv.removeClass("d-none");
}

function overlayHide(overlay, data) {
    let hideFuncName = `${overlay}_hide`;
    let showFuncName = `${showFromTo_current_panel}_showFromOverlay`;
    let showFuncNameSpecific = `${showFromTo_current_panel}_showFromOverlay_${overlay}`;

    overlay_hideActive++;

    let origEmbeddedShow = overlay_embeddedShow;
    
    if (hideFuncName in window) {
        dbg_print("overlay hide", hideFuncName);
        window[hideFuncName]();
    }

    if (showFuncNameSpecific in window) {
        dbg_print("show", showFuncNameSpecific);
        window[showFuncNameSpecific](data);
    }

    let overlayDiv = $(`#${overlay}`);
    if (showFuncName in window) {
        if (data === null) {
            let overlayDataFuncName = `${overlay}_data`;
            if (overlayDataFuncName in window) {
                dbg_print("overalay data", overlayDataFuncName);
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
        
        dbg_print("show", showFuncName);
        window[showFuncName](data);
    }
    
    dbg_print("hide", overlay);
    overlayDiv.addClass("d-none");

    if (overlay_embeddedShow <= 0) {
        dbg_print("show", overlay);

        $(`#${showFromTo_current_panel}`).removeClass("d-none");
    } else if (overlay_embeddedShow != origEmbeddedShow) {
        overlay_embeddedShow--;
    }

    overlay_hideActive--;    
}
