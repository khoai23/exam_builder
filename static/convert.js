// update the highlighting of the text, depending on what
//const parser = new DOMParser();
var current_text = "";

// read the text from txt file and display it as is
function update_text(event) {
	// TODO support reading Word; I know I did this some time ago
	var fr=new FileReader();
	fr.onload=function(){
		current_text = fr.result;
		// convert current text to HTML formatted
		//let dom = parser.parseFromString(current_text, "text/html");
		//console.log(current_text);
		$("#raw_text").html(current_text.replaceAll("\n", "<br \>"));
		$("#raw_text_wrapper").show();
		allow_upload();
	}
	fr.readAsText(event.currentTarget.files[0], "utf-8");
}

function update_highlight(event) {
	// reload all possible markup with its own 
	var highlighted_text = current_text;
	for (const [id, type] of [["#question_header", "text-light bg-dark"], ["#answer1_header", "text-light bg-primary"], ["#answer2_header", "text-light bg-success"], ["#answer3_header", "text-light bg-danger"], ["#answer4_header", "text-black bg-warning"]]) {
		let header = $(id).val();
		if(header.length > 0) {
			// is a valid header, find and colorize all instance in 
			highlighted_text = highlighted_text.replaceAll(header, "<span class=\"" + type + "\">" + header + "</span>");
		}
	}
	// load into the raw_text field again 
	$("#raw_text").html(highlighted_text.replaceAll("\n", "<br \>"));
	console.log(highlighted_text);
	// also reset uploading button to correct state
	allow_upload();
}

function allow_upload() {
	let has_empty = ["#answer1_header", "#answer2_header", "#answer3_header", "#answer4_header"].some(id => $(id).val().length == 0);
	$("#upload_btn").prop("disabled", has_empty || current_text.length == 0);
}

// populate the parse table with the values loaded.
function populate_table(problems) {
	var table_content = $("#parse_table").find("tbody");
	// first wipe the table clean
	table_content.empty();
	// add the problems to the table
	for(p of problems) {
		// each of the problem correspond to a row 
		let row = $("<tr />");
		table_content.append(row);
		// for q/a1-4; each row is a textarea 
		for(q of ["question", "answer1", "answer2", "answer3", "answer4"]) {
			let input = $("<pre id=\"" + q + "\" contenteditable />");
			let cell = $("<td />");
			row.append(cell); cell.append(input);
			input.text(p[q]);
		}
		// correct (dropdown 1-4), category (textarea), tag (textarea), use (checkbox)
		let input_correct_btn = $("<button class=\"btn btn-secondary dropdown-toggle\" id=\"correct\" data-toggle=\"correct_dropdown\" aria-haspopup=\"true\" aria-expanded=\"false\">?</button>");
		let input_correct_dropdown = $("<div class=\"dropdown-menu\" /> aria-labelledby=\"correct\"");
		for(var i=1; i<=4;i++) input_correct_dropdown.append( $("<button class=\"btn btn-link\">" + i + "</button>") );
		let input_correct = $("<div class=\"correct_dropdown\" />");
		input_correct.append(input_correct_btn, input_correct_dropdown);
		let input_category = $("<input type=\"textarea\" id=\"category\"/>");
		let input_tags = $("<input type=\"textarea\" id=\"tag\"/>");
		let input_use = $("<input type=\"checkbox\" id=\"use\"/>");
		for(ip of [input_correct, input_category, input_tags, input_use]) {
			let cell = $("<td />");
			row.append(cell); cell.append(ip);
		}
	}
	// show the table if needed.
	$("#parse_table_wrapper").show();
}

function upload_convertable() {
	// upload the raw text as string, this simplifies flow when dealing with doc/docx
	let cues = ["#question_header", "#answer1_header", "#answer2_header", "#answer3_header", "#answer4_header"].map(id => $(id).val());
	console.log(cues);
	let payload = JSON.stringify({"text": current_text, "cues": cues});
	$.ajax({
			url: "convert_text_to_table", 
			type: "POST",
			data: payload, 
			contentType: "application/json",
			dataType: "json",
			success: function(data, textStatus, jqXHR){
				if(data["result"]) {
					populate_table(data["problems"]);
				} else {
					console.log("Failed, error data:", data);
				}
			},
			error: function(jqXHR, textStatus, error){
				// TODO check failure here
				console.log("Failure with error: " + error);
			}
	});
	// console.log($("#file_import").prop("files")[0]);
}

$(document).ready(function() {
	// first reset 
	allow_upload();
});