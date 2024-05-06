// drag & drop support; todo make sense later
function allowDrop(event) {
	event.preventDefault();
}

function drag(event) {
	//console.log(event.target);
	event.dataTransfer.setData("qidx", $(event.target).attr("qidx"))
}

function drop(event) {
	event.preventDefault();
	let item_qid = parseInt( event.dataTransfer.getData("qidx") ); 
	let item = $(".question_box").filter(function(index) {
		return parseInt( $(this).attr("qidx") ) == item_qid;
	})[0];
	// console.log(item, item_qid);
	event.target.appendChild(item);
	update_group_count(event);
}

// test function to plug wherever
function test(event) {
	alert("Button working: \"" + event.target.innerText + "\"");
}

// create a new questionnaire with all the selected questions at 1st category
function create_questionnaire_old(event) {
	// get all the question id available
	var valid_id = get_selected_question_ids();
	// TODO put them into the droppable containers.
	// for now just write them into a label
	//document.getElementById("questionnaire_items").innerText = "Selectable IDs: " + valid_id.toString();
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

function create_questionnaire(event, dragdrop_mode=true) {
	// just be add_to_group with extra action 
	add_to_group(event, true, 0);
	$("#data_table").collapse('hide'); $("#result_frame").collapse('hide');
	$("#category_selector").collapse('show'); // automatically hide the table 
	// also enable the category_selector's button from this point onward 
	$("#category_selector_btn").prop('disabled', false);
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

function update_group_count(event, dragdrop_mode=true) {
	// upon trigger, simply re-calculate category count 
	var cats;
	if(dragdrop_mode) {
		cats = [...Array(4).keys()].map( si => $("#classifier_section_" + si.toString()))
			.map( section => section.find(".question_box").length );
	} else {
		cats = [0, 0, 0, 0]
		var questions = $("#barebone_classifier").find("label").each(function(index) {
			let class_list = $(this)[0].className.split(/\s+/);
			let group_index = check_group(class_list);
			if(group_index >= 0) {
				cats[group_index]++;
			} else {
				console.log("Cannot perform find category on ", $(this));
			}
		});
	}
	// log for now 
	console.log(cats);
	for(let i=0;i<4;i++){
		$("#group_count_" + i.toString()).text(cats[i]);
		$("#group_" + i.toString()).prop("disabled", cats[i] == 0);
		$("#score_" + i.toString()).prop("disabled", cats[i] == 0);
//		console.log($("#group_count_" + i.toString()), "->", cats[i])
	}
}

function submit_questionnaire(event) {
	// check for validity; then submit the data to the server; receiving an entry link
//	var data = [[$("#group_0").val(), []], [$("#group_1").val(), []], 
//		[$("#group_2").val(), []], [$("#group_3").val(), []]];
	groups = [0, 1, 2, 3].map(i => []);
	$("#barebone_classifier").find("label").each(function(index) {
		let question_index = parseInt($(this).attr("qidx"));
		// console.log($(this), question_index)
		let qcl =  $(this)[0].className.split(/\s+/);
		let question_category = check_group(qcl);
		if(question_category < 0) {
			console.log("Cannot find category on ", $(this), "index ",  question_index, "will be ignored.");
			return;
		}
		// append the index to the list of choices
		groups[question_category].push(question_index);
	});
	// check and convert the group data to appropriate formats ()
	var data, err_type;
	[data, err_type] = check_group_score(groups);
	if(err_type.every(v => v === null) && err_type.length > 0) {
		// everything is ok, clear and push to an event 
		data = data.filter(v => v[2].length > 0);
		var payload = JSON.stringify({"template": data, "setting": readQuestionnaireSetting(event)});
		console.log("Cleaned result: ", payload);
		var result_panel = $("#result_panel");
		result_panel.hide();
		var category = $("#category_dropdown").text().trim();
		var success_fn = function(data, textStatus, jqXHR){
			console.log("Received: ", data);
			if(data["result"]) {
				// add the link for admin page & test page 
				// TODO add a button to do link copying
				var base = window.location.origin;
				// set the admin and exam link 
				var admin_path = base + "/single_manager" + "?template_key=" + data["session_key"] + "&key=" + data["admin_key"];
				var admin_link = $("#admin_link");
				admin_link.attr("href", admin_path); admin_link.text(admin_path)
				var exam_path = base + "/identify" + "?template_key=" + data["session_key"];
				var exam_link = $("#exam_link");
				exam_link.attr("href", exam_path); exam_link.text(exam_path)
				// enable the good panel; hiding the bad one
				$("#result_good").show(); $("#result_bad").hide()
				// also close down the selector, shouldn't need it now
				$("#category_selector").collapse('hide');
			} else {
				$("#result_bad_error").text(data["error"]);
				$("#result_bad_traceback").text(data["error_traceback"]);
				// enable the bad panel; hiding the good one
				$("#result_good").show(); $("#result_bad").hide()
				// still want the selector
				// $("#category_selector").collapse('hide');
			}
			// also hiding the above panels
			$("#data_table").collapse('hide'); 
			// open the view 
			$("#result_frame").collapse('show');
			result_panel.show();
		}
		perform_post(payload, "build_template?category=" + encodeURIComponent(category), success_fn=success_fn);
	} else {
		// demand fixes with an alert
		console.log(err_type);
		alert("Error:\n" + err_type.filter(v => v !== null).join("\n"))
		return
	}
	// Alert to screen for now 
	// alert("Selection created:" + data.toString() )
}

// add the selected to corresponding category; any current values is overriden
GROUP_CLASS_NAME = ["border-primary", "border-success", "border-danger", "border-warning"]
function add_to_group(event, dragdrop_mode=true, group_index=-1) {
	// get the checked
	var checked_ids = get_selected_question_ids();
	// get group; convert to qidx attributes
	if(group_index < 0) {
		group_index = parseInt($("#add_to_group_btn").html().slice(-1)[0]) - 1; // take last and convert to int; then minus 1 to move [1, 4] to [0, 4)
	}
	let add_field = GROUP_CLASS_NAME[group_index];
	let remove_field = GROUP_CLASS_NAME.slice(0, group_index).join(" ") + " " + GROUP_CLASS_NAME.slice(group_index+1).join(" ");
	var q_indices = $.map(checked_ids, i => i.toString());
	if(dragdrop_mode) {
		// var sections = [...Array(10).keys()].map(i => $("#classifier_section_" + i.toString()));
		var current_section_ids, section;
		for(let si=0;si<4;si++){
			section = $("#classifier_section_" + si.toString());
			if(si == group_index) {
				current_section_ids = [...checked_ids];
				section.find("label").each(function (index) {
					let i = checked_ids.indexOf( parseInt($(this).attr("qidx")) )
					if(i >= 0) {
						current_section_ids.splice(i, 1); // item is already here; just ignore.
					}
				});
				for(qidx in current_section_ids) {
					// item here means it's not in existence yet; add new object in.
					$('<label>').attr("class", "border m-2 p-2 question_box").attr("qidx", qidx.toString())
						.attr("draggable", true).attr("ondragstart", "drag(event)")
						.text("Q" + qidx.toString()).appendTo(section);
				}
			} else {
				section.find("label").each(function (index) {
					let i = checked_ids.indexOf( parseInt($(this).attr("qidx")) )
					if(i >= 0) {
						// label should be removed from this section itself.
						$(this).remove();
					}
				});
			}
		}
	} else {
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
	}
	// recheck the group availability
	update_group_count(classifier, dragdrop_mode);
}

function switch_add_group(group_index) {
	// modify the button to this group index 
	$("#add_to_group_btn").html("Add to Group " + group_index);
}

var number_regex = /^\+?\d+$/
function update_student_list(event) {
	// upon selected file; attempt to parse and load the student list.
	var target_file = event.currentTarget.files[0];
	var reader = new FileReader();
	reader.onload = function(e) {
		var data = reader.result;
		const workbook = XLSX.read(data, {type: "binary"});
		const first_sheet = workbook.Sheets[workbook.SheetNames[0]];
		// expecting data at column 2-3 (ID and name) and from row 3. Maybe allow customizing?
		data = XLSX.utils.sheet_to_json(first_sheet, {range: "B3:C103", header:1});
		// filter out fields that are incomplete or wrong
		data = data.filter(r => r.length == 2).filter(r => !r.includes(undefined));
		//		console.log(data);
		data = data.filter(r => typeof(r[0]) == "number" || number_regex.test(r[0].trim()));
		console.log("Parsed data: ", data)
		if(data.length == 0) {
			alert("Invalid supplied data: excel must have ID+Name range B3:C-, and ID must be numerical")
		} else {
			// populate the dropdown with the supplied units
			var student_list = $("#student_list");
			for(r of data) {
				//console.log(r);
				// add checkboxes, each has corresponding id and value
				student_list.append($("<input class=\"m-1\" type=\"checkbox\" id=\"" + r[0] + "\" st_name=\"" + r[1]
					+ "\">(" + r[0] + ") " + r[1] + "</input>").prop("checked", true));
				student_list.append($("<br />"));
			}
			// enable button to dropdown
			$("#toggle_student_list").prop("disabled", false);
			// TODO put this data into template making
			$("#load_student_list_result").text("Student List loaded");
		}
	};
	reader.onerror = function(e) {
		console.log("Encounter read error: ", e);
	};
	reader.readAsBinaryString(target_file);
}

