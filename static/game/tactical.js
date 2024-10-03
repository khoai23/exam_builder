/* The tactical map will run by a railroaded script for now; will upgrade to dynamic responses later.
 * */

//// RAILROAD (STATIC) SECTION

// should be given the current script from server/jinja; at which point we should comment this out
// very simple - 1 offensive, 2 defensive, offensive defeated both sequentially.
var railroad_script = null;

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

function nextScriptStep(script, loopback=true, animation=true) {
	current_script_step += 1;
	if(current_script_step >= script.length) {
		if(loopback) {
			current_script_step = 0; // allow loopback, start with 0 again
		} else {
			return false; // skip the step; TODO unload itself from the interval
		}
	}
	//console.log("Running railroaded step ", current_script_step);
	// move everything to their specific location.
	let step_data = script[current_script_step];
	for (const [unit_id, [x, y, strength, action]] of Object.entries(step_data)) {
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
}

function toggle_railroad_script(event, interval=1000) {
	if(!railroad_script) {
		console.error("No railroad script available, this function (toggle_railroad_script) cannot be executed.");
		return;
	}
	console.log("Toggling railroad_script; interval(if any): ", interval);
	if(current_run_id === null) {
		// currently disabled; switch on 
		current_run_id = setInterval( () => nextScriptStep(railroad_script), interval);
	} else {
		// currently enabled; switch off 
		clearInterval(current_run_id);
		current_run_id = null;
	}
}

//// INTERACTIVE CHOICE SECTION

var choice_script = null;
var current_preview_script = null;
var current_preview_choice = null;

function switch_script_choice_preview(event, option_key, interval=1000) {
	if(!choice_script) {
		console.error("No choice script available, this function (switch_script_choice_preview) cannot be executed.");
	}
	// should be triggered on hovering - if currently previewing the same thing, do nothing; if not, switch over to that instead
	if(option_key != current_preview_choice) {
		current_preview_choice = option_key;
		current_preview_script = choice_script["initial"].concat(choice_script[option_key]);
		if(current_run_id) {
			clearInterval(current_run_id);
		}
		current_run_id = setInterval( () => nextScriptStep(current_preview_script), interval );
		current_script_step = -1;
		console.log("Switched over to previewing for choice '" + option_key + "'. Script: ", current_preview_script);
	}
}

function choose_option(event, option_key) {
	alert("TODO implement. Chose option: '" + option_key + "'.");
}
