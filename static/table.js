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

var current_selected_category = null;
var currently_selected_tag = [];
// show the combination of category & tag. Used in a variety of situation 
function show_by_category_and_tag() {
	$("tbody").find("tr").each(function(index) {
		let row_cat = $(this).find(".category_cell").first().text().trim();
		let row_tag = $(this).find(".tag_cell").text();
		// no category selection or category is correct
		let has_category = (current_selected_category === null) || (row_cat === current_selected_category);
		// no tag selection or tag is included in selected
		let has_tag = (currently_selected_tag.length === 0) || currently_selected_tag.some(t => row_tag.includes(t));
		// console.log(row_cat);
		if(has_category && has_tag)
			$(this).show();
		else 
			$(this).hide();
	});
}
// show only a category depending on the clicked button 
function select_category(event) {
	var category = event.currentTarget.innerText;
	if(category === "All") {
		// throw away the filtering
		current_selected_category = null;
		$("#category_dropdown").text("Category");
	} else {
		// filter all fields that does not contain this category 
		current_selected_category = category;
		$("#category_dropdown").text(category);
	}
	show_by_category_and_tag();
	// update the clear filter and show it 
	// $("#filter_category_clear").text(category + "(X)");
	// $("#filter_category_clear").show();
}

// add or remove the tag depending on which one
function toggle_view_tag(event) {
	let tag = $(event.currentTarget.parentNode).find(".form-check-label").text().trim();
	console.log("Clicked on", event, "with tag", tag);
	let checked = $(event.currentTarget).is(":checked");
	if(checked) {
		currently_selected_tag.push(tag);
	} else {
		currently_selected_tag = currently_selected_tag.filter(t => t !== tag);
	}
	show_by_category_and_tag();
}

// remove all tag; used for a whole button box. TODO migrate to a similar checkbox?
function clear_tag(event) {
	// deselect all boxes 
	$("thead").find(".form-check-input").each(function() { $(this).prop("checked", false); } )
	currently_selected_tag = [];
	show_by_category_and_tag();
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

function build_category_cell(cell_text) {
	return $("<button class=\"btn btn-link dropdown-item\" onclick=select_category(event)>" + cell_text + "</button>");
}

function build_tag_cell(tag_text) {
	let tag_overall = $("<div>").addClass("form-check m-1");
	let tag_checkbox = $("<input type=\"checkbox\">").addClass("form-check-input").attr("onclick", "toggle_view_tag(event)");
	let tag_label = $("<label for=\"tag_check_all\"> " + tag_text + " </label>").addClass("form-check-label");
	tag_overall.append(tag_checkbox); tag_overall.append(tag_label);
	return tag_overall;
}

// upon successful update, rebuild the table accordingly
function reupdate_questions(data, clear_table = true) {
	var i = 0;
	if(clear_table) {
		// if clear table, delete everything and re-show 
		$("tbody").empty();
	} else {
		// if not, only update the ones that aren't at the table 
		i = $("tbody").find("tr").length;
	}
	let categories = []; let tags = [];
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
			// console.log(formatted_templates);
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
		let category = q["category"] || "N/A";
		let cat_cell = $("<td>").addClass("category_cell").append($("<button>").addClass("m-0 p-0 btn btn-link").attr("onclick", "select_category(event)").text(category));
		row.append(cat_cell);
		let tag_cell = $("<td>");
		if("tag" in q) {
			q["tag"].forEach( function(tag, index) {
				tag_cell.append($("<button>").addClass("m-0 p-0 btn btn-link tag_cell").attr("onclick", "toggle_select_tag(event)").text(tag));
				if(!tags.includes(tag)) { tags.push(tag); } // add to current tags if not in there
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
		if(!categories.includes(category)) { categories.push(category); } // add to current categories if not in there
	};
	// after the rows updated; reupdate the items in the category/tag dropdown menu 
	let catmenu = $("#category_dropdown_menu");
	catmenu.empty();
	catmenu.append(build_category_cell("All"));
	categories.forEach( function(cat) { catmenu.append(build_category_cell(cat)); });
	let tagmenu = $("#tag_dropdown_menu");
	tagmenu.empty();
	tagmenu.append($("<button>").addClass("btn btn-link").text("Clear").attr("onclick", "clear_tag(event)"));
	tags.forEach( function(tag) { tagmenu.append(build_tag_cell(tag)); });
	
	// after everything had updated; re-typeset MathJax elements 
	MathJax.typeset();
}


