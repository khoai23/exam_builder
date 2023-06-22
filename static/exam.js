var submitted = false;

function runTimer(elapsed, remaining) {
	var total = elapsed + remaining;
	if(total == 0) {
		console.log("No timer, do not run pbar");
		// happen with no timer; hide the timer bar and do not update 
		$("#timer_wrapper").hide();
		return;
	}
	var id = setInterval(function() {
		let percentage = Math.min(elapsed / total, 1.0);
		if(elapsed >= total) {
			// quit increasing 
			clearInterval(id);
			// enforce submission here.
			if(!submitted) {
				// force closing all regions
				$("#finished_region").show();
				$("#exam_region").hide();
				$("#submit_region").hide();
				// send the submission command
				submit(null, true);
				// reset the percentage 
				$("#timer").css("width", "100%");
				$("#timer").text("Finished.");
				// hide the autosubmit again
				$("#autosubmit_warning").hide()
			}
		}
		// set the value for the bar 
		//$("#timer").attr('aria-valuenow', percentage);
		$("#timer").css("width", (percentage * 100.0).toFixed(2) + "%")
		let rm = Math.floor(total - elapsed)
		$("#timer").text(`${Math.floor(rm / 60)}m${(rm % 60)}s`);
		if(0.8 < percentage && percentage <= 0.95) {
			$("#timer").addClass("bg-warning")
		} else if(0.95 < percentage) {
			$("#timer").removeClass("bg-warning").addClass("bg-danger")
			$("#autosubmit_warning").show()
		}
		elapsed += 0.25;
	}, 250); // every 1/4 sec
}

function listAnswers() {
	var answers = {};
	var radios = $("#exam_region").find("[id^=qr_]");
	radios.each(function (index) {
		let indices = $(this).attr("id").split("_");
		let question_id = parseInt(indices[1]);
		let answer_id = parseInt(indices[2]) + 1; // answers are submitted by index1 form (1-4) to follow data format
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
	var checkboxes = $("#exam_region").find("[id^=qc_]");
	checkboxes.each(function(index) {
		let indices = $(this).attr("id").split("_");
		let question_id = parseInt(indices[1]);
		let answer_id = parseInt(indices[2]) + 1; // answers are submitted by index1 form (1-4) to follow data format
		if($(this).is(":checked")) {
			// add an array in slot if not exist; add nothing if not.
			if(question_id in answers && answers[question_id] != null) {
				answers[question_id].push(answer_id);
			} else {
				answers[question_id] = [answer_id];
			}
		} else {
			if(! question_id in answers ) {
				// void out the answer to prevent missing option
				answers[question_id] = null;
			}
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

function submit(event, autosubmit) {
	// the modal confirmed submission; compile the answer list
	var answers = listAnswers();
	var submission = [];
	// bind to exam data indices
	for(let i=0; i<exam_data_length; i++) {
		submission.push(answers[i]);
	}
	console.log(submission); // view for now
	// var base = window.location.origin;
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
				if(autosubmit) {
					$("#finished_message").text("Answers had been auto-submitted. Close the browser and await teacher responses.");
				} else {
					$("#finished_message").text("Answers had been submitted. Close the browser and await teacher responses.");
				}
				submitted = true;
			} else {
				// something is wrong 
				if("error" in data) {
					// generic error; display 
					$("#finished_message").text("Error during submission: " + data["error"] + "\nYou may try again after a short delay.");
					// in autosubmit, re-enable the submit regions; in case that submission fails somehow and can be recovered.
					if(autosubmit)
						$("submit_region").show();
					submitted = false;
				} else {
					// without error = already submitted 
					$("#finished_region").show();
					$("#exam_region").hide();
					$("#submit_region").hide();
					$("#finished_message").text("Answers had already been submitted before.");
					submitted = true;
				}
			}
		},
		error: function(jqXHR, textStatus, error){
			console.log("Received error:", error);
			$("#finished_message").text("Connection error: " + textStatus + "\nError type: " + error.toString() );
		}
	});
}
