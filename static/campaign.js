// provide appropriate update for the campaign 
 
function draw_polygon(polygon_data) {
	// draw the appropriate polygon on a <svg> tag; the data must be consistent with app.py data 
	var [x, y, w, h, points, attr] = polygon_data;
	var base = $("<svg>").attr("height", h).attr("width", w).css({"position": "absolute", "top": `${y}px`, "left": `${x}px`});
	// convert points into associating str 
	points = points.map(p => `${p[0]},${p[1]}`).join(" ");
	var poly = $("<polygon>").attr("points", points).css({"fill": attr["fg"], "stroke": attr["bg"], "stroke-width": 1});
	base.append(poly);
	// if exist a center; paste it in the polygon 
	if("center" in attr) {
		if("name" in attr) { // if has polygon name, print it bolded (stroke-width) & 20px
			var name_wrapper = $("<g>").attr("font-size", 20).attr("fill", "black").attr("text-anchor", "middle");
			var name_label = $("<text>").attr("x", attr["center"][0]).attr("y", attr["center"][1]).text(attr["name"]);
			name_wrapper.css("stroke-width:.5;");
			name_wrapper.append(name_label);
			base.append(name_wrapper);
		}
		if("text" in attr) { // if has additional text, print it normally 16px
			var text_wrapper = $("<g>").attr("font-size", 16).attr("fill", "black").attr("text-anchor", "middle");
			var text_label = $("<text>").attr("x", attr["center"][0]).attr("y", attr["center"][1] + 20).text(attr["text"]);
			text_wrapper.append(text_label);
			base.append(text_wrapper);
		}
	}
	return base;
};

function draw_arrow(arrow_data, arrow_index) {
	// draw the appropriate arrow in a similar way
	var [x, y, w, h, attr] = arrow_data;
	var base = $("<svg>").attr("height", h).attr("width", w).css({"position": "absolute", "top": `${y}px`, "left": `${x}px`});
	// head of the arrow
	var head = $("<marker>").attr("id", `head${arrow_index}`);
	for (const [k, v] in Object.entries(attr["arrowhead"])) {
		head.attr(k, v);
	}
	var [hp1, hp2, hp3] = attr["arrowhead_poly"];
	let headpath = $("<path>").attr("d", `M ${hp1[0]} ${hp1[1]} L ${hp2[0]} ${hp2[1]} L ${hp3[0]} ${hp3[1]} z`).attr("fill", attr["color"]); 
	head.append(headpath);
	base.append( $("<defs>").append(head) );
	// line of the arrow 
	var path_points = "M " + attr["points"].map(p => p[1] !== null ? `Q ${p[1][0]},${p[1][1]} ${p[0][0]},${p[1][0]}` : `${p[0][0]},${p[0][1]}`).join(" ")
	var path = $("<path>").attr("d", path_points).attr("marker-end", `url(#head${arrow_index})`).attr("stroke", attr["color"]).attr("stroke-width", attr["thickness"]).attr("fill", "none");
	if("dash" in attr) {
		path.attr("stroke-dasharray", `${attr["dash"]},${attr["dash"]}`);
	}
	base.append(path);
	// console.log("Drawn", base, "with index ", arrow_index);
	return base;
}

function reload_map(poly_data, arrow_data) {
	// reload the polygons by re-drawing them on existing canvas 
	// wipe 
	var canvas = $("#canvas");
	canvas.empty(); 
	// redraw 
	poly_data.forEach(function(pld) {
		var polygon = draw_polygon(pld);
		canvas.append(polygon);
	});
	arrow_data.forEach(function(ard, i) {
		var arrow = draw_arrow(ard, i);
		canvas.append(arrow);
	});
	// reset html for entire canvas 
	canvas.html(canvas.html());
}


function perform_and_reload(event, action) {
	// performing an action, e.g NEXT, and receive appropriate updates 
	// use url 
	console.log(action);
	var url = "play";
	if(action == "next") {
		url += "?next=true";
	}
	var payload = ""; // post with no actual data; using GET will spawn whole webpage, whereas 
	var on_success = function(data, textStatus, jqXHR){
		if(data["result"]) {
			// received data, reloading display elements 
			console.log("Received map data: ", data);
			reload_map(data["polygons"], data["arrows"]);
		} else {
			// failed, TODO revert failed changes back to default
			console.error("Failed to get phase data, error", data["error"]);
		}
	};
	perform_post(payload, url, success_fn=on_success);
}
