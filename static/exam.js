var getUrlParameter = function getUrlParameter(sParam) {
	var sPageURL = window.location.search.substring(1),
		sURLVariables = sPageURL.split('&'), sParameterName;
	for (let i = 0; i < sURLVariables.length; i++) {
		sParameterName = sURLVariables[i].split('=');
		if (sParameterName[0] === sParam) {
			return sParameterName[1] === undefined ? true : decodeURIComponent(sParameterName[1]);
		}
	}
	return false;
};

function runTimer(elapsed, remaining) {
	var total = elapsed + remaining;
	var id = setInterval(function() {
		let percentage = Math.min(elapsed / total, 100.0);
		if(elapsed >= total) {
			// quit increasing 
			clearInterval(id);
			// enforce submission here.
		}
		// set the value for the bar 
		//$("#timer").attr('aria-valuenow', percentage);
		$("#timer").css("width", (percentage * 100.0).toFixed(2) + "%")
		let rm = Math.floor(total - elapsed)
		$("#timer").text(`${Math.floor(rm / 60)}m${(rm % 60)}s`);
		elapsed += 0.25;
	}, 250); // every 1/4 sec
}

function listAnswers() {
	var radios = $("#exam_region").find("[id^=q_]");
	var answers = {};
	radios.each(function (index) {
		let indices = $(this).attr("id").split("_");
		let question_id = parseInt(indices[1]);
		let answer_id = parseInt(indices[2]);
		// console.log(indices);
		if($(this).is(":checked")) {
			// TODO if there is multiple answer_id to a question and notify it if that happens.
			answers[question_id] = answer_id;
		} else if(question_id in answers) {
			// slot already there, do nothing
		} else {
			// slot not exist, hollow it out
			answers[question_id] = null;
		}
	});
	return answers;
}

function updateModal() {
	// bind to opening of the modal; warn student on unanswered node
	// list all radio nodes. TODO support other variants too
	var has_unanswered = false;
	for (const [qid, aid] of Object.entries(listAnswers())) {
		if(aid == null) {
			// blank
			has_unanswered = true;
			// TODO update reviewing table as well
		}
	}
	if(has_unanswered) {
		$("#warning_label").show();
		$("#confirmation_submit").removeClass("button-primary").addClass("button-warning");
	} else {
		$("#warning_label").hide();
		$("#confirmation_submit").removeClass("button-warning").addClass("button-primary");
	}
}

$(document).ready(function() {
	// wrap to ensure that the document is fully instantalized before allowing this trigger
	// $("#confirmation_modal").on("show.bs.modal", updateModal); 
});

function submit(event) {
	// the modal confirmed submission; compile the answer list
	var answers = listAnswers();
	var submission = [];
	// bind to exam data indices
	for(let i=0; i<exam_data.length; i++) {
		submission.push(answers[i]);
	}
	console.log(submission); // view for now
	var base = window.location.origin;
	var submit_link = "submit?key=" + getUrlParameter("key");
	// send 
	$.ajax({
		url: submit_link, 
		type: "POST",
		data: JSON.stringify(submission), 
		contentType: "application/json",
		dataType: "json",
		success: function(data, textStatus, jqXHR){
			console.log("Received result: ", data);
			if(data["result"]) {
				// good submission; display finished region
				$("#finished_region").show();
				$("#exam_region").hide();
				$("#submit_region").hide();
				$("#finished_message").text("Answers had been submitted. Close the browser and await teacher responses.");
			} else {
				// something is wrong 
				if("error" in data) {
					// generic error; display 
					$("#finished_message").text("Error during submission: " + data["error"] + "\nYou may try again after a short delay.");
				} else {
					// without error = already submitted 
					$("#finished_region").show();
					$("#exam_region").hide();
					$("#submit_region").hide();
					$("#finished_message").text("Answers had already been submitted before.");
				}
			}
		}
	});
}
