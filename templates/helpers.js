function updateNavPanel(panelHandle, newId, title, back, up) {
    let navback = panelHandle.find(".nav-back")[0];
    let navup = panelHandle.find(".nav-up")[0];
    navback.dataset.navfrom = newId;
    
    if (back) {
        navback.dataset.navto = back
    }
    
    navup.dataset.navfrom = newId;
    if (up) {
        navup.dataset.navto = up
    }
    
    panelHandle.find(".nav-title").text(title)
    panelHandle.attr("id", newId);
}

function toggleIcon(who, state, trueIcon, falseIcon) {
    who.removeClass(`bi-${trueIcon}`).removeClass(`bi-${falseIcon}`);
    who.addClass(state ? `bi-${trueIcon}` : `bi-${falseIcon}`);
}

function renderIcon(icon, id, clss, style, extra) {
    let rId = id ? ` id="${id}"` : "";
    let rClass = clss ? clss : "";
    let rStyle = style ? `style=" ${style}"` : "";
    let rExtra = extra ? extra : "";

    return `<i class="bi bi-${icon} ${rClass}"${rId}${rStyle} ${rExtra}></i>`;
}

function addActionIcon(parent, id, title, icon, action, data, addBreak) {
    let parentId = $(parent)[0].id;

    if (addBreak) {
        $(parent).append('<div class="w-100"></div>')
    }
    
    let newIcon =
        `<div class="actionIcon col-3 col-md-2 text-center mb-1 mt-2 iconClass-${parentId}" onclick="${action}" id="${id}">
<div>
      <i class="bi bi-${icon}" id="iconId-${id}"></i>
</div
<div>
    <span id="iconTitle-${id}" >${htmlToText(title).replace(/(?:\r\n|\r|\n)/g, '<br>')}</span>
</div>
    </div>`;
    
    $(parent).append(newIcon)
    let added = $(`#${id}`)
    for (let p in data) {
        added[0].dataset[`icondata${p}`] = data[p];
    }
    
    return added;
}

function addSelectableIcon(parent, id, checkedClass, title, icon, data, addBreak) {
    let parentId = $(parent)[0].id;

    if (addBreak) {
        $(parent).append('<div class="w-100"></div>')
    }
    
    let newIcon =
        `<div class="col-auto text-center mb-4 actionIcon selectable-icon-class-${parentId}" id="${id}">
       <div class="selectable-icon-wrapper mx-auto">
         <i class="bi bi-${icon}" id="iconId-${id}"> </i>
         <input class='selectable-icon-input ${checkedClass}' type="checkbox" id="checkId-${id}">
         <label for="checkId-${id}"></label>
       </div>   
       <div class="mx-auto">
         <span id="iconTitle-${id}" >${htmlToText(title).replace(/(?:\r\n|\r|\n)/g, '<br>')}</span>
       </div>
    </div>
          `;
    
    $(parent).append(newIcon)
    let added = $(`#checkId-${id}`)
    for (let p in data) {
        added[0].dataset[`icondata${p}`] = data[p];
    }

    return added;
}

function getSelectedIconList(checkedClass) {
    return $(`.${checkedClass}:checkbox:checked`)
}

function getUnselectedIconList(checkedClass) {
    return $(`.${checkedClass}:checkbox:not(:checked)`)
}

function addColourSelector(parent, id, deflt, colours) {
    let header = `<select class="form-control" id="${id}">`
    
    let colourList = colours.map(
        function(c) {
            return `<option value="${c[0]}" ${(deflt == c[0]) ? "selected" : ""}> ${c[0]} </option>`
        })
    
    $(parent).append(header + colourList.join("\n") + '</select>');
}

function setColour(element, colour) {
    $(`${element} option[value="${colour}"]`).attr('selected','selected');
}

function emptyTable(table, emptyHeaders) {
    if (emptyHeaders) {
        $(`#${table} thead`).empty();
    }
    $(`#${table} tbody`).empty();
}

function renderDynamicTableData(parent, nTable, caption, headers, data, needSeparator, tableClasses) {
    if (needSeparator) {
        $(parent).append('<hr class="divider mt-2" />')
    }

    if (tableClasses === undefined || tableClasses === null) {
        tableClasses = "no-more-tables"
    }
    $(`#${parent}`).append(
        `<table class="table table-striped caption-top ${tableClasses}" id="${nTable}" >
   ${caption?'<caption class="fw-bolder">' + htmlToText(caption) + '</caption>': '' }
   <thead class="thead-light">
   </thead>
   <tbody>
   </tbody>
</table>`)
    renderTableData(nTable, headers, data);
}

function renderTableData(table, headers, data) {
    let tHead = $(`#${table} thead`);
    let tBody = $(`#${table} tbody`);
    
    tHead.empty();
    tBody.empty();
    headers.forEach(h => tHead.append(`<th> ${htmlToText(h)} </th>`));
    data.forEach(function (d, i) {
        let s = '<tr>'
        d.forEach((e, i) => s += `<td data-title="${htmlToText(headers[i])}"> ${htmlToText(e)} </td>`)
        s += '</tr>'
        tBody.append(s)          
    })
}

function loadSettings(prefix, settings, itemDiv) {
    let settingClass = `${prefix}-setting`;
    
    for (let setting in settings) {
        if (itemDiv) {
            $(itemDiv).append(`<div class="row mt-2"><div class="col-4 col-md-3 mt-2">
   <label for="${prefix}-${setting}" >${setting}:</label>
</div>
<div class="col-6 col-md-4">
   <input type="text" class="form-control check-time" id="${prefix}-${setting}" value="">
	     </div></div>`)
        }
        
        let tgt = $(`#${prefix}-${setting}`)
        tgt.addClass(settingClass);
        if (setting.includes("colour") || setting.includes("Colour")) {
            setColour(`#${prefix}-${setting}`, settings[setting])
        } else {
            tgt.val(settings[setting])
        }
    }
}

function gatherSettings(prefix) {
    let settingClass = `.${prefix}-setting`;
    let settings = {};
    
    $(settingClass).each(function (e) {
        settings[this.id.split('-')[1]] = this.value
    })
    
    return settings
}

function grabNamesFromPeers(topSelector, bottomSelector) {
    for (let p in peers) {
        let peer = peers[p][0];
        if (peer != "Unassigned") {
	    TeamNamesGet(peer)
	        .done(function(response) {
	            $(`${topSelector}${p}`).val(response.team1);
	            $(`${bottomSelector}${p}`).val(response.team2);
	        });
        }
    }
}

function capitalize(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

function normTime(t, prefix) {
    if (! isNaN(t)) {
        if (t >= 60) {
            let m = t % 60;
            let h =  ((t - m) / 60);
            let s = prefix + ' ' + h + 'h';
            if (m != 0) {
                s += ' ' + m + 'm';
            }
            
            return s
        } else {
            return prefix + ' ' + t + 'm';
        }
    }
    
    return capitalize(t); 
}

function waitForRemote(prmIp, target, op, skipTime, onSuccess) {
    let secs = 0;
    let tgt = `${target}`;
    let restartTimer = setInterval(function() {
        secs++;
        if (secs > 300) {
            $(tgt).text(`${op} failed`);
            clearInterval(restartTimer);
            return
        }
        if (secs > skipTime) {
            WhoAreYou(prmIp)
                .done(function(res) {
                    $(tgt).text(`${op} succeeded`)
                    clearInterval(restartTimer);
                    onSuccess()
                })
                .fail(function() {
                    $(tgt).text(`... ${secs}` );
                })
        } else {
            $(tgt).text(`... ${secs}` );
        }
        
    }, 1000);
}

var btnClickTime = 350;

function setupClickHack() {
    $('.btn').bind('touchstart', function () {
        var el = $(this);
        el.addClass('hover-clicked').addClass("hover"); 
        
        el.hover(null, function () {
            el.removeClass('hover').removeClass('hover-clicked');
        });
        
        setTimeout(function () {
            el.removeClass('hover-clicked').addClass('hover');
        }, btnClickTime);
    });
}

function security_enableAdminPages(isAdmin) {
    if (isAdmin === undefined) {
        isAdmin = loginInfo && loginInfo.isAdmin;
    }

    if (isAdmin) {
        $(".security-adminOnly").show();
    } else {
        $(".security-adminOnly").hide();
    }
}
