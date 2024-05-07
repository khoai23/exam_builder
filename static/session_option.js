// interaction with session_option.tpl

function readQuestionnaireSetting(event) {
	// read non-critical setting associated with the questionnaire 
	var checked_student_list = $("#student_list").find("input").filter((index, node) => $(node).is(":checked"));
	// double bracket to prevent auto-flattening. Javascript.
	var valid_student_arr = checked_student_list.map((index, node) => [[$(node).attr("id"), $(node).attr("st_name")]]).toArray();
//	console.log(valid_student_arr);
//	console.log(Object.fromEntries(valid_student_arr));
	var setting = {
		"session_name": $("#session_name").val(),
		"student_identifier_name": $("#id_name").val(),
		"exam_duration": parseInt($("#session_duration").val()),
		"grace_duration": parseInt($("#grace_duration").val()),
		"session_start":$("#start_exam_time").val() + " " + $("#start_exam_date").val(), // leave parsing to server
		"session_end": $("#end_exam_time").val() + " " + $("#end_exam_date").val(), 
		"show_result": $("#allow_result").is(":checked"),
		"show_score": $("#allow_score").is(":checked"),
		"student_list": Object.fromEntries(valid_student_arr)
	};
	console.log("Chosen setting: ", setting)
	return setting
}

function updateQuestionnaireSetting(setting) {
	// write back the appropriate settings into the fields.
	if("session_name" in setting) {
		$("#session_name").val(setting["session_name"]);
	}
	if("student_identifier_name" in setting) {
		$("#id_name").val(setting["student_identifier_name"]);
	}
	if("exam_duration" in setting) {
		$("#session_duration").val(setting["exam_duration"].toString());
	}
	if("grace_duration" in setting) {
		$("#grace_duration").val(setting["exam_duration"].toString());
	}
	// for time-related, re-split and update them again 
	if("session_start" in setting) {
		let start_data = setting["session_start"].split(" ");
		$("#start_exam_time").val(start_data[0]);
		$("#start_exam_date").val(start_data[1]);
	}
	if("session_end" in setting) {
		let end_data = setting["session_end"].split(" ");
		$("#end_exam_time").val(end_data[0]);
		$("#end_exam_date").val(end_data[1]);
	}
	// for checkbox 
	if("show_result" in setting) {
		$("#allow_result").prop("checked", setting["show_result"]);
	}
	if("show_score" in setting) {
		$("#allow_score").prop("checked", setting["show_score"]);
	}
	// student_list cannot be used here 
	$("#student_list").prop("disabled", true);
}

function check_group_score(current_group) {
	// for each possible group; check and build for corresponding values
	// group is 4-list of each question id 
	var data = Object.keys(current_group).map(k => [parseInt($("#group_" + k).val()), parseFloat($("#score_" + k).val()), current_group[k]]);
	console.log("Raw result", data, current_group, Object.entries(current_group));
	// Check phase.
	var err_type = data.map(function(item, index) {
		// console.log(item[2]);
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
	return [data, err_type]
}
