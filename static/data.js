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

function createQuestionnaire(event) {
	// get all the question id available
	var valid_id = [];
//	var table = document.getElementById("question_table");
//	console.log(table.rows);
//	for(let i=1; i<table.rows.length; i++) { // ignore header
//		console.log(table.rows[i].cells[9]);
//		let cb = table.rows[i].cells[9].firstElementChild;
//		if(cb.checked) {
//			valid_id.push(i-1)
//		}
//	}
	var checklist = $("#question_table").find("[id^=use_question_]");
	// find all use_question_ item in the table 
	//console.log(checklist);
	checklist.each(function(index) {
//		console.log($(this)); // dunno why each returned an object though
		if($(this)[0].checked) valid_id.push(index); 
	});
	// TODO put them into the droppable containers.
	// for now just write them into a label
	document.getElementById("questionnaire_items").innerText = "Selectable IDs: " + valid_id.toString();
	// alert("Made list; item is " +  valid_id.toString());
	// create changeable categorizer
	var classifier = $("#barebone_classifier");
	console.log(classifier);
	console.log($("#classifier_wrapper"));
	if(valid_id.length > 0) {
		classifier.empty();
		valid_id.forEach( function(id) {
			$('<label class="border border-primary m-2 p-2" onclick="swapCategory(event)" qidx="' + id + '"> <b>Q' + id + '</b></label>').appendTo(classifier);
		});
		$("#classifier_wrapper").show(); // bootstrap cannot use hide/show apparently
		updateDisposition(event);
	} else {
		$("#classifier_wrapper").hide(); // bootstrap cannot use hide/show apparently
		//classifier.hide();
	}
}

function swapCategory(event) {
	// upon clicking the categorizer, change its fill color with class
//	console.log(event.currentTarget);
	var class_list = event.currentTarget.className.split(/\s+/);
//	console.log(class_list);
	//	TODO swap them iteratively instead of this hardcoding
	if(class_list.includes("border-primary")) {
		$(event.currentTarget).toggleClass("border-primary border-success");
	} else if(class_list.includes("border-success")) {
		$(event.currentTarget).toggleClass("border-success border-danger");
	} else if(class_list.includes("border-danger")) {
		$(event.currentTarget).toggleClass("border-danger border-warning");
	} else if(class_list.includes("border-warning")) {
		$(event.currentTarget).toggleClass("border-warning border-primary");
	} else {
		console.log("Cannot perform swapCategory on ", event.currentTarget);
	}
	updateDisposition(event);
}

function updateDisposition(event) {
	// upon trigger, simply re-calculate category count 
	var cats = [0, 0, 0, 0];
	var questions = $("#barebone_classifier").find("label").each(function(index) {
		let class_list = $(this)[0].className.split(/\s+/);
		if(class_list.includes("border-primary")) {
			cats[0]++;
		} else if(class_list.includes("border-success")) {
			cats[1]++;
		} else if(class_list.includes("border-danger")) {
			cats[2]++;
		} else if(class_list.includes("border-warning")) {
			cats[3]++;
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
		"session_start": Date.parse( $("#start_date_text").val() ), // TODO access the datepicker item instead
		"session_end": Date.parse( $("#end_date_text").val() ), // TODO access the datepicker item instead 
		"show_result": $("#allow_result").is(":checked"),
		"show_score": $("#allow_score").is(":checked"),
	};
	console.log("Chosen setting: ", setting)
	return setting
}

function submitQuestionnaire(event) {
	// check for validity; then submit the data to the server; receiving an entry link
//	var data = [[$("#group_0").val(), []], [$("#group_1").val(), []], 
//		[$("#group_2").val(), []], [$("#group_3").val(), []]];
	var data = [0, 1, 2, 3].map(i => [parseInt($("#group_" + i).val()), parseFloat($("#score_" + i).val()), []]);
	$("#barebone_classifier").find("label").each(function(index) {
		let question_index = parseInt($(this).attr("qidx"));
		console.log($(this), question_index)
		let qcl =  $(this)[0].className.split(/\s+/);
		let question_category = -1;
		if(qcl.includes("border-primary")) {
			question_category = 0;
		} else if(qcl.includes("border-success")) {
			question_category = 1;
		} else if(qcl.includes("border-danger")) {
			question_category = 2;
		} else if(qcl.includes("border-warning")) {
			question_category = 3;
		} else {
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
		var payload = JSON.stringify(data);
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
				// open the view 
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

$(document).ready(function() {
	console.log("Document ready, initializing");
	// bind the grace period checkbox to the input 
	$("#allow_grace").click(function() {
		$("#grace_duration").attr("disabled", $(this).is(":checked"));
	});
	// activate the datetimepicker options
	//$("#start_date_picker").datetimepicker();
	//$("#end_date_picker").datetimepicker();
})
