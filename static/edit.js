function set_buttons_state(working) {
	// set all buttons in respective bar with to disabled/enabled accordingly
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
	$.ajax({
		type: "GET",
		url: "rollback",
		success: function(data, textStatus, jqXHR) {
			if(data["result"]) {
				$("#io_result").removeClass("text-danger").addClass("text-success").text("Rollback done, old data had been loaded.");
				get_and_reupdate_question(event);
			} else {
				$("#io_result").removeClass("text-success").addClass("text-danger").text("Rollback failed.");
				console.log("Error: ", data["error"]);
			}
			set_buttons_state(false);
			//$(event.currentTarget).attr("disabled", false);
		},
		error: function(jqXHR, textStatus, error){
			console.log("Received error", error);
			$("#io_result").removeClass("text-success").addClass("text-danger").text("Rollback failed.");
			set_buttons_state(false);
			//$(event.currentTarget).attr("disabled", false);
		},
		// always: function() { $(event.currentTarget).prop("disabled", false); } // doesnt work
	})
}

// TODO allow confirmation when doing Import & Replace as well
// confirm deletion of a selected box. 
// Populate and show a modal as needed
function update_modal_delete(event) {
	$("#modal_body").text("Do you really want to delete the selected item?");
}

function perform_confirm_modal(event) {
	return delete_selected(event);
}

// delete the selected boxes. Sending the command and reload the data 
// should be called by perform_confirm_modal
function delete_selected(event) {
	set_buttons_state(true);
	var payload = JSON.stringify(get_selected_question_ids());
	$.ajax({
		type: "DELETE",
		url: "delete_questions",
		data: payload, 
		contentType: "application/json",
		dataType: "json",
		success: function(data, textStatus, jqXHR) {
			// console.log(data["questions"]);
			if(data["result"]) {
				$("#io_result").removeClass("text-danger").addClass("text-success").text("Deleted selected questions.");
				get_and_reupdate_question();
			} else {
				console.log("Received error:", data["error"]);
				$("#io_result").removeClass("text-success").addClass("text-danger").text("Deletion failed.");
			}
			set_buttons_state(false);
		},
		error: function(jqXHR, textStatus, error){
			console.log("Received error", error);
			set_buttons_state(false);
		},
	})
}
