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
	"hold": "hourglass",
	"recon": "binoculars",
	"working": "hammer",
	"working-hide": "hammer",
	"planning": "clipboard",
	"approve": "clipboard-check",
	"disapprove": "clipboard-x",
	"aid-medic": "bandaid",
	"rest": "cup-hot",
	"rest-hide": "cup-hot",
	"retreat": "escape",
}

function update_action_icon(core_icon, action_icon, action) {
	// depending on specific action, give the core_icon appropriate opacity.
	// TODO streamline it like `action_icons` above 
	if(action == "blink") {
		core_icon.addClass("animate-blink");
		core_icon.css("opacity", "1.0")
	} else {
		core_icon.removeClass("animate-blink");
		if(action == "inactive") {
			core_icon.css("opacity", "0.0"); // effectively completely hiding it
		} else if(action == "rout") {
			core_icon.css("opacity", "0.2")
		} else if(action.includes("hide")) { // if work in secret, make it transparent
			core_icon.css("opacity", "0.5")
		} else {
			core_icon.css("opacity", "1.0")
		}
	}
	// depending on specific action, give the action_icon appropriate visual
	if(action_icons[action]) {
		// have associating action icon; the actual element should be swapped. TODO don't disrupt it if it's correct?
		action_icon.removeClass().addClass("bi bi-" + action_icons[action]);
		action_icon.show()
		if(action.includes("working") || action.includes("rest") ) { // also allow action icon to blink on specific ones
			action_icon.addClass("animate-blink");
		}
	} else {
		// have no associating action icon, the element will be hidden 
		action_icon.hide()
	}
}

var nextStepSuspended = false;
var scriptLoopback = false;

function nextScriptStep(script, animation=true, force_next_step=false) {
	if(nextStepSuspended && !force_next_step) {
		return; // this will be governed by autorun. When autorun is enabled, this block does not execute. When autorun is disabled, this function will only be available with force_next_step deliberately set to True
	}
	if(current_script_step >= script.length-1) {
		if(scriptLoopback) {
			current_script_step = 0; // allow loopback, start with 0 again
		} else {
			return false; // skip the step; TODO unload itself from the interval
		}
	} else {
		current_script_step += 1;
	}
	$("#current_step").text(current_script_step);
	//console.log("Running railroaded step ", current_script_step);
	// move everything to their specific location.
	let step_data = script[current_script_step];
	for (const [unit_id, [x, y, strength, action]] of Object.entries(step_data)) {
		let unit = $("#" + unit_id);
		if(x === null || y === null) {
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

var go_next_section = roll; // they are the same - just send up a signal to continue

// this concern editing, updating the scenario with the interactions on screens

var editable = false;
var editable_ids = null;

var current_edit_item = null;

function bind_all_existing_item() {
	// bind all the relevant items on the control board to reflect inner control 
	$("#checkbox_autorun").on("click", function() {
		// autorun the sequence accordingly. Should set continuation flag and stop interval fn from executing
		let autorun_is_active = $("#checkbox_autorun").is(":checked");
		nextStepSuspended = !autorun_is_active; 
		// also disabling/enabling increment/decrement step as autorun is moving
		$("#btn_previous_step").prop("disabled", autorun_is_active);
		$("#btn_next_step").prop("disabled", autorun_is_active);
	});

	$("#checkbox_loopback").on("click", function() {
		// just enable the flag to allow loopback
		scriptLoopback = $("#checkbox_loopback").is(":checked");
	});
	
	// populate the selectors with appropriate options.
	let action_selector = $("#action_selector");
	action_selector.append($("<option>").attr("value", "use_above").text("Use prior state"));
	for (const [action, icon_cue] of Object.entries(action_icons)) {
		action_selector.append($("<option>").attr("value", action).text(action));
	}

	$("#btn_next_step").on("click", function() {
		let script = railroad_script ? railroad_script : current_preview_script;
		if(!script) {
			// No valid script; this will do nothing.
			console.log("No script; cannot move to next step.", railroad_script, current_preview_script);
			return
		}
		nextScriptStep(script, false, true); // No animation & bypassing the autorun's blocker
	});

	$("#btn_previous_step").on("click", function() {
		let script = railroad_script ? railroad_script : current_preview_script;
		if(!script) {
			// No valid script; this will do nothing.
			console.log("No script; cannot move to previous step.", railroad_script, current_preview_script);
			return
		}
		if(current_script_step <= 0) {
			console.log("Script already reached first position; cannot backtrack any further.");
			return
		}
		current_script_step -= 2;
		nextScriptStep(script, false, true); // No animation & bypassing the autorun's blocker
	});

	let update_mock_icon = function() {
		// on changes of items that is relevant to the display of the icon, update all the necessary properties 
		let core_icon_cls = $("#core_icon").val();
		$("#mockup_icon").removeClass().addClass("bi bi-" + core_icon_cls);
		let rank_icon_cls = $("#rank_icon").val();
		if(rank_icon_cls) {
			$("#mockup_icon_rank").removeClass().addClass("bi bi-" + rank_icon_cls).show();
		} else {
			$("#mockup_icon_rank").hide();
		}
		let action = $("#action_selector").val();
		// TODO dim instead of complete hide in the editable mode
		update_action_icon($("#mockup_icon"), $("#mockup_icon_action"), action);
	};
	$("#core_icon").on("change", update_mock_icon);
	$("#action_selector").on("change", update_mock_icon);
	$("#rank_icon").on("change", update_mock_icon);

	$("#btn_update_current").on("click", update_unit_at_step);
	$("#btn_unselect_unit").on("click", unselect_unit);

	// synchronize the UI element with their appropriate variables
	unselect_unit();
	$("#checkbox_autorun").prop("checked", !nextStepSuspended);
	$("#checkbox_loopback").prop("checked", scriptLoopback);


	// bind the appropriate function to show the properties being broadcasted; this last even after mouseup.
	// TODO properly disengage the item after some time to allow addition 
	var class_icon_regex = /bi\-([\w\d\-]+)/g
	dragStartCallback = function (element) {
		current_edit_item = element;
		let unit_id = current_edit_item.attr("id");
		$("#core_icon").val(current_edit_item.attr("class").match(class_icon_regex)[0].replace("bi-", ""));
		let rank_item = $("#" + unit_id + "_rank");
		// TODO load the actual info from the json instead
		if(rank_item.length && rank_item.is(":visible")) {
			// has a visible rank item; rank_icon will be populated.
			$("#rank_icon").val(rank_item.attr("class").match(class_icon_regex)[0].replace("bi-", ""));
		} else {
			$("#rank_icon").val("");
		}
		// retrieve the appropriate action from the railroading mechanism, and set the action accordingly
		let script = railroad_script ? railroad_script : current_preview_script;
		if(!script || current_script_step < 0) {
			// ideally, even with the failure of properly enabled script, the selector will still be wired on the values currently assigned to the actual icon. TODO later though
			//let status_item = $("#" + unit_id + "_action");
			//$("#action_icon").val(status_item.attr("class"));
		} else {
			console.log(script, current_script_step, unit_id);
			// valid script & valid step, extract appropriate action being used and select the appropriate one from that dropdown
			let step_value = script[current_script_step > script.length ? script.length-1 : current_script_step][unit_id];
			if(step_value === undefined) { // step data is unspecified; item is keeping the above state.
				action = "use_above"
			} else {
				action = step_value[3];
			}
			$("#action_selector").val(action);
		}
		// also enable the update button & disable the add function
		$("#btn_add_new_unit").prop("disabled", true);
		$("#btn_update_current").prop("disabled", false);
	}
	// bind the appropriate function to reflect necessary X/Y coordinates
	dragPerformCallback = function (element, offset) {
		$("#x_coordinate").val(offset.left);
		$("#y_coordinate").val(offset.top);
	}
	// now bind all items with appropriate ids with generalized drag & drop 
	editable_ids.forEach(i => {
		let item = $("#"+i);
		// console.log("Adding draggable for", item);
		setElementDragable(item);
	});
}

// dynamic repopulation. TODO transfer the current jinja embedded-in-page data into this one, by 1st download the template, then 2nd repopulate it with the javascript functionality

function update_unit_at_step() {
	// function will be triggered for an existing valid entity (current_edit_item), a valid step (current_script_step) and optionally the appropriate cue of the current running script
	// write the step data being edited into the appropriate spot 
	if(!current_edit_item) {
		console.log("No selected item to update; action cannot be run.");
		return;
	}
	let script = null;
	let preview_choice = null;
	if(railroad_script) {
		script = railroad_script;
	} else if(current_preview_script) {
		script = current_preview_script;
		preview_choice = current_preview_choice;
	} else {
		console.log("Script to try editing doesn't exist, action cannot be run.");
		return
	}
	if(current_script_step < 0 || current_script_step >= script.length) {
		console.log("Current step is incorrect; action cannot be performed.")
	}
	let target_script_step = script[current_script_step];
	let target_id = current_edit_item.attr("id");
	let action_type = $("#action_selector").val();
	// TODO support full-hide by assigning nulls
	if(action_type == "use_above") {
		// using the previous step's data (change nothing); delete the id from the dictionary.
		delete target_script_step[target_id];
		console.log("Deleted the step ", current_script_step, " as obj ", target_script_step, " & id; this will use the prior status as-is", target_id);
	} else {
		// using a specific action; overwrite that id with new data.
		// ideally x/y should always be populated; but in case it doesn't, take the actually visible current positions on board
		let x = parseFloat($("#" + target_id).css("left"));
		let y = parseFloat($("#" + target_id).css("top"));
		let strength = 100; // TODO actually update this 
		target_script_step[target_id] = [x, y, strength, action_type];
		console.log("Updated the step ", current_script_step, " as obj ", target_script_step, " with ", target_script_step[target_id]);
	}
}

function unselect_unit() {
	// unhook the current_edit_item; wipe the entire section, allow Add if the step is 0 and disable Update.
	["x_coordinate", "y_coordinate", "core_icon", "rank_icon", "action_selector"].forEach(id => $("#" + id).val(""));
	current_edit_item = null;
	$("#btn_add_new_unit").prop("disabled", current_script_step === 0);
	$("#btn_update_current").prop("disabled", true);
}

function submit_script_change() {
	// sending the appropriate script change up to be considered by the scenario.
	alert("Fill in later.")
}
