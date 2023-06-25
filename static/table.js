function get_selected_question_ids() {
	var valid_id = [];
	var checklist = $("#question_table").find("[id^=use_question_]");
	// find all use_question_ item in the table 
	//console.log(checklist);
	checklist.each(function(index) {
//		console.log($(this)); // dunno why each returned an object though
		if($(this)[0].checked) valid_id.push(index); 
	});
	return valid_id;
}

function select_category(event) {
	// select a category depending on the clicked button 
	var category = event.currentTarget.innerText;
	// filter all fields that does not contain this category 
	$("tbody").find("tr").each(function(index) {
		let row_cat = $(this).find(".category_cell").first().text().trim();
		console.log(row_cat);
		if(row_cat !== category) 
			$(this).hide();
		else 
			$(this).show();
	});
	// update the clear filter and show it 
	$("#filter_category_clear").text(category + "(X)");
	$("#filter_category_clear").show();
}

// clear out the selected category 
function clear_category(event) {
	$("tbody").find("tr").each(function(index) { $(this).show(); });
	// hide the clear filter 
	$("#filter_category_clear").hide();
}

function toggle_select_tag(event) {
	// select/deselect all items by a chosen tag. if not all items selected, use select mode
	var target_tag = event.currentTarget.innerText;
	// get all same-tag row; extract the checkboxes
	var boxes = $("tbody").find("tr").filter(function(index) {
		return $(this).find(".tag_cell:contains('" + target_tag + "')").length > 0;
	}).find("[id^=use_question_]");
	console.log(boxes);
	if(boxes.filter(":checked").length == boxes.length) {
		// all box checked; deselect 
		boxes.each(function() { $(this).prop("checked", false); })
	} else {
		// zero/some box checked; select
		boxes.each(function() { $(this).prop("checked", true); })
	}
}

function toggle_all_tag(event) {
	// select/deselect the visible items.
	var boxes = $("tbody").find("tr").filter(function(index) {
		return $(this).is(":visible"); // get only the visible boxes
	}).find("[id^=use_question_]");
	if(boxes.filter(":checked").length == boxes.length) {
		// all box checked; deselect 
		boxes.each(function() { $(this).prop("checked", false); })
	} else {
		// zero/some box checked; select
		boxes.each(function() { $(this).prop("checked", true); })
	}
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
		} else if(data[i]["is_single_option"]) {
			let formatted_templates = q["variable_limitation"].trim().replaceAll("|||", "\t=>\t");
			console.log(formatted_templates);
			row.append($("<td>").text(q["answer1"]));
			row.append($("<td colspan='4' style='white-space: pre-wrap'>").text(formatted_templates));
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


