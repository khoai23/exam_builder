var use_local_data = false;
var edit_by_modal = true;

function get_selected_question_ids(in_index0 = true) {
	var valid_id = [];
	var checklist = $("#question_table").find("[id^=use_question_]");
	var offset = in_index0 ? 0 : 1;
	// find all use_question_ item in the table 
	//console.log(checklist);
	checklist.each(function(index) {
//		console.log($(this)); // dunno why each returned an object though
		if($(this)[0].checked) valid_id.push( parseInt($(this).attr("qid")) - offset ); 
	});
	return valid_id;
}

var category_update_function = null; // this value is to be called upon a category change
var selector_update_function = null; // this value is to be updated upon a selector load (checkbox)
var all_categories = null;
var current_selected_category = localStorage.getItem("8thcircle_category");
var current_selected_hardness = localStorage.getItem("8thcircle_hardness") || 0; 
var all_tags = null;
var currently_selected_tag = []; 
var editable = false;

var current_data = null;
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
	if(!bounded_edit) {
		console.log("1st edit modal triggered; binding function.");
		$("#edit_true_text").on("change input", _render_edit);
		bounded_edit = true;
	}
	// console.log("True content: ", q[key]);
	$("#edit_true_text").val(q[key]);
	_render_edit();
	$("editModalTitle").text("Editing question " + currently_edited_cell_id.toString());
	$("#editModal").modal("show");
}

function _submit_edit_modal() {
	// when submitting; send the necessary data in #edit_true_text away 
	let content = $("#edit_true_text").val();
	console.log("Sending: ", currently_edited_cell_id, currently_edited_key, content);
	// alert("Check log for data supposed to be push");
	edit_question(currently_edited_cell_id, currently_edited_key, content); // using index0 for this.
	current_edit_item.text(content);
	// voiding the rest & hide
	currently_edited_cell_id = null;
	currently_edited_key = null;
	current_edit_item = null;
	$("#editModal").modal("hide");
}

function setup_editable(cell, qid, key, index0) {
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

// used when use_local_data is false; data is reloaded on the long web instead 
function load_data_into_table(start, end, request_tags=false, hardness=undefined, url="filtered_questions") {
	let catstr = "category=" + encodeURI(current_selected_category);
	let tagstr = currently_selected_tag.length === 0 ? "" : "tag=" + encodeURI(currently_selected_tag.join(","));
	if(tagstr == "") {
		url = url + "?" + catstr;
	} else {
		url = url + "?" + catstr + "&" + tagstr;
	}
	if(start !== undefined) {
		url = url + "&start=" + start.toString();
		start = Math.floor(start / length_per_view);
	} else {
		start = 0;
	}
	if(end !== undefined) {
		url = url + "&end=" + end.toString();
	}
	if(hardness === undefined) {
		hardness = current_selected_hardness;
	}
	url = url + "&hardness=" + hardness.toString();

	if(request_tags) {
		if(currently_selected_tag.length > 0) {
			console.log("Trying to request tags with already selected tag; this will still work, but will returning same value as selected");
			// TODO disable this?
		}
		url = url + "&request_tags=true"
	}
	// console.log("Querying url, ", url, catstr, tagstr);
	$.ajax({
		type: "GET",
		url: url,
		success: function(data, textStatus, jqXHR) {
			current_data = data["questions"];
			// update the questions 
			reupdate_questions(data["questions"]);
			// show all necessary tags if specifically requested
			if(request_tags) {
				internal_update_filter(data["tags"]);
			}
			update_view_index(start, Math.floor(data["all_length"] / length_per_view));
		},
		error: function(jqXHR, textStatus, error){
			console.log("Received error", error);
		},
	});
}
	
// show the combination of category & tag. Used in a variety of situation 
function show_by_category_and_tag(request_tags=false) {
	if(use_local_data) {
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
	} else {
		load_data_into_table(undefined, undefined, request_tags=request_tags)
	}
}

// show only a category depending on the clicked button 
function select_category(event) {
	var category = event.currentTarget.innerText;
	if(false && category === "All") {
		// throw away the filtering
		current_selected_category = null;
		$("#category_dropdown").text("Category");
	} else {
		// save to local storage 
		localStorage.setItem("8thcircle_category", category);
		// filter all fields that does not contain this category 
		current_selected_category = category;
		$("#category_dropdown").text(category);
		if(category_update_function !== null){
			category_update_function(all_categories, category);
		}
		// also disable all tags and try again
		currently_selected_tag = [];
	}
	show_by_category_and_tag(request_tags=true);
	// update the clear filter and show it 
	// $("#filter_category_clear").text(category + "(X)");
	// $("#filter_category_clear").show();
}

function select_hardness(hardness_value) {
	console.log("Switching to hardness value", hardness_value);
	current_selected_hardness = hardness_value;
	localStorage.setItem("8thcircle_hardness", current_selected_hardness);
	// TODO make this less annoying
	$("#hardness_dropdown").text(current_selected_hardness == 0 ? "All" : current_selected_hardness == -1 ? "Unrated" : current_selected_hardness == -2 ? "Rated" : current_selected_hardness.toString());
	show_by_category_and_tag(request_tags=true)
}

function selector_update(event) {
	// function on checkbox click and/or tag click; should not do anything by default 
	if(selector_update_function !== null) {
		selector_update_function(event);
	}
}

// add or remove the tag depending on which one
function toggle_view_tag(event) {
	let tag = $(event.currentTarget.parentNode).find(".form-check-label").text().trim();
	//console.log("Clicked on", event, "with tag", tag);
	let checked = $(event.currentTarget).is(":checked");
	if(checked) {
		currently_selected_tag.push(tag);
	} else {
		currently_selected_tag = currently_selected_tag.filter(t => t !== tag);
	}
	show_by_category_and_tag(request_tags=false);
}

// remove all tag; used for a whole button box. TODO migrate to a similar checkbox?
function clear_tag(event) {
	// deselect all boxes 
	$("thead").find(".form-check-input").each(function() { $(this).prop("checked", false); } )
	currently_selected_tag = [];
	show_by_category_and_tag();
	selector_update(event);
}

function toggle_select_tag(event) {
	// select/deselect all items by a chosen tag. if not all items selected, use select mode
	var target_tag = event.currentTarget.innerText;
	// get all same-tag row; extract the checkboxes
	var boxes = $("tbody").find("tr").filter(function(index) {
		return $(this).find(".tag_cell:contains('" + target_tag + "')").length > 0;
	}).find("[id^=use_question_]");
	// console.log(boxes);
	if(boxes.filter(":checked").length == boxes.length) {
		// all box checked; deselect 
		boxes.each(function() { $(this).prop("checked", false); })
	} else {
		// zero/some box checked; select
		boxes.each(function() { $(this).prop("checked", true); })
	}
	selector_update(event);
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
	selector_update(event);
}

const length_per_view = 1000;
const button_list = ["table_button_first", "table_button_previous", "table_button_current", "table_button_next", "table_button_last"];
var max_question_index = 0;

function update_view_index(current_index, max_index) {
	// if max_index, reupdate the bar depending on value
	console.log("Updating index", current_index, "of", max_index);
	if(max_index !== undefined) {
		max_question_index = max_index;
		if(max_index == 0) {
			// sub-1 (index 0), showing no bar
			$("#table_button_bar").hide();
		} else {
			$("#table_button_bar").show();
			if(max_index < 5) {
				// between 2-5(index 1-4), repurpose the buttons in direct format 
				for(let i=0; i<5; i++) {
					let btn = $("#" + button_list[i]);
					if(i <= max_index) {
						// changing text as needed; and show it
						btn.text((i+1).toString()).attr("onclick", "load_data_into_table(" + (i*length_per_view).toString() + "," + ((i+1)*length_per_view).toString() + ")");
						btn.show();
					} else { // not needed, hide it
						btn.hide();
					}
				}
				$("#elipse_start").hide();
				$("#elipse_end").hide();
			} else {
				// 5+, set button in default format with correct end index
				$("#table_button_first").text("1").attr("onclick", "load_data_into_table(0," + length_per_view.toString() + ")");
				$("#table_button_previous").text("<");
				//$("#table_button_next").text(">");
				$("#table_button_last").text((max_index+1).toString()).attr("onclick", "load_data_into_table(" + (max_question_index*length_per_view).toString() + ")");
			}
		}
	}
	// update the values depending on the current_index & max_question_index
	if(max_question_index < 5) {
		// direct format 
		button_list.forEach(function(name, index){
			if(index == current_index) {
				$("#" + name).addClass("btn-primary").removeClass("btn-outline-primary");
			} else {
				$("#" + name).removeClass("btn-primary").addClass("btn-outline-primary");
			}
		})
	} else {
		// default format, showing items depending on immediate distance between current toward first & last 
		$("#table_button_current").text((current_index+1).toString());
		// front section
		$("#table_button_previous").attr("onclick", "load_data_into_table(" + ((current_index-1)*length_per_view).toString() + "," + (current_index*length_per_view).toString() + ")")
		if(current_index == 0) { // first; hide all
			$("#table_button_first").hide();
			$("#elipse_start").hide();
			$("#table_button_previous").hide();
		} else if(current_index == 1) { // second, hide the spanning & previous
			$("#table_button_first").show();
			$("#elipse_start").hide();
			$("#table_button_previous").hide();
		} else if(current_index == 2) { // third, hide the spanning & repurpose the previous 
			$("#table_button_first").show();
			$("#elipse_start").hide();
			$("#table_button_previous").text(current_index.toString()).show();
		} else { // >3, show the elipses
			$("#table_button_first").show();
			$("#elipse_start").show();
			$("#table_button_previous").text("<").show();
		}
		// back section
		$("#table_button_next").attr("onclick", "load_data_into_table(" + ((current_index+1)*length_per_view).toString() + "," + ((current_index+2)*length_per_view).toString() + ")")
		if(current_index == max_question_index) { // last; hide all
			$("#table_button_last").hide();
			$("#elipse_end").hide();
			$("#table_button_next").hide();
		} else if(current_index == max_question_index-1) { // second, hide the spanning & previous
			$("#table_button_last").show();
			$("#elipse_end").hide();
			$("#table_button_next").hide();
		} else if(current_index == max_question_index-2) { // third, hide the spanning & repurpose the previous 
			$("#table_button_last").show();
			$("#elipse_end").hide();
			$("#table_button_next").text((current_index+2).toString()).show();
		} else { // <-3, show the elipses
			$("#table_button_last").show();
			$("#elipse_end").show();
			$("#table_button_next").text(">").show();
		}
	}
}

function get_and_reupdate_question(event, with_duplicate=true) {
	// first load into the table; 
	load_data_into_table(undefined, undefined, request_tags=true);
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

function external_update_filter(chain_to_reupdate_question=false) {
	// update the category; if specific flag is enabled, also auto-select the first category and load accordingly
	$.ajax({
		type: "GET",
		url: "all_filter",
		success: function(data, textStatus, jqXHR) {
			//console.log(data)
			console.log("Loaded category:", data["categories"]);
			let catmenu = $("#category_dropdown_menu");
			catmenu.empty();
			// catmenu.append(build_category_cell("All"));
			data["categories"].sort(); // ensure consistent ordering
			all_categories = data["categories"];
			all_categories.forEach( function(cat) { catmenu.append(build_category_cell(cat)); });
			if(chain_to_reupdate_question) {
				if(!all_categories.includes(current_selected_category)) {
					current_selected_category = all_categories[0]; // selected first category 
					console.log("Did not found current category; setting to default (1st, ", current_selected_category, ")");
				}
				$("#category_dropdown").text(current_selected_category); // also change the display to the appropriate version
				// hardness value is always correct per session.
				$("#hardness_dropdown").text(current_selected_hardness == 0 ? "All" : current_selected_hardness == -1 ? "Unrated" : current_selected_hardness == -2 ? "Rated" : current_selected_hardness.toString());
				if(category_update_function !== null) {
					category_update_function(all_categories, current_selected_category)
				}
				load_data_into_table(undefined, undefined, request_tags=true)
			}
		},
		error: function(jqXHR, textStatus, error){
			console.log("Received error", error);
		},
	})
}

function internal_update_filter(tags) {
	let tagmenu = $("#tag_dropdown_menu");
	tagmenu.empty();
	tagmenu.append($("<button>").addClass("btn btn-link").text("Clear").attr("onclick", "clear_tag(event)"));
	tags.forEach( function(tag) { tagmenu.append(build_tag_cell(tag)); });
}

// upon successful update, rebuild the table accordingly
function reupdate_questions(data, clear_table = true) {
	var i = 0;
	if(clear_table) {
		// if clear table, delete everything and re-show 
		$("tbody").empty();
	} else {
		// if not, only update the ones that aren't at the table 
		// Never open this again; what if I want append mode?
		i = $("tbody").find("tr").length;
	}
	let categories = []; let tags = [];
	if(editable && edit_by_modal) {
		// if edit by modal; requires the data to be kept 
		current_data = data;
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
		let hardness_cell = $("<td>").text(q["hardness"] || "?");
		if(q["hardness"]) {
			hardness_cell = hardness_cell.attr("class", "hardness_" + q["hardness"].toString());
		} else {
			hardness_cell = hardness_cell.attr("class", "hardness_undefined");
		}
		let question_cell = $("<td colspan='2'>").attr("display", "white-space: pre-wrap");
		if(q["question"].includes("|||")) { // image-included; attempt to 
			const pieces = q["question"].split("|||");
			pieces.forEach(function (p) {
				p = p.trim();
				if(p) {
					if(p.startsWith("http")){ // hack to detect image
						question_cell.append($("<img class=\"img-thumbnail\" style=\"max-width: 300px;\">").attr("src", p));
					} else { // TODO re-add the splitted value if exist (e.g is_single_equation)
						question_cell.append($("<span>").text(p));
					}
				}
			});
		} else {
			question_cell.text(q["question"]); // plaintext, just
		}
		// additionally; if editable value is active; allow editing & binding
		if(editable) {
			hardness_cell = setup_editable(hardness_cell, q["id"], "hardness", i);
			question_cell = setup_editable(question_cell, q["id"], "question", i);
		}
		let row = $("<tr>").append([id_cell, hardness_cell, question_cell]);
		if(data[i]["is_single_equation"]) {
			let formatted_templates = q["variable_limitation"].trim().replaceAll("|||", "\t=>\t");
			let answer_cell = $("<td colspan='3' style='white-space: pre-wrap'>").attr("class", "d-none d-lg-table-cell d-xl-table-cell").text(q["answer1"]);
			let template_cell = $("<td colspan='2' style='white-space: pre-wrap'>").attr("class", "d-none d-lg-table-cell d-xl-table-cell").text(formatted_templates);
			if(editable) {
				answer_cell = setup_editable(answer_cell, q["id"], "answer1", i);
				template_cell = setup_editable(template_cell, q["id"], "variable_limitation", i);
			}
			row.append([answer_cell, template_cell]);
		} else if(data[i]["is_single_option"]) {
			let formatted_templates = q["variable_limitation"].trim().replaceAll("|||", "\t=>\t");
			// console.log(formatted_templates);
			let answer_cell = $("<td colspan='2'>").attr("class", "d-none d-lg-table-cell d-xl-table-cell").text(q["answer1"]);
			let template_cell = $("<td colspan='3' style='white-space: pre-wrap'>").attr("class", "d-none d-lg-table-cell d-xl-table-cell").text(formatted_templates);
			if(editable) {
				answer_cell = setup_editable(answer_cell, q["id"], "answer1", i);
				template_cell = setup_editable(template_cell, q["id"], "variable_limitation", i);
			}
			row.append([answer_cell, template_cell]);
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
				let key = "answer" + j.toString();
				let answer = q[key];
				if(answer === undefined) {
					console.error("Question", q, "missing answer of index", j);
					answers.push($("<td>").attr("class", "d-none d-lg-table-cell d-xl-table-cell").addClass("bg-danger"));
				} else if(answer.includes("|||")) {
					// is image variant; put into img tag and put inside
					answer = answer.replaceAll("|||", "");
					answers.push($("<td>").attr("class", "d-none d-lg-table-cell d-xl-table-cell").append(
						$("<img class=\"img-thumbnail\" style=\"max-width: 300px;\">").attr("src", answer)
					));
				} else {
					// is text variant, push in directly
					answers.push($("<td>").attr("class", "d-none d-lg-table-cell d-xl-table-cell").text(answer));
				}
				if(correct_ids.includes(j)) {
					answers[answers.length-1].addClass(is_multiple_choice ? "table-info" : "table-success");
				}
				if(editable) {
					answers[answers.length-1] = setup_editable(answers[answers.length-1], q["id"], key, i);
				}
			}
			// append everything 
			row.append(answers);
			// correct question will be added in similar format to python tuple (wrapped in bracket, separated by comma)
			if(is_multiple_choice){
				row.append($("<td>").attr("class", "d-none d-lg-table-cell d-xl-table-cell").text("(" + correct_ids.join(",") + ")"));
			} else {
				row.append($("<td>").attr("class", "d-none d-lg-table-cell d-xl-table-cell").text(correct_ids[0]));
			}
		}
		// category, tag, and use checkbox 
		//console.log("Cat/Tag: ", q["category"], q["tag"]);
		let category = q["category"] || "N/A";
		if(use_local_data) {
			let cat_cell = $("<td>").addClass("category_cell").append($("<button>").addClass("m-0 p-0 btn btn-link").attr("onclick", "select_category(event)").text(category));
			row.append(cat_cell);
		}
		let tag_cell = $("<td>");
		if("tag" in q) {
			q["tag"].forEach( function(tag, index) {
				if(index > 0) { tag_cell.append($("<br>")) }
				tag_cell.append($("<button>").addClass("m-0 p-0 btn btn-link tag_cell").attr("onclick", "toggle_select_tag(event)").text(tag));
				if(!tags.includes(tag)) { tags.push(tag); } // add to current tags if not in there
			});
		} else {
			tag_cell.text("-");
		}
		row.append(tag_cell);
		let use_cell = $("<td>").addClass("custom-checkbox").append(
			$("<input type=\"checkbox\" id=\"use_question_" + q["id"] + "\">").addClass("custom-control").attr("onclick", "selector_update(event)").attr("qid", q["id"])
		);
		row.append(use_cell);
		table_body.append(row);
		// console.log("Constructed row: ", row);
		if(!categories.includes(category)) { categories.push(category); } // add to current categories if not in there
	};
	if(use_local_data) {
		// in local data, after the rows updated; reupdate the items in the category/tag dropdown menu 
		let catmenu = $("#category_dropdown_menu");
		catmenu.empty();
		catmenu.append(build_category_cell("All"));
		categories.forEach( function(cat) { catmenu.append(build_category_cell(cat)); });
		let tagmenu = $("#tag_dropdown_menu");
		tagmenu.empty();
		tagmenu.append($("<button>").addClass("btn btn-link").text("Clear").attr("onclick", "clear_tag(event)"));
		tags.forEach( function(tag) { tagmenu.append(build_tag_cell(tag)); });
	} else {
		// in remote data; catmenu and tagmenu is persistent
	}
	
	// after everything had updated; re-typeset MathJax elements 
	MathJax.typeset();
}

if(!use_local_data) {
	// add extra update to load all categories/tags in
	$(document).ready(external_update_filter);
}
