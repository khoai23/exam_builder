// update the highlighting of the text, depending on what
//const parser = new DOMParser();
var current_text = "";

// black magic section: taken from https://docxtemplater.com/faq/#how-can-i-retrieve-the-docx-content-as-text
function str2xml(str) {
    if (str.charCodeAt(0) === 65279) {
        // BOM sequence
        str = str.substr(1);
    }
    return new DOMParser().parseFromString(str, "text/xml");
}

// get the docx content; apparently this wont even need docxtemplater
function getParagraphs(content) {
    const zip = new PizZip(content);
	console.log(zip);
    const xml = str2xml(zip.files["word/document.xml"].asText());
    const paragraphsXml = xml.getElementsByTagName("w:p");
    const paragraphs = [];

    for (let i = 0, len = paragraphsXml.length; i < len; i++) {
        let fullText = "";
        const textsXml =
            paragraphsXml[i].getElementsByTagName("w:t");
        for (let j = 0, len2 = textsXml.length; j < len2; j++) {
            const textXml = textsXml[j];
            if (textXml.childNodes) {
                fullText += textXml.childNodes[0].nodeValue;
            }
        }

        paragraphs.push(fullText);
    }
    return paragraphs;
}

// read the text from txt file and display it as is
function update_text(event) {
	// TODO support reading Word; I know I did this some time ago
	var target_file = event.currentTarget.files[0];
	var fr = new FileReader();
	if(target_file.name.includes(".txt")) {
		// txt file; read as utf-8 formatted 
		console.log("File", target_file.name, "is text; handling..")
		fr.onload = function(){
			current_text = fr.result;
			// convert current text to HTML formatted
			//let dom = parser.parseFromString(current_text, "text/html");
			//console.log(current_text);
			//$("#raw_text").html(current_text.replaceAll("\n", "<br \>"));
			update_highlight(event);
			$("#raw_text_wrapper").show();
			// allow_upload();
		}
		fr.readAsText(target_file, "utf-8");
	} else if (target_file.name.includes(".docx")) {
		console.log("File", target_file.name, "is docx; handling..")
		fr.onload = function() {
			let content = fr.result;
			// const zip = new PizZip(content);
			// const doc = new window.docxtemplater(zip);
			current_text = getParagraphs(content).join("\n");
			//$("#raw_text").html(current_text.replaceAll("\n", "<br \>"));
			update_highlight(event);
			$("#raw_text_wrapper").show();
			//allow_upload();
		}
		fr.readAsBinaryString(target_file);
	} else {
		alert("Invalid file:`", target_file.name, "`; please choose a valid option (from docx/txt).")
	}
}

function update_highlight(event) {
	// reload all possible markup with its own 
	var highlighted_text = current_text;
	var is_regex = $("#cue_is_regex").is(":checked");
	for (const [id, type] of [["#question_header", "text-light bg-dark"], ["#answer1_header", "text-light bg-primary"], ["#answer2_header", "text-light bg-success"], ["#answer3_header", "text-light bg-danger"], ["#answer4_header", "text-black bg-warning"]]) {
		let header = $(id).val();
		if(header.length > 0) {
			// is a valid header, find and colorize all instance in 
			let searcher = header;
			if(is_regex) {
				searcher = new RegExp("(" + header + ")", "g");
			}
			highlighted_text = highlighted_text.replaceAll(searcher, "<span class=\"" + type + "\">$1</span>");
		}
	}
	// load into the raw_text field again 
	$("#raw_text").html(highlighted_text.replaceAll("\n", "<br \>"));
	// console.log(highlighted_text);
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
			let input = $("<div id=\"" + q + "\" style=\"white-space: pre-wrap;\" contenteditable />");
			let cell = $("<td />");
			row.append(cell); cell.append(input);
			input.text(p[q].trim());
		}
		// correct (dropdown 1-4), category (textarea), tag (textarea), use (checkbox)
		// just use checkbox for now
		let input_use = $("<input type=\"checkbox\" id=\"use\"/>"); 
		let cell = $("<td />");
		row.append(cell); cell.append(input_use);
		/*
		let input_correct_btn = $("<button class=\"btn btn-secondary dropdown-toggle\" id=\"correct\" data-toggle=\"dropdown\" aria-haspopup=\"true\" aria-expanded=\"false\">?</button>");
		let input_correct_dropdown = $("<div class=\"dropdown-menu\" /> aria-labelledby=\"correct\"");
		for(var i=1; i<=4;i++) input_correct_dropdown.append( $("<button class=\"btn btn-link\" onclick=select_correct_id(event)>" + i + "</button>") );
		let input_correct = $("<div class=\"correct_dropdown\" />");
		input_correct.append(input_correct_btn, input_correct_dropdown);
		let input_category = $("<input type=\"textarea\" id=\"category\"/>");
		let input_tags = $("<input type=\"textarea\" id=\"tag\"/>");
		for(ip of [input_correct, input_category, input_tags, input_use]) {
			let cell = $("<td />");
			row.append(cell); cell.append(ip);
		}*/
	}
	// show the table if needed.
	$("#parse_table_wrapper").show();
}

function upload_convertable() {
	// upload the raw text as string, this simplifies flow when dealing with doc/docx
	// trim to prevent nonsense spacing
	let cues = ["#question_header", "#answer1_header", "#answer2_header", "#answer3_header", "#answer4_header"].map(id => $(id).val().trim());
	let cue_is_regex = $("#cue_is_regex").is(":checked");
	console.log(current_text, cues, cue_is_regex);
	let payload = JSON.stringify({"text": current_text, "cues": cues, "cue_is_regex": cue_is_regex});
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

// gotten from https://stackoverflow.com/questions/14964035/how-to-export-javascript-array-info-to-csv-on-client-side
function export_to_csv(filename, rows, headers) {
	var processRow = function (row) {
		var finalVal = '';
		for (var j = 0; j < row.length; j++) {
			var innerValue = row[j] === null ? '' : row[j].toString();
			if (row[j] instanceof Date) {
				innerValue = row[j].toLocaleString();
			};
			var result = innerValue.replace(/"/g, '""');
			if (result.search(/("|,|\n)/g) >= 0)
				result = '"' + result + '"';
			if (j > 0)
				finalVal += ',';
			finalVal += result;
		}
		return finalVal + '\n';
	};

	var csvFile = '';
	if(headers !== undefined) {
		csvFile += headers.join(",") + '\n';
	}
	for (var i = 0; i < rows.length; i++) {
		csvFile += processRow(rows[i]);
	}

	var blob = new Blob([csvFile], { type: 'text/csv;charset=utf-8;' });
	if (navigator.msSaveBlob) { // IE 10+
		navigator.msSaveBlob(blob, filename);
	} else {
		var link = document.createElement("a");
		if (link.download !== undefined) { // feature detection
			// Browsers that support HTML5 download attribute
			var url = URL.createObjectURL(blob);
			link.setAttribute("href", url);
			link.setAttribute("download", filename);
			link.style.visibility = 'hidden';
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
		}
	}
}

function save_csv(event) {
	// convert all rows to corresponding fields
	var table_rows = $("#parse_table").find("tbody").find("tr");
	var rows = [];
	table_rows.each(function() {
		//console.log($(this).find("#use"));
		if(!$(this).find("#use").is(":checked")) {
			// ignore if question is not checked
			return;
		}
		let row = ["#question", "#answer1", "#answer2", "#answer3", "#answer4"].map(id => $(this).find(id).text());
		//console.log(row);
		rows.push(row);
	});
	if(rows.length > 0) {
		//console.log(rows);
		filename = $("#file_import")[0].files[0].name.replaceAll(" ", "_").split(".")[0] + ".csv";
		export_to_csv(filename, rows, ["Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4"]);
		$("#save_status").show().text("Exported to \"" + filename + "\"");
	} else {
		alert("No row selected; cannot export");
	}
}

// toggle selection of the use field
function toggle_use(event) {
	var all_use_checkboxes = $("#parse_table").find("input:checkbox");
	// to_state is true when at least one checkbox is unclicked, and false otherwise
	console.log(all_use_checkboxes.toArray());
	let to_state = all_use_checkboxes.toArray().some(node => !$(node).is(":checked"));
	// console.log(all_use_checkboxes, to_state);
	all_use_checkboxes.each(function() { $(this).prop("checked", to_state); })
}

// select specific answer as correct.
function select_correct_id(event) {
	console.log("Clicked: ", event.currentTarget);
}

//function to hardfix specific templates.
function choose_template(index) {
	// console.log(index);
	switch(index) {
		case 0:
			["#question_header", "#answer1_header", "#answer2_header", "#answer3_header", "#answer4_header"].map(id => $(id).prop("disabled", false));
			$("#cue_is_regex").prop("checked", false);
			break;
		case 1:
			["#question_header", "#answer1_header", "#answer2_header", "#answer3_header", "#answer4_header"].map(id => $(id).prop("disabled", true));
			$("#question_header").val("Câu \\d+(:|\\.)");
			$("#answer1_header").val("A\\.");
			$("#answer2_header").val("B\\.");
			$("#answer3_header").val("C\\.");
			$("#answer4_header").val("D\\.");
			$("#cue_is_regex").prop("checked", true);
			break;
		case 2:
			["#question_header", "#answer1_header", "#answer2_header", "#answer3_header", "#answer4_header"].map(id => $(id).prop("disabled", true));
			$("#question_header").val("Bài \\d+(:|\\.)");
			$("#answer1_header").val("A\\.");
			$("#answer2_header").val("B\\.");
			$("#answer3_header").val("C\\.");
			$("#answer4_header").val("D\\.");
			$("#cue_is_regex").prop("checked", true);
			break;
		default:
			// for safety, unrecognized value re-enable all fields
			["#question_header", "#answer1_header", "#answer2_header", "#answer3_header", "#answer4_header"].map(id => $(id).prop("disabled", false));
			break;
	}
	update_highlight();
}

// allow copying table directly to clipboard 
function copy_to_clipboard(event) {
	var copy_table = $("tbody").clone();
	// removing last row of every internal row 
	copy_table.find("tr td:last-child").remove();
	console.log(copy_table);
	// convert to blob 
	// var blob = new Blob([copy_table[0].outerHTML], { type: "text/html" });
	copy_table.hide()
	$("table").append(copy_table);
	var range = document.createRange();
	range.selectNode(copy_table[0]);
	window.getSelection().addRange(range) ;
	document.execCommand('copy');
	copy_table.remove();
}

$(document).ready(function() {
	// first reset 
	allow_upload();
});