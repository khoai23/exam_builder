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

function update_action_icon(core_icon, action_icon, action) {
	// depending on specific action, give the core_icon appropriate opacity.
	// TODO streamline it like `action_icons` above 
	if(action == "blink") {
		core_icon.addClass("animate-blink");
	} else {
		core_icon.removeClass("animate-blink");
		if(action == "inactive") {
			core_icon.css("opacity", "0.0"); // effectively hiding it
		} else if(action == "rout") {
			core_icon.css("opacity", "0.2")
		} else if(action == "hide") {
			core_icon.css("opacity", "0.5")
		} else {
			core_icon.css("opacity", "1.0")
		}
	}
	// depending on specific action, give the action_icon appropriate visual
	if(action_icons[action]) {
		// have associating action icon; the actual element should be swapped
		action_icon.removeClass().addClass("bi bi-" + action_icons[action]);
		action_icon.show()
	} else {
		// have no associating action icon, the element will be hidden 
		action_icon.hide()
	}
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
			if(!animation || current_script_step == 0) {
				unit.css("left", x);
				unit.css("top", y);
			} else {
				unit.animate({"left": x, "top": y}, 500) // animation finish in 0.5s
			}
		}
		// update action accordingly
		update_action_icon(unit, $("#" + unit_id + "_action"), action);
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

function choose_option(event, choice_str) {
	//alert("TODO implement. Chose option: '" + option_key + "'. Key to back-access: " + getUrlParameter("key"));
	let current_scenario_key = getUrlParameter("key");
	perform_get("interact_scenario?key=" + current_scenario_key + "&choice=" + choice_str, (data, textStatus, jqXHR) => {
		// on receiving data, redirect to the new scenario by appropriate response 
		redirect_link = data["link"];
		console.log("Received link, attempt to redirect to: ", redirect_link);
		window.location.href = redirect_link;
	})
}

function roll(event) {
	// alert("TODO implement. Must get roll result from the server." + "'. Key to back-access: " + getUrlParameter("key"))
	let current_scenario_key = getUrlParameter("key");
	perform_get("interact_scenario?key=" + current_scenario_key, (data, textStatus, jqXHR) => {
		// on receiving data, redirect to the new scenario by appropriate response 
		redirect_link = data["link"];
		console.log("Received link, attempt to redirect to: ", redirect_link);
		window.location.href = redirect_link;
	})
}
