// this section will bind with associated table (& edit modal if specified)

var edit_by_modal = true;
var full_edit = true; // if false, this will edit per field; if true, edit the whole basis of the question (question, answer1-4, correct_ids) including all the special variants.

// v1: edit inline
var currently_edited_cell_id = null;
var currently_edited_key = null;
var currently_edited_content = null;
function _focus_fn() {
	let edit_id = $(this).attr("qid");
	let edit_key = $(this).attr("key");
	if((edit_id != currently_edited_cell_id || edit_key != currently_edited_key)
		&& currently_edited_cell_id && currently_edited_key && currently_edited_content) {
		// change is registered; will attempt to propagate data 
		//console.log("Sending: ", currently_edited_cell_id, currently_edited_key, currently_edited_content);
		//alert("Check log for data supposed to be push");
		edit_question(currently_edited_cell_id, currently_edited_key, currently_edited_content); // using index0 for this.
		currently_edited_cell_id = edit_id;
		currently_edited_key = edit_key;
		currently_edited_content = null;
	} else {
		console.log("1st focus at ", edit_id, " recording edit.");
		currently_edited_cell_id = edit_id;
		currently_edited_key = edit_key;
		currently_edited_content = null;
	}
}
function _alias_input_fn() {
	$(this).trigger("change");
}
function _change_fn() {
	currently_edited_content = $(this).text();
}

// v2, edit by the associated modal
var current_edit_item = null;
var bounded_edit = false;
function _render_edit() {
	// retrieve, convert & create appropriate display element if there is MathJax/embedded image in the data. 
	let content = $("#edit_true_text").val();
	let display = $("#edit_display");
	display.empty();
	// console.log("Current content: ", content);
	if(content.includes("|||")) {
		// if has image; render them
		const pieces = content.split("|||");
		pieces.forEach(function (p) {
			p = p.trim();
			if(p) {
				if(p.startsWith("http")){ // hack to detect image
					display.append($("<img class=\"img-thumbnail\" style=\"max-width: 300px;\">").attr("src", p));
				} else { // TODO re-add the splitted value if exist (e.g is_single_equation)
					display.append($("<span>").text(p));
				}
			}
		});
	} else {
		display.text(content);
	}
	if(content.includes("\\(") || content.includes("\\)") || content.includes("$$")) {
		// if has MathJax; reload them.
		// MathJax.Hub.Queue(["TypeSet", MathJax.Hub, "edit_display"]);
		MathJax.typesetClear([display[0]]);
		MathJax.typesetPromise([display[0]]);
	}
}

function _open_edit_modal(index0, key, parent_cell) {
	// retrieve targetted data; populate the modal with it and then pops.
	let q = current_data[index0];
	currently_edited_cell_id = q["id"];
	currently_edited_key = key;
	current_edit_item = parent_cell;
	if(full_edit) {
		$("#edit_single_value").addClass("d-none"); $("#edit_full_question").removeClass("d-none");
		// populate
		["question", "answer1", "answer2", "answer3", "answer4", "variable_limitation"].forEach(function(field) {
			if(q[field] === undefined) return; // do not attempt to populate if missing
			$("#edit_" + field).val(q[field]);
		});
		$("#edit_answer_single_equation").val(q["answer1"]); // answer1 should always be available anyway 
		console.log($("#edit_correct_answer").find("input"));
		$("#edit_correct_answer").find("input").each(function() {
			let active = false;
			let answer_index = parseInt( $(this).attr("id").split("_")[3] );
			if(q["is_multiple_choice"]) {
				active = $.inArray(answer_index, q["correct_id"]) >= 0;
			} else {
				active = (answer_index === q["correct_id"]);
			}
			// console.log("check: ", $(this).attr("id").split("_")[3], answer_index, q["correct_id"], active);
			$(this).prop("checked", active);
		});
		// after filling; trigger the hiding depending on which variant of questions & convert it.
		var variant = "generic";
		["is_single_option", "is_single_equation", "is_fixed_equation"].forEach(function(special) {
			if(q[special]) {
				variant = special;
			}
		})
		switch_question_mode(null, enforce_variant=variant);
	} else {
		$("#edit_single_value").removeClass("d-none"); $("#edit_full_question").addClass("d-none").removeClass("d-flex");
		if(!bounded_edit) {
			console.log("1st edit modal triggered; binding function.");
			$("#edit_true_text").on("change input", _render_edit);
			bounded_edit = true;
		}
		$("#edit_single_value").show(); $("#edit_full_question").hide();
		$("#edit_true_text").val(q[key]);
		_render_edit();
	}
	$("#editModalTitle").text("Editing question " + currently_edited_cell_id.toString());
	$("#editModal").modal("show");
}

function _submit_edit_modal() {
	if(full_edit) {
		// depending on which tab had been used & which values had been modified, selectively send up the rest 
		let variant = $("#question_type_tab").find("button.active").attr("id").replace("_tab", "");
		console.log("variant:", variant);
		let question = current_data[currently_edited_cell_id];
		let new_question = {};
		["question", "answer1", "answer2", "answer3", "answer4", "variable_limitation"].forEach(function(field) {
			new_question[field] = $("#edit_" + field).val();
		});
		if(variant === "generic") { // generic will void undefined
			delete new_question["variable_limitation"];
		} else { 
			new_question[variant] = true;
			if(variant === "is_single_option" || variant === "is_single_equation") { // single option/equation will void 2-4 answers; plus retrieve 1 from "edit_answer_single_equation" instead 
			new_question["answer1"] = $("#edit_answer_single_equation").val();
			["answer2", "answer3", "answer4"].forEach(function(field) { delete new_question[field]; });
			}
		}
		let checkboxes = $("#edit_correct_answer").find("input").filter(function() { return $(this).prop("checked"); }); //.filter(cb => cb.prop("checked"));
		if(checkboxes.length > 1) {
			new_question["is_multiple_choice"] = true;
			new_question["correct_id"] = checkboxes.toArray().map( item => parseInt($(item).attr("id").split("_")[3]) );
		} else {
			new_question["is_multiple_choice"] = false;
			new_question["correct_id"] = parseInt( checkboxes.attr("id").split("_")[3] );
		}
		console.log("New question obj: ", new_question);
		edit_question_multiplefield(currently_edited_cell_id, new_question, question);
	} else {
		// when submitting; send the necessary data in #edit_true_text away 
		let content = $("#edit_true_text").val();
		console.log("Sending: ", currently_edited_cell_id, currently_edited_key, content);
		// alert("Check log for data supposed to be push");
		edit_question(currently_edited_cell_id, currently_edited_key, content); // using index0 for this.
		current_edit_item.text(content);
	}
	// voiding the rest & hide
	currently_edited_cell_id = null;
	currently_edited_key = null;
	current_edit_item = null;
	$("#editModal").modal("hide");
}

function update_cell_editable(cell, qid, key, index0) {
	if(edit_by_modal) {
		edit_button = $("<button>").attr("class", "btn btn-link").append($("<i>").attr("class", "bi bi-pen"));
		edit_button.on('click', () => _open_edit_modal(index0, key, cell));
		cell.append(edit_button);
		return cell;
	} else {
		converted_cell = cell.attr("contenteditable", "true").attr("qid", qid).attr("key", key);
		converted_cell.on('focus', _focus_fn).on('blur keyup paste', _alias_input_fn).on('change', _change_fn);
		return converted_cell;
	}
}
// regardless of mode; bind this to table.js's convert_to_editable
convert_to_editable = update_cell_editable;

function switch_question_mode(event, enforce_variant=undefined) {
	//console.log("Received event: ", event, "; target: ", event.currentTarget);
	//alert("Switched.");
	var current_tab, variant;
	if(enforce_variant) {
		// console.log("Question variant is set to ", enforce_variant)
		variant = enforce_variant;
		current_tab = $("#" + variant + "_tab");
	} else {
		event.preventDefault();
		current_tab = $(event.currentTarget);
		variant = current_tab.attr("id").replace("_tab", "");
	}
	//console.log("find button:", current_tab, " in ", $("#question_type_tab").find("button"));
	$("#question_type_tab").find("button").each(function() {
		let btn = $(this);
		//console.log("iterate btn: ", btn, "vs", current_tab, "=", btn[0] === current_tab[0]);
		if(btn[0] === current_tab[0]) {
			btn.addClass("active");
		} else {
			btn.removeClass("active");
		}
	});
	console.log("Switching to variant: ", variant);
	if(variant === "generic") { // all except "generic" will has variable_limitation
		$("#edit_limitation").addClass("d-none");
	} else {
		$("#edit_limitation").removeClass("d-none");
		if(variant !== "is_single_option") {
			$("#edit_variable_limitation_lbl").text("Variable Limitations");
		} else {
			$("#edit_variable_limitation_lbl").text("Pairings");
		}
	}

	if(variant === "is_single_equation" || variant === "is_single_option") { // is_single_equation | is_single_option will use the special answer box
		$("#edit_answer_set_1").addClass("d-none");
		$("#edit_answer_set_2").addClass("d-none");
		$("#edit_correct_answer").addClass("d-none");
		$("#edit_answer_single").removeClass("d-none");
	} else {
		$("#edit_answer_set_1").removeClass("d-none");
		$("#edit_answer_set_2").removeClass("d-none");
		$("#edit_correct_answer").removeClass("d-none");
		$("#edit_answer_single").addClass("d-none");
	}
}

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
	// console.log($("#export_link"))
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

// send editing signal for specific box. Only send the command.
// TODO on failure, revert the specific spot with appropriate data somehow; should be queryable from table.
function edit_question(qid, key, value) {
	var category = $("#category_dropdown").text();
	var payload = JSON.stringify({"id": qid, "field": key, "value": value})
	let success_fn = function(data, textStatus, jqXHR) {
		if(data["result"]) {
			$("#io_result").removeClass("text-danger").addClass("text-success").text("Question \"" + qid + "\" updated.");
		} else {
			$("#io_result").removeClass("text-success").addClass("text-danger").text("Question update failed. Please manually reset the page.");
		}
	};
	let error_fn = function(jqXHR, textStatus, error){
			console.log("Received error", error);
	};
	perform_post(payload, "modify_question?category=" + encodeURIComponent(category), success_fn=success_fn, error_fn=error_fn, type="POST");
} 

function edit_question_multiplefield(qid, new_question, old_question) {
	// parse the entire question object into json; if any field already matches the old question, discard it to lessen server workload.
	// after finishing; update the old question object in current_data too.
	for(const [key, value] of Object.entries(new_question)) {
		if(!value) continue; // just ignore 
		let old_value = old_question[key];
		if(typeof value !== typeof old_value) {
			// change in type (e.g convert to is_multiple_choice question.); keep
			continue;
		} else {
			if(typeof value === 'string' || value instanceof String) {
				if(value.trim() === old_value.trim()) {
					// trimmed version match; skip 
					delete new_question[key];
				}
			} else if(typeof value == "number") {
				if(value == old_value) {
					// value match; skip 
					delete new_question[key];
				}
			} // we could skip is_multiple_choice answer as well; but later.
		}
	}
	new_question["id"] = qid; // put the id in 
	["is_single_equation", "is_single_option", "is_fixed_equation"].forEach(function(field) {
		// these properties MUST be available always; to ensure question format is not screwed.
		if(new_question[field]) return;
		new_question[field] = false;
	})

	var category = $("#category_dropdown").text();
	var payload = JSON.stringify(new_question)
	let success_fn = function(data, textStatus, jqXHR) {
		if(data["result"]) {
			$("#io_result").removeClass("text-danger").addClass("text-success").text("Question \"" + qid + "\" updated.");
			// reaching here, we rewrite the data on current_data. TODO also reload the table item as well.
			$.extend(true, old_question, new_question);
		} else {
			$("#io_result").removeClass("text-success").addClass("text-danger").text("Question update failed. Please manually reset the page.");
		}
	};
	let error_fn = function(jqXHR, textStatus, error){
			console.log("Received error", error);
	};
	perform_post(payload, "modify_question?multiple_mode=true&category=" + encodeURIComponent(category), success_fn=success_fn, error_fn=error_fn, type="POST");
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

