function set_modifiers_state(enable) {
	// set the modifier (swap category, add tag, remove tag, delete) to appropriate state
	$("#modify_bar").find("button").prop("disabled", !enable);
	$("#new_tag_field").prop("disabled", !enable);
	if(!enable){
		$("#removable_tags").hide(); // always hide when nothing selected
	}
}

function set_buttons_state(working) {
	// set all mass buttons (import, export, rollback) to disabled/enabled accordingly
	// also switch the spinner and text depending on which
	// TODO set spinner color
	if(working){
		$("#button_bar").find("button").prop("disabled", true);
		$("#spinner").show();
		$("#io_result").hide();
	} else {
		$("#button_bar").find("button").prop("disabled", false);
		$("#spinner").hide();
		$("#io_result").show();
	}
}

var replacement_mode = false;
function choose_file(event, mode) {
	replacement_mode = mode;
	$("#import_file").click();
}

function submit_file(event) {
// $(document).on("ready", function() {
//	console.log("Attempt override submit.")
	//$(event.currentTarget).attr("disabled", true);
	var form = $("#import_form");
	var actionUrl = form.attr('action') + "?replace=" + replacement_mode.toString();
	var data = new FormData(form[0])
	console.log("Submitting: ", data);
	set_buttons_state(true);
	$.ajax({
		type: "POST",
		url: actionUrl,
		data: data,
		processData: false,
		contentType: false,
		success: function(data, textStatus, jqXHR) {
			console.log("Form submitted: ", data);
			if(data["result"]) {
				$("#io_result").removeClass("text-danger").addClass("text-success").text("Import done, data reloaded.").show();
				//$(event.currentTarget).attr("disabled", false);
				get_and_reupdate_question(event);
				external_update_filter();
			} else {
				$("#io_result").removeClass("text-success").addClass("text-danger").text("Import failed; error: " + data["error"]).show();
			}
			set_buttons_state(false);
		},
		error: function(jqXHR, textStatus, error){
			console.log("Received error", error);
			$("#io_result").removeClass("text-success").addClass("text-danger").text("Import failed.")
			//$(event.currentTarget).attr("disabled", false);
			set_buttons_state(false);
		},
		// always: function() { $(event.currentTarget).prop("disabled", false); } // doesnt work
	});
}

function export_file(event) {
	// simply transfer the click to the link 
	$("#export_link").click();
}

function rollback(event) {
	//$(event.currentTarget).attr("disabled", true);
	set_buttons_state(true);
	var category = $("#category_dropdown").text();
	let success_fn = function(data, textStatus, jqXHR) {
		if(data["result"]) {
			$("#io_result").removeClass("text-danger").addClass("text-success").text("Rollback done, old data had been loaded.");
			get_and_reupdate_question(event);
		} else {
			$("#io_result").removeClass("text-success").addClass("text-danger").text("Rollback failed.");
			console.log("Error: ", data["error"]);
		}
		set_buttons_state(false);
		//$(event.currentTarget).attr("disabled", false);
	}; 
	let error_fn = function(jqXHR, textStatus, error){
		console.log("Received error", error);
		$("#io_result").removeClass("text-success").addClass("text-danger").text("Rollback failed.");
		set_buttons_state(false);
		//$(event.currentTarget).attr("disabled", false);
	}
	perform_get("rollback?category=" + encodeURIComponent(category), success_fn=success_fn, error_fn=error_fn)
}

// TODO allow confirmation when doing Import & Replace as well
// confirm deletion of a selected box. 
// Populate and show a modal as needed 
var modal_action = null; 
var modal_target = null;
function update_modal_delete(event) {
	modal_action = "delete";
	modal_target = null
	$("#modal_body").empty();
	$("#modal_body").text("Do you really want to delete the selected item?");
}

function update_modal_swap_category(event) {
	modal_action = "swapcat";
	var target_category = $(event.currentTarget).text().trim();
	modal_target = target_category;
	$("#modal_body").html("Do you want to swap to category <b>" + target_category + "</b>?");
	$("#confirmation_modal").modal("show");
}

function update_modal_add_tag(event) {
	modal_action = "addtag";
	var expected_tag = $("#new_tag_field").val().trim();
	modal_target = expected_tag;
//	console.log("Tagging in as: ", expected_tag);
	$("#modal_body").html("Do you want to add a new tag <b>" + expected_tag + "</b>?");
	$("#confirmation_modal").modal("show");
}

function update_modal_remove_tag(event) {
	modal_action = "removetag";
	var expected_tag = $(event.currentTarget).text().trim();
	modal_target = expected_tag;
	$("#modal_body").html("Do you want to delete a tag <b>" + expected_tag + "</b>?");
	$("#confirmation_modal").modal("show");
}

function perform_confirm_modal(event) {
	if(modal_action === "delete") {
		return delete_selected();
	} else if(modal_action === "swapcat") {
		return swap_category(modal_target);
	} else if(modal_action === "addtag") {
		return add_tag(modal_target);
	} else if(modal_action === "removetag") {
		return remove_tag(modal_target);
	} else {
		console.log("Unrecognized action", modal_action);
	}
}

// delete the selected boxes. Sending the command and reload the data 
// should be called by perform_confirm_modal 
// no need to show the modal manually through jquery; 
function delete_selected() {
	set_buttons_state(true);
	var category = $("#category_dropdown").text();
	var payload = JSON.stringify(get_selected_question_ids());
	let success_fn = function(data, textStatus, jqXHR) {
		if(data["result"]) {
			$("#io_result").removeClass("text-danger").addClass("text-success").text("Deleted selected questions.");
			get_and_reupdate_question();
		} else {
			console.log("Received error:", data["error"]);
			$("#io_result").removeClass("text-success").addClass("text-danger").text("Deletion failed.");
		}
		set_buttons_state(false);
	};
	let error_fn = function(jqXHR, textStatus, error){
			console.log("Received error", error);
			set_buttons_state(false);
	};
	// post through DELETE hardpoint
	perform_post(payload, "delete_questions?category=" + encodeURIComponent(category), success_fn=success_fn, error_fn=error_fn, type="DELETE");
}

function swap_category(new_category) {
	set_buttons_state(true);
	var category = $("#category_dropdown").text();
	var payload = JSON.stringify(get_selected_question_ids());
	let success_fn = function(data, textStatus, jqXHR) {
		if(data["result"]) {
			$("#io_result").removeClass("text-danger").addClass("text-success").text("Swapped category.");
			get_and_reupdate_question();
		} else {
			console.log("Received error:", data["error"]);
			$("#io_result").removeClass("text-success").addClass("text-danger").text("Removed category.");
		}
		set_buttons_state(false);
	};
	let error_fn = function(jqXHR, textStatus, error){
			console.log("Received error", error);
			set_buttons_state(false);
	};
	perform_post(payload, "swap_category?from=" + encodeURIComponent(category) + "&to=" + encodeURIComponent(new_category), success_fn=success_fn, error_fn=error_fn);
}

function add_tag(new_tag) {
	set_buttons_state(true);
	var category = $("#category_dropdown").text();
	var payload = JSON.stringify(get_selected_question_ids());
	let success_fn = function(data, textStatus, jqXHR) {
		if(data["result"]) {
			$("#io_result").removeClass("text-danger").addClass("text-success").text("Question tag updated.");
			get_and_reupdate_question();
		} else {
			console.log("Received error:", data["error"]);
			$("#io_result").removeClass("text-success").addClass("text-danger").text("Question tag adding failed.");
		}
		set_buttons_state(false);
	};
	let error_fn = function(jqXHR, textStatus, error){
			console.log("Received error", error);
			set_buttons_state(false);
	};
	perform_post(payload, "add_tag?category=" + encodeURIComponent(category) + "&tag=" + encodeURIComponent(new_tag), success_fn=success_fn, error_fn=error_fn);
}

function remove_tag(new_tag) {
	set_buttons_state(true);
	var category = $("#category_dropdown").text();
	var payload = JSON.stringify(get_selected_question_ids());
	let success_fn = function(data, textStatus, jqXHR) {
		if(data["result"]) {
			$("#io_result").removeClass("text-danger").addClass("text-success").text("Question tag removed.");
			get_and_reupdate_question();
		} else {
			console.log("Received error:", data["error"]);
			$("#io_result").removeClass("text-success").addClass("text-danger").text("Question tag removal failed.");
		}
		set_buttons_state(false);
	};
	let error_fn = function(jqXHR, textStatus, error){
			console.log("Received error", error);
			set_buttons_state(false);
	};
	perform_post(payload, "remove_tag?category=" + encodeURIComponent(category) + "&tag=" + encodeURIComponent(new_tag), success_fn=success_fn, error_fn=error_fn);
}

// setup the appropriate function for table
selector_update_function = function(event) {
	// console.log("selector_update_function triggered");
	let tagbox = $("#removable_tags");
	// update fields accordingly 
	var checklist = $("#question_table").find("[id^=use_question_]");
	var checked = checklist.filter((i, it) => it.checked);
	if(checked.length === 0) { // always setup the bar depending on how many selector updated
		// console.log("disabled (no box)")
		set_modifiers_state(false);
		return;
	} else {
		// console.log("enabled (w/ box)")
		set_modifiers_state(true)
	}
	// backrefer to the next tag list 
	var tag_fields = checked.parent().prev();
	// select all buttons, filter as field
	var tags = new Set(tag_fields.find("button").map((i, it) => $(it).text().trim()));
	if(tags.length == 0) {
		// found no appropriate tag; also hide the bar away 
		$("#removable_tags").hide();
		return;
	} else {
		// there are appropriate tag, display 
		$("#removable_tags").show();
	}
	// create appropriate boxes.
	// check all children for existing tags 
	tagbox.children().each(function(index, item){
		let text = $(item).text().trim();
		if( tags.has(text) ) {
			// current box is part of acceptable tags; remove it from the set
			tags.delete(text);
		} else {
			// current box is old tag; throw the box away 
			$(item).remove();
		}
	});
	// tagbox.empty();
	tags.forEach(function(val) {  
		// console.log("deleter: ", val);
		// all remaining tags will get a corresponding button with close icon
		let new_button = $("<button>").addClass("btn btn-outline-danger").attr("onclick", "update_modal_remove_tag(event)").text(val).append($("<span class=\"bi-x\">"));
		tagbox.append(new_button);
	});
}

category_update_function = function(categories, selected) {
	// console.log("category_update_function triggered");
	// update swapper 
	var swapper = $("#swap_category_dropdown_menu");
	swapper.empty();
	categories.forEach(function(it) {
		// console.log("swapper: ", it);
		swapper.append($("<button>").addClass("btn btn-link dropdown-item").attr("onclick", "update_modal_swap_category(event)").text(it));
	});
	// also force the modifier to disabled when the category got updated 
	set_modifiers_state(false);
}

