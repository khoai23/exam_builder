var getUrlParameter = function getUrlParameter(sParam) {
	var sPageURL = window.location.search.substring(1),
		sURLVariables = sPageURL.split('&'), sParameterName;
	for (let i = 0; i < sURLVariables.length; i++) {
		sParameterName = sURLVariables[i].split('=');
		if (sParameterName[0] === sParam) {
			return sParameterName[1] === undefined ? true : decodeURIComponent(sParameterName[1]);
		}
	}
	return false;
};

function download_blob(blob, filename) {
	// create a link and download a blob as a file
	if (navigator.msSaveBlob) { // IE 10+
		navigator.msSaveBlob(blob, filename);
	} else {
		var link = document.createElement("a");
		if (link.download !== undefined) { // feature detection
			// Browsers that support HTML5 download attribute
			var url = URL.createObjectURL(blob);
			link.setAttribute("href", url);
			link.setAttribute("download", filename);
			link.style.visibility = 'hidden';
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
		}
	}
}

function s2ab(s) {
	var buf = new ArrayBuffer(s.length);
	var view = new Uint8Array(buf);
	for (var i = 0; i != s.length; ++i) view[i] = s.charCodeAt(i) & 0xFF;
	return buf;
}

function _ajax_default_error_fn(jqXHR, textStatus, error) {
	console.error("Received error", error);
}

function _ajax_default_receive_fn(data, textStatus, jqXHR) {
	console.log("Received data", data)
}

// perform an appropriate ajax function. Usually just 
function perform_post(payload, url, success_fn=_ajax_default_receive_fn, error_fn=_ajax_default_error_fn, type="POST") {
	if(typeof payload !== 'string' && !(payload instanceof String)) {
		// payload is not string; attempt to convert 
		payload = JSON.stringify(payload);
	}
	$.ajax({
		type: type,
		url: url,
		data: payload, 
		contentType: "application/json",
		dataType: "json",
		success: success_fn,
		error: error_fn,
	});
}

function perform_get(url, success_fn=_ajax_default_receive_fn, error_fn=_ajax_default_error_fn, type="GET") {
	$.ajax({
		type: type,
		url: url,
		success: success_fn,
		error: error_fn,
	});
}

function build_wait_div(dot_count=5) {
	// TODO build a indicator with {dot_count} dot that fade in/out sequentially
}
