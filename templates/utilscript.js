var accessToken = '';

var peers = [];
var ip = "";
var scheme = '';
var port = '';
var address = '';

function isStringEmpty(value) {
   return value === undefined || value === null || value.trim() === "";
}

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
         if (errorThrown == "Forbidden" || errorThrown == "Unauthorized") {
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

function formatTime(secs, showHours, maxHours) {
   if (maxHours) {
	   secs = secs % (maxHours * 3600);
   }

   let hours = Math.trunc(secs / 3600);
   let minutes = zeroPad(Math.trunc((secs % 3600) / 60));
   let seconds = zeroPad(Math.trunc(secs) % 60);

   if (hours || showHours) {
	   return `${hours}:${minutes}:${seconds}`;
   } else {
	   return `${minutes}:${seconds}`;
   }
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
   let timeLimit = s.split(':');

   let seconds = parseFloat(timeLimit[timeLimit.length - 1]);

   if (timeLimit.length >= 2) {
      seconds += parseFloat(timeLimit[timeLimit.length - 2]) * 60;
      if (timeLimit.length >= 3) {
         seconds += parseFloat(timeLimit[timeLimit.length - 3]) * 3600;
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

function validField(isValid, input) {
   if (isValid) {
	   input.removeClass('invalid').addClass('valid');
   } else {
	   input.removeClass('valid').addClass('invalid');
   }

    return isValid;
}

function verify_field_pattern(rePat, input, allowEmpty) {
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

var digitRegex = /^\d+$/;

function verify_time_field(input, allowEmpty) {
   return verify_field_pattern(/^[0-9]{1,2}(:[0-9][0-9]){0,2}$/, input, allowEmpty);
}

function verify_int_field(input, allowEmpty) {
   return verify_field_pattern(/^[0-9]+$/, input, allowEmpty);
}

function verify_float_field(input, allowEmpty) {
   return verify_field_pattern(/^[0-9](\.[0-9]+)?$/, input, allowEmpty);
}

function verify_timeOfDay_field(input, allowEmpty) {
   input = $(input);

   let value = input.val();
   let sp = value.split(":");
   let isValid = false;

   if (sp.length == 3) {
      if (digitRegex.test(sp[0]) && digitRegex.test(sp[1]) && digitRegex.test(sp[2])) {
         let hours = Number(sp[0]);
         let minutes = Number(sp[1]);
         let seconds = Number(sp[2]);

         if (hours >= 0 && hours <= 23 &&
             minutes >= 0 && minutes <= 59 &&
             seconds >= 0 && seconds <= 59) {
            isValid = true;
         }
      }
   }

   return isValid;
}

function verify_notEmpty_field(input, allowEmpty) {
   return verify_field_pattern(/./, input, allowEmpty);
}

function verify_unique_field(input, allowEmpty) {
   input = $(input);
   let inputSelector = input.data("verify-unique")
   let uniqueFieldList = $(inputSelector);

   // not efficient but not much used either
   $(unqiueFieldList).each(function(index) {
	   let outer = this;
	   $(unqiueFieldList).each(function(index) {
	      if (outer != this && outer.value && this.value && outer.value == this.value) {
		      return false;
	      }
	   });
   });

   return true;
}

function verify_password_field(input, allowEmpty) {
   input = $(input);
   let newSelector = input.data("verify-password-new")
   let oldPasswordId = input.data("verify-old-password-id")

   let newFieldList = $(newSelector);
   let oldPassword = $(`#${oldPasswordId}`);

   let oldV = oldPassword.val();

   let oldValid = oldV .trim() != "";
   let newValid = true;

   let newV = newFieldList.val();
   newFieldList.each(function (idx) {
      newValid &= $(this).val() == newV;
   })

   newFieldList.each(function (idx) {
      let v = $(this).val()
      newValid &= (v != oldV) && (v.trim() != "");
   })

   validField(newValid, newFieldList);
   validField(oldValid, oldPassword);

   return (oldPasswordId == input.attr("id")) ? oldValid : newValid;
}

function verify_field_class(inputSelector, testF, allowEmpty) {

   // not efficient but not much used either
   $(input).each(function(index) {
      if (!testF($(this))) {
         return false;
      }
   });

   return true;
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

function toDateInputValue(time) {
   console.log("AAA", time.toISOString());
   let d = `${time.getFullYear()}-${zeroPad(time.getMonth() + 1)}-${zeroPad(time.getDate())}`
   console.log(d);

   return d
}

function toTimeInputValue(time) {
   let t =  time.toTimeString().slice(0,5);

   console.log(t, time)
   return t;
}

function toISODateTime(date, time) {
   let extra0 = time[1] == ":" ? "0" : "";
   let s = `${date}T${extra0}${time}`;

   return new Date(s);
}

$(document).ready(function(){
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

function testElement(el) {
   let isValid = false;
   let testType = el.data("verify-type");

   let testFunction = `verify_${testType}_field`;

   if (testFunction in window) {
      isValid = window[testFunction](el, el.data("verify-allow-empty"));
   }

   return isValid;
}

function checkAllFields(selector) {
   let items = $(selector);
   let allOk = true;

   for (let idx = 0; idx < items.length; idx++) {
      let el = $(items[idx]);

      let isValid = testElement(el);
      allOk &= isValid;

      validField(isValid, el);
   }

   return allOk;
}

function checkElement(el) {
   el = $(el);
   let isValid = testElement(el);

   validField(isValid, el);

   let target = el.data("verify-submit");
   if (!isStringEmpty(target)) {
      if (isValid) {
         isValid = checkAllFields(el.data("verify-selector"));
      }

      enableField(isValid, target);
   }

   return isValid;
}

function enableFieldChecking(selector, target) {
   let items = $(selector);

   items.on('input', e => checkElement(e.target))
        .on('keyup', e => checkElement(e.target))
        .data("verify-submit", target)
        .data("verify-selector", selector);

   let submitOk = checkAllFields(selector);

   enableField(target, submitOk);
}
