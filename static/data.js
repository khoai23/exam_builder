// drag & drop support; todo make sense later
function allowDrop(event) {
	event.preventDefault();
}

function drag(event) {
	event.dataTransfer.setData("text", ev.target.id)
}

function drop(event) {
	event.preventDefault();
	var item_id = ev.dataTransfer.getData("text")
	event.target.appendChild(document.getElementById(item_id))
}

// test function to plug wherever
function test(event) {
	alert("Button working: \"" + event.target.innerText + "\"");
}

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

// create a new questionnaire with all the selected questions at 1st category
function create_questionnaire(event) {
	// get all the question id available
	var valid_id = get_selected_question_ids();
	// TODO put them into the droppable containers.
	// for now just write them into a label
	document.getElementById("questionnaire_items").innerText = "Selectable IDs: " + valid_id.toString();
	// alert("Made list; item is " +  valid_id.toString());
	// create changeable categorizer
	var classifier = $("#barebone_classifier");
//	console.log(classifier);
//	console.log($("#classifier_wrapper"));
	// void the current questionnaire ids
	if(valid_id.length > 0) {
		classifier.empty();
		valid_id.forEach( function(id) {
			$('<label class="border border-primary m-2 p-2" onclick="swap_group(event)" qidx="' + id + '"> <b>Q' + id + '</b></label>').appendTo(classifier);
		});
		$("#classifier_wrapper").show();
		update_group_count(event);
		$("#data_table").collapse('hide'); $("#result_frame").collapse('hide');
		$("#category_selector").collapse('show'); // automatically hide the table 
		// also enable the category_selector's button from this point onward 
		$("#category_selector_btn").prop('disabled', false);
	} else {
		$("#classifier_wrapper").hide(); // bootstrap cannot use hide/show apparently
	}
}

// return id of each group (0-4 for primary-success-danger-warning)
function check_group(class_list) {
	if(class_list.includes("border-primary")) {
		return 0;
	} else if(class_list.includes("border-success")) {
		return 1;
	} else if(class_list.includes("border-danger")) {
		return 2;
	} else if(class_list.includes("border-warning")) {
		return 3;
	} else {
		return -1;
	}
}

SWAP_CLASS_NAME = ["border-primary border-success", "border-success border-danger", "border-danger border-warning", "border-warning border-primary"]
function swap_group(event) {
	// upon clicking the categorizer, change its fill color with group's class
//	console.log(event.currentTarget);
	var class_list = event.currentTarget.className.split(/\s+/);
//	console.log(class_list);
	let group_index = check_group(class_list);
	if(group_index >= 0) {
		$(event.currentTarget).toggleClass(SWAP_CLASS_NAME[group_index]);
	} else {
		console.log("Cannot perform swapCategory on ", event.currentTarget);
	}
	update_group_count(event);
}

function update_group_count(event) {
	// upon trigger, simply re-calculate category count 
	var cats = [0, 0, 0, 0];
	var questions = $("#barebone_classifier").find("label").each(function(index) {
		let class_list = $(this)[0].className.split(/\s+/);
		let group_index = check_group(class_list);
		if(group_index >= 0) {
			cats[group_index]++;
		} else {
			console.log("Cannot perform find category on ", $(this));
		}
	});
	// log for now 
//	console.log(cats);
	for(let i=0;i<4;i++){
		$("#group_count_" + i.toString()).text(cats[i]);
		$("#group_" + i.toString()).prop("disabled", cats[i] == 0);
		$("#score_" + i.toString()).prop("disabled", cats[i] == 0);
//		console.log($("#group_count_" + i.toString()), "->", cats[i])
	}
}

function readQuestionnaireSetting(event) {
	// read non-critical setting associated with the questionnaire 
	var setting = {
		"session_name": $("#session_name").val(),
		"student_identifier_name": $("#id_name").val(),
		"exam_duration": parseInt($("#session_duration").val()),
		"grace_duration": parseInt($("#grace_duration").val()),
		"session_start":$("#start_exam_time").val() + " " + $("#start_exam_date").val(), // leave parsing to server
		"session_end": $("#end_exam_time").val() + " " + $("#end_exam_date").val(), 
		"show_result": $("#allow_result").is(":checked"),
		"show_score": $("#allow_score").is(":checked"),
	};
	console.log("Chosen setting: ", setting)
	return setting
}


function submit_questionnaire(event) {
	// check for validity; then submit the data to the server; receiving an entry link
//	var data = [[$("#group_0").val(), []], [$("#group_1").val(), []], 
//		[$("#group_2").val(), []], [$("#group_3").val(), []]];
	var data = [0, 1, 2, 3].map(i => [parseInt($("#group_" + i).val()), parseFloat($("#score_" + i).val()), []]);
	$("#barebone_classifier").find("label").each(function(index) {
		let question_index = parseInt($(this).attr("qidx"));
		console.log($(this), question_index)
		let qcl =  $(this)[0].className.split(/\s+/);
		let question_category = check_group(qcl);
		if(question_category < 0) {
			console.log("Cannot find category on ", $(this), "index ",  question_index, "will be ignored.");
			return;
		}
		// append the index to the list of choices
		data[question_category][2].push(question_index);
	});
	console.log("Raw result", data);
	// Check phase.
	var err_type = data.map(function(item, index) {
		console.log(item[2]);
		if(item[2].length > 0) {
			if(isNaN(item[0]) || item[0] == 0)
				return "Category " + index + " is valid but want zero question.";
			else if(item[0] > item[2].length)
				return "Category " + index + " has insufficient base.";
			else if(isNaN(item[1]) || item[1] <=0)
				return "Score of " + index + " is NaN/non-positive";
		} else if(item[2].length == 0) {
			// should be disabled and value irrelevant
			return null;
		}
		return null;
	});
	if(err_type.every(v => v === null) && err_type.length > 0) {
		// everything is ok, clear and push to an event 
		data = data.filter(v => v[2].length > 0);
		var payload = JSON.stringify({"template": data, "setting": readQuestionnaireSetting(event)});
		console.log("Cleaned result: ", payload);
		var result_panel = $("#result_panel");
		result_panel.hide();
		$.ajax({
			url: "build_template", 
			type: "POST",
			data: payload, 
			contentType: "application/json",
			dataType: "json",
			success: function(data, textStatus, jqXHR){
				console.log("Received: ", data);
				// add the link for admin page & test page 
				// TODO add a button to do link copying
				var base = window.location.origin;
				// set the admin and exam link 
				var admin_path = base + "/manage" + "?template_key=" + data["session_key"] + "&key=" + data["admin_key"];
				var admin_link = $("#admin_link");
				admin_link.attr("href", admin_path); admin_link.text(admin_path)
				var exam_path = base + "/identify" + "?template_key=" + data["session_key"];
				var exam_link = $("#exam_link");
				exam_link.attr("href", exam_path); exam_link.text(exam_path)
				// also hiding the above panels
				$("#data_table").collapse('hide'); 
				$("#category_selector").collapse('hide');
				// open the view 
				$("#result_frame").collapse('show');
				result_panel.show();
			},
			error: function(jqXHR, textStatus, error){
				// TODO check failure here
				console.log("Failure with error: " + error);
			}
		});
	} else {
		// demand fixes with an alert
		console.log(err_type);
		alert("Error:\n" + err_type.filter(v => v !== null).join("\n"))
		return
	}
	// Alert to screen for now 
	// alert("Selection created:" + data.toString() )
}

function choose_file(event) {
	$("#import_file").click();
}

function submit_file(event) {
// $(document).on("ready", function() {
//	console.log("Attempt override submit.")
	var form = $("#import_form");
	var actionUrl = form.attr('action');
	var data = new FormData(form[0])
	console.log(data);
	$.ajax({
		type: "POST",
		url: actionUrl,
		data: data,
		processData: false,
		contentType: false,
		success: function(data, textStatus, jqXHR) {
			console.log("Form submitted: ", data);
			$("#io_result").removeClass("text-danger").addClass("text-success").text("Import done, data reloaded.");
		},
		error: function(jqXHR, textStatus, error){
			console.log(error);
			$("#io_result").removeClass("text-success").addClass("text-danger").text("Import failed.")
		}
	});
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

// add the selected to corresponding category; any current values is overriden
GROUP_CLASS_NAME = ["border-primary", "border-success", "border-danger", "border-warning"]
function add_to_group(event) {
	// get the checked
	var checked_ids = get_selected_question_ids();
	// get group; convert to qidx attributes
	var group_index = parseInt($("#add_to_group_btn").html().slice(-1)[0]) - 1; // take last and convert to int; then minus 1 to move [1, 5) to [0, 4)
	let add_field = GROUP_CLASS_NAME[group_index];
	let remove_field = GROUP_CLASS_NAME.slice(0, group_index).join(" ") + " " + GROUP_CLASS_NAME.slice(group_index+1).join(" ");
	var q_indices = $.map(checked_ids, i => i.toString());
	// go through the item in the classifier; 
	// if id already exist, swap it with new class; if it not, add it
	var classifier = $("#barebone_classifier");
//	console.log(checked_ids, group_index);
	classifier.find("label").each(function (index) {
		let i = checked_ids.indexOf( parseInt($(this).attr("qidx")) )
//		console.log($(this).attr("qidx"), i);
		if(i >= 0) {
			// is already in the classifier, switch the class over 
			$(this).removeClass(remove_field).addClass(add_field);
			// also deduce from checked_ids
			checked_ids.splice(i, 1);
		}
	});
//	console.log(checked_ids)
	// for each item remaining in the checked_ids; add them new into the classifiers
	checked_ids.forEach( function(id) {
		$('<label class="border ' + add_field + ' m-2 p-2" onclick="swap_group(event)" qidx="' + id + '"> <b>Q' + id + '</b></label>').appendTo(classifier);
	});
	// recheck the group availability
	update_group_count(classifier);
}

function switch_add_group(group_index) {
	// modify the button to this group index 
	$("#add_to_group_btn").html("Add to Group " + group_index);
}

function toggle_select_tag(event) {
	// select/deselect all items by a chosen tag. if not all items selected, use select mode
	var target_tag = event.currentTarget.innerText;
	// get all same-tag row; extract the checkboxes
	var boxes = $("tbody").find("tr").filter(function(index) {
		return $(this).find(".tag_cell:contains('" + target_tag + "')").length > 0;
	}).find("[id^=use_question_]");
	//console.log(boxes);
	if(boxes.filter(":checked").length == boxes.length) {
		// all box checked; deselect 
		boxes.each(function() { $(this).prop("checked", false); })
	} else {
		// zero/some box checked; select
		boxes.each(function() { $(this).prop("checked", true); })
	}
}

$(document).ready(function() {
	console.log("Document ready, initializing");
	// bind the grace period checkbox to the input 
	$("#allow_grace").click(function() {
		$("#grace_duration").attr("disabled", $(this).is(":checked"));
	});
	// activate the datetimepicker options
	//$("#start_date_picker").datetimepicker();
	$(".datepicker").datepicker({
		format: "dd-mm-yyyy",
		todayHighlight: true,
	});
	// clicking the show of Data Table card will collapse the Category Selector & Result
	$("#data_table").on("show.bs.collapse", function() { 
		$("#category_selector").collapse('hide'); 
		$("#result_frame").collapse('hide');
	});
})
