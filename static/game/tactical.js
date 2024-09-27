/* The tactical map will run by a railroaded script for now; will upgrade to dynamic responses later.
 * */

// should be given the current script from server/jinja; at which point we should comment this out
// very simple - 1 offensive, 2 defensive, offensive defeated both sequentially.
var railroad_script = [
	{ "offensive": {1: [45, 15, 1.0, "move"]}, "defensive": {2: [50, 5, 0.25, "hold"], 3: [60, 60, 0.5, "hold"]} },
	{ "offensive": {1: [45, 10, 1.0, "attack"]}, "defensive": {2: [50, 5, 0.25, "defend"], 3: [60, 60, 0.5, "move"]} },
	{ "offensive": {1: [45, 10, 0.9, "hold"]}, "defensive": {2: [50, 5, 0.10, "rout"], 3: [60, 50, 0.5, "move"]} },
	{ "offensive": {1: [45, 10, 0.9, "move"]}, "defensive": {2: [55, 0, 0.10, "rout"], 3: [60, 40, 0.5, "move"]} },
	{ "offensive": {1: [50, 10, 0.9, "move"]}, "defensive": {2: [null, null, null, "rout"], 3: [60, 30, 0.5, "move"]} },
	{ "offensive": {1: [50, 20, 0.9, "move"]}, "defensive": {2: [null, null, null, "rout"], 3: [60, 20, 0.5, "move"]} },
	{ "offensive": {1: [53, 20, 0.9, "attack"]}, "defensive": {2: [null, null, null, "rout"], 3: [58, 20, 0.5, "attack"]} },
	{ "offensive": {1: [55, 20, 0.75, "attack"]}, "defensive": {2: [null, null, null, "rout"], 3: [60, 20, 0.4, "defend"]} },
	{ "offensive": {1: [55, 20, 0.75, "attack"]}, "defensive": {2: [null, null, null, "rout"], 3: [60, 20, 0.4, "defend"]} },
	{ "offensive": {1: [58, 20, 0.55, "attack"]}, "defensive": {2: [null, null, null, "rout"], 3: [60, 25, 0.2, "defend"]} },
	{ "offensive": {1: [58, 20, 0.15, "attack"]}, "defensive": {2: [null, null, null, "rout"], 3: [60, 25, 0.1, "rout"]} },
	{ "offensive": {1: [55, 20, 0.15, "hold"]}, "defensive": {2: [null, null, null, "rout"], 3: [null, null, null, "rout"]} },
];

var current_script_step = -1;
var current_run_id = null;

var action_icons = {
	"move": "arrows-move",
	"attack": "exclamation-diamond",
	"defend": "shield-exclamation",
	"hide": "eye-slash",
	"rout": "x-lg",
	"hold": "hourglass"
}

function update_action_icon(item, action) {
	// depending on specific action, give the item appropriate icon 
	item.removeClass().addClass("bi bi-" + action_icons[action]);
}

function nextScriptStep(loopback=true, animation=true) {
	current_script_step += 1;
	if(current_script_step >= railroad_script.length) {
		if(loopback) {
			current_script_step = 0; // allow loopback, start with 0 again
		} else {
			return false; // skip the step; TODO unload itself from the interval
		}
	}
	//console.log("Running railroaded step ", current_script_step);
	// move everything to their specific location.
	let step_data = railroad_script[current_script_step];
	for (const [unit_id, [x, y, strength, action]] of Object.entries(step_data["offensive"])) {
		let unit = $("#" + unit_id);
		if(x === null || y === null || strength === null) {
			// unit have left the board and should be hidden
			unit.hide();
		} else {
			// unit is still active; move to necessary positions. TODO strength indicator. TODO action indicator. TODO movement animation
			unit.show();
			// when hiding, set opacity to 50%; else it's 100%
			unit.css("opacity", action == "rout" ? "0.2" : action == "rout" ? "0.5" : "1.0" )
			if(!animation || current_script_step == 0) {
				unit.css("left", x);
				unit.css("top", y);
			} else {
				unit.animate({"left": x, "top": y}, 500) // animation finish in 0.5s
			}
		}
		// update action accordingly
		update_action_icon($("#" + unit_id + "_action"), action);
	}
	for (const [unit_id, [x, y, strength, action]] of Object.entries(step_data["defensive"])) {
		let unit = $("#" + unit_id);
		if(x === null || y === null || strength === null) {
			// unit have left the board and should be hidden
			unit.hide();
		} else {
			// unit is still active; move to necessary positions. TODO strength indicator. TODO action indicator. TODO movement animation
			unit.show();
			unit.css("opacity", action == "hide" ? "0.5" : "1.0" )
			if(!animation || current_script_step == 0) {
				unit.css("left", x);
				unit.css("top", y);
			} else {
				unit.animate({"left": x, "top": y}, 500) // animation finish in 0.5s
			}
		}
		// update action accordingly
		update_action_icon($("#" + unit_id + "_action"), action);
	}
}

function toggle_railroad_script(event, interval=1000) {
	console.log("Toggling railroad_script; interval(if any): ", interval);
	if(current_run_id === null) {
		// currently disabled; switch on 
		current_run_id = setInterval(nextScriptStep, interval);
	} else {
		// currently enabled; switch off 
		clearInterval(current_run_id);
		current_run_id = null;
	}
}

$(document).ready(toggle_railroad_script);
//toggle_railroad_script();
