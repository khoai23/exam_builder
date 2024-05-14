// provide appropriate update for the campaign 
 
var autorun_interval = null;

function toggle_autorun(event) {
	if(autorun_interval == null) {
		// switch on 
		autorun_interval = window.setInterval(function() {
			if(autorun_interval == null) return;
			perform_and_reload(event, "next");
		}, 2000)
	} else {
		// switch off
		clearInterval(autorun_interval);
		autorun_interval = null;
	}
}

function draw_polygon(polygon_data) {
	// draw the appropriate polygon on a <svg> tag; the data must be consistent with app.py data 
	var [x, y, w, h, points, attr] = polygon_data;
	var base = $("<svg>").attr("height", h).attr("width", w).css({"position": "absolute", "top": `${y}px`, "left": `${x}px`});
	// convert points into associating str 
	points = points.map(p => `${p[0]},${p[1]}`).join(" ");
	var poly = $("<polygon>").attr("points", points).css({"fill": attr["fg"], "stroke": attr["bg"], "stroke-width": attr["border_size"] ?? 1 });
	base.append(poly);
	// if exist a center; paste it in the polygon 
	if("center" in attr) {
		if("symbol" in attr) { // if has additional utf-8 symbols, print them with bigger size (24px)
			var symbol_wrapper = $("<g>").attr("font-size", 24).attr("fill", "black").attr("text-anchor", "middle");
			var symbol_label = $("<text>").attr("x", attr["center"][0]).attr("y", attr["center"][1] - 20).text(attr["symbol"]);
			symbol_wrapper.append(symbol_label);
			base.append(symbol_wrapper);
		}
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
		head = head.attr(k, v);
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
	// console.log(action);
	var url = "play";
	if(action == "next") {
		url += "?next=true";
	}
	var payload = ""; // post with no actual data; using GET will spawn whole webpage, whereas 
	var on_success = function(data, textStatus, jqXHR){
		if(data["result"]) {
			// if has key, allow access to the quiz thru the link(quasi-button)
			var quiz_button = $("#to_quiz_btn");
			if(data["quiz_key"]) {
				quiz_button.removeClass("disabled").attr("href", "campaign_quiz?key=" + data["quiz_key"]);
			} else {
				quiz_button.addClass("disabled").attr("href", "");
			}
			if(data["action_logs"]) {
				// new log had been created; put it to the `log` object as separate paragraph 
				let log_container = $("#log");
				data["action_logs"].forEach(function(log) {
					if(log.includes("<") && log.includes(">")) {
						// html-formatted; parse as new item by jquery to generate any sub-tag
						log_container.append($( "<p>" + log + "</p>"));
					} else {
						// unformatted; just append in as raw text
						log_container.append($("<p>").text(log));
					}
				});
				log_container.animate({ scrollTop: log_container.prop("scrollHeight")}, 1000);
			}
			// received data, reloading display elements 
			console.log("Received map data: ", data);
			reload_map(data["polygons"], data["arrows"]);
			if ("attacks" in data) {
				// phase is attack, update accordingly 
				load_attack_vectors(event, data["attacks"]);
				toggle_phase(event, "attack");
			} else if ("moves" in data) {
				load_movement_vectors(event, data["moves"]);
				toggle_phase(event, "move");
			} else if ("deploy" in data) {
				load_deployment_spots(event, data["deployments"])
				toggle_phase(event, "deploy");
			} else {
				console.log("No additional control allowed. TODO hide the entire control panel")
				toggle_phase(event, "hide");
			}
		} else {
			// failed, TODO revert failed changes back to default
			console.error("Failed to get phase data, error", data["error"]);
		}
	};
	perform_post(payload, url, success_fn=on_success);
}

function debug_campaign(event) {
	// just perform a setcoef action for now 
	var on_success = function(data, textStatus, jqXHR){
		if(data["result"]) {
			// should not 
		}
	};
	$.get("set_coef?coef=3", on_success)
}

function toggle_phase(event, phase_type) {
//	let is_attack = phase_type === "attack"
//	let is_deploy = phase_type === "deploy"
//	let is_move = phase_type === "move"
	//console.log(is_attack, is_deploy, is_move);
	["attack", "deploy", "move"].forEach(function(v, i) {
		if(v === phase_type) {
			$("#tab_" + v).addClass("active text-primary").removeClass("disabled");
			$("#" + v + "_content").show();
			// also rename the execute button on appropriate phase
			$("#execute_btn").text(v[0].toUpperCase() + v.slice(1).toLowerCase());
		} else {
			$("#tab_" + v).removeClass("active text-primary").addClass("disabled");
			$("#" + v + "_content").hide();
		}
	});
}

function load_attack_vectors(event, data) {
	// load attack vectors, each in a selector
	// multiple attacks can be selected, but they must have the same destination 
	var panel = $("#attack_content");
	// purge current content 
	panel.empty();
	// load new data into the panel 
	for (const [index, [sname, tname, sid, tid, max]] of Object.entries(data)) {
		let field = $("<li>").attr("id", "attack_field_" + index.toString()).attr("attack_source", sid).attr("attack_target", tid).attr("onclick", "toggle_attack_vector(event)").addClass("list-group-item");
		field.append($("<span>").append($("<b>").text(sname)));
		field.append($("<span>").text("\u2192"));
		field.append($("<span>").append($("<b>").text(tname)));
		let input = $("<input>").attr("type", "number").attr("min", 0).attr("max", max).addClass("form-control attack_amount");
		// inputs are disabled by default, until toggle allows it 
		input.prop("disabled", true);
		field.append(input);
		panel.append(field);
	}
}

function load_movement_vectors(event, data) {
	// load movement vectors also in selector; each correspond to one origin points
	// movement will have a limit of total units allowed out of each origin points. Crossing this value will grey out the submit button and add a red border for the selector 
	var panel = $("#move_content");
	// purge current content 
	panel.empty();
	for(const [index, [sname, sid, targets, max]] of Object.entries(data)) {
		let field = $("<li>").attr("id", "move_field_" + index.toString()).attr("move_source", sid).attr("max", max).addClass("list-group-item d-flex flex-row");
		// shared source 
		field.append($("<span>").text(`(${max.toString()})`));
		field.append($("<span>").text("from"));
		field.append($("<span>").append($("<b>").text(sname)));
		// splitted destination list - each correspond to a row
		// use a table to ensure shared inputbox 
		let table = $("<table>");
		// console.log("Expected destinations", targets); 
		for(const [tname, tid] of targets) { // iterate through targets
			let row = $("<tr>")
			// first cell, containing both arrow & target name
			let first_cell = $("<td>");
			first_cell.append($("<span>").text("\u2192"));
			first_cell.append($("<span>").append($("<b>").text(tname)))
			row.append( first_cell );
			// second cell, the input will also autoupdate state of the parent henceforth
			let input = $("<input>").attr("move_target", tid).attr("type", "number").attr("min", 0).attr("max", max).attr("onchange", "check_move_vectors(event)").addClass("form-control move_amount");
			row.append( $("<td>").append(input) );
			table.append(row);
		}
		field.append( table ); // $("<table>").append(table)
		panel.append(field);
	}
}

function toggle_attack_vector(event) {
	// an attack vector is toggled. 
	// If nothing has been selected yet, show all same-destination as green (included) and other as red (excluded). excluded fields are all disabled
	// If itself has been selected, return everything to default white and clear & disable all field
	// If itself had been excluded, do nothing. The toggle should only work on the same 
	let field = $(event.currentTarget);
	if(field.hasClass("list-group-item-success")) {
		// check if focusing the internal input 
		let field_input = field.find("input")[0];
		if(!field_input.isSameNode(document.activeElement)) {
			// not focused, return everything to default 
			$("#attack_content").find("[id^=attack_field_]").each(function(index){
				// remove the class
				$(this).removeClass("list-group-item-success list-group-item-danger");
				// deactivate internal input 
				$(this).find("input").prop("disabled", true);
			});
		}
		// else in focus, ignore
	} else if(field.hasClass("list-group-item-danger")) {
		console.log("Clicked on excluded, nothing happens");
	} else {
		// filter accordingly 
		let all_fields = $("#attack_content").find("[id^=attack_field_]"); 
		let target = field.attr("attack_target");
		console.log("Shared target: ", target);
		// field for sametarget - turn to green, and allow input
		all_fields.filter(function(i) { 
			return $(this).attr("attack_target") === target;
		}).addClass("list-group-item-success").find("input").prop("disabled", false);
		// field for different target - turn to red, no need to change hopefully
		all_fields.filter(function(i) { 
			return $(this).attr("attack_target") !== target;
		}).addClass("list-group-item-danger");
	}
}

function check_move_vectors(event) {
	// originate from an input field in a move "selector" 
	// assert that the sum of all requested do not exceed the maximum units available; if it does, visually indicate 
	let target_element = $(event.currentTarget);
	let field = target_element.parents("[id^=move_field_]");
	// iterate through all possible inputs and sum the requested units together
	var requested = 0;
	field.find("input").each(function(i) { 
		requested += parseInt($(this).val()) || 0; 
	});
	var valid_orders = requested < parseInt(field.attr("max"));
	console.log("rqt", requested, "avb", parseInt(field.attr("max")), "valid", valid_orders);
	if(valid_orders) {
		// format & enable appropriately 
		field.removeClass("list-group-item-danger");
	} else {
		field.addClass("list-group-item-danger");
	}
	// for execute_btn; check for all items in the list if any has the indicator class
	var has_error = !valid_orders || $("[id^=move_field_]").is(".list-group-item-danger");
	$("#execute_btn").prop("disabled", has_error);
}
