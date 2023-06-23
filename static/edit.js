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
	$.ajax({
		type: "POST",
		url: actionUrl,
		data: data,
		processData: false,
		contentType: false,
		success: function(data, textStatus, jqXHR) {
			console.log("Form submitted: ", data);
			$("#io_result").removeClass("text-danger").addClass("text-success").text("Import done, data reloaded.");
			//$(event.currentTarget).attr("disabled", false);
			get_and_reupdate_question(event);
		},
		error: function(jqXHR, textStatus, error){
			console.log("Received error", error);
			$("#io_result").removeClass("text-success").addClass("text-danger").text("Import failed.")
			//$(event.currentTarget).attr("disabled", false);
		},
		// always: function() { $(event.currentTarget).prop("disabled", false); } // doesnt work
	});
}

function rollback(event) {
	//$(event.currentTarget).attr("disabled", true);
	$.ajax({
		type: "GET",
		url: "rollback",
		success: function(data, textStatus, jqXHR) {
			if(data["result"]) {
				$("#io_result").removeClass("text-danger").addClass("text-success").text("Rollback done, old data had been loaded.");
				get_and_reupdate_question(event);
			} else {
				$("#io_result").removeClass("text-success").addClass("text-danger").text("Rollback failed.")
				console.log("Error: ", data["error"]);
			}
			//$(event.currentTarget).attr("disabled", false);
		},
		error: function(jqXHR, textStatus, error){
			console.log("Received error", error);
			$("#io_result").removeClass("text-success").addClass("text-danger").text("Rollback failed.")
			//$(event.currentTarget).attr("disabled", false);
		},
		// always: function() { $(event.currentTarget).prop("disabled", false); } // doesnt work
	})
}

function get_and_reupdate_question(event, with_duplicate = true) {
	//$(event.currentTarget).attr("disabled", true);
	$.ajax({
		type: "GET",
		url: "questions?with_duplicate=" + with_duplicate.toString(),
		success: function(data, textStatus, jqXHR) {
			// console.log(data["questions"]);
			reupdate_questions(data["questions"]);
		},
		error: function(jqXHR, textStatus, error){
			console.log("Received error", error);
		},
	})
}

// upon successful update, rebuild the table accordingly
function reupdate_questions(data, clear_table = true) {
	var i = 0
	if(clear_table) {
		// if clear table, delete everything and re-show 
		$("tbody").empty();
	} else {
		// if not, only update the ones that aren't at the table 
		i = $("tbody").find("tr").length;
	}
	// regardless of mode; inserting from start-index to end of data 
	table_body = $("tbody");
	for(; i < data.length; i++) {
		let q = data[i];
		// console.log("Question: ", q);
		let id_cell = $("<td>").text(q["id"]);
		if(q["has_duplicate"] !== undefined) {
			id_cell.addClass("table-warning");
		} else if(q["duplicate_of"] !== undefined) {
			// duplicate_of may point to 0
			// TODO allow click to jump to the target row; or to show only the source & target ala Category
			id_cell.addClass("table-danger");
		}
		let row = $("<tr>").append([
			id_cell,
			$("<td>").text(q["question"])
		]);
		if(data[i]["is_single_equation"]) {
			row.append($("<td colspan='5'>").text(q["answer1"]));
		} else {
			let answers = [];
			var correct_ids = q["correct_id"];
			var is_multiple_choice = true;
			if(!Array.isArray(correct_ids)) { // not multiple, convert to array
				is_multiple_choice = false;
				correct_ids = [correct_ids];
			}
			// for each answer, create appropriate td cell
			// console.log("Correct: ", correct_ids);
			for(let j=1; j<=4; j++) {
				let answer = q["answer" + j.toString()];
				if(answer.includes("|||")) {
					// is image variant; put into img tag and put inside
					answer = answer.replaceAll("|||", "");
					answers.push($("<td>").append(
						$("<img class=\"img-thumbnail\" style=\"max-width: 300px;\">").attr("src", answer)
					));
				} else {
					// is text variant, push in directly
					answers.push($("<td>").text(answer));
				}
				if(correct_ids.includes(j)) {
					answers[answers.length-1].addClass(is_multiple_choice ? "table-info" : "table-success");
				}
			}
			// append everything 
			row.append(answers);
			// correct question will be added in similar format to python tuple (wrapped in bracket, separated by comma)
			if(is_multiple_choice){
				row.append($("<td>").text("(" + correct_ids.join(",") + ")"));
			} else {
				row.append($("<td>").text(correct_ids[0]));
			}
		}
		// category, tag, and use checkbox 
		//console.log("Cat/Tag: ", q["category"], q["tag"]);
		let cat_cell = $("<td>").addClass("category_cell").append($("<button>").addClass("m-0 p-0 btn btn-link")
			.attr("onclick", "select_category(event)").text(q["category"] || "N/A"));
		row.append(cat_cell);
		let tag_cell = $("<td>");
		if("tag" in q) {
			q["tag"].forEach( function(tag, index) {
				tag_cell.append($("<button>").addClass("m-0 p-0 btn btn-link tag_cell").attr("onclick", "toggle_select_tag(event)").text(tag));
			});
		} else {
			tag_cell.text("-");
		}
		row.append(tag_cell);
		let use_cell = $("<td>").addClass("custom-checkbox").append(
			$("<input type=\"checkbox\" class=\"custom-control\" id=\"use_question_" + q["id"] + "\">")
		);
		row.append(use_cell);
		table_body.append(row);
		// console.log("Constructed row: ", row);
	}
	// after everything had updated; re-typeset MathJax elements 
	MathJax.typeset();
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
		},
		error: function(jqXHR, textStatus, error){
			console.log("Received error", error);
		},
	})
}
