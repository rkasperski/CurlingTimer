var accessToken = "{{accessToken}}";

var peers = [
    {% for s in sheets %}
    ["{{ s.ip }}", "{{s.ordinal}}"], 
    {% endfor %} ];

setMyAddress("{{ip}}", "{{scheme}}", "{{port}}");
