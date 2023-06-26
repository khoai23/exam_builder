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
		let cell = $("<td />");/*
		row.append(cell); cell.append(input_use);*/
		
		let input_correct_btn = $("<button class=\"btn btn-secondary dropdown-toggle\" id=\"correct\" data-toggle=\"dropdown\" aria-haspopup=\"true\" aria-expanded=\"false\">?</button>");
		let input_correct_dropdown = $("<div class=\"dropdown-menu\" /> aria-labelledby=\"correct\"");
		for(var i=1; i<=4;i++) input_correct_dropdown.append( $("<button class=\"btn btn-link\" onclick=select_correct_id(event)>" + i + "</button>") );
		let input_correct = $("<div class=\"correct_dropdown\" />");
		input_correct.append(input_correct_btn, input_correct_dropdown);
		let input_category = $("<input type=\"textarea\" class=\"category\"/>");
		let input_tags = $("<input type=\"textarea\" class=\"tag\"/>");
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
	// trim to prevent nonsense spacing
	let cues = ["#question_header", "#answer1_header", "#answer2_header", "#answer3_header", "#answer4_header"].map(id => $(id).val().trim());
	let cue_is_regex = $("#cue_is_regex").is(":checked");
	console.log("Upload to handle by server: ", current_text, cues, cue_is_regex);
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

function match_all(regex, str) {
	let matches = [];
	let m;
	while ((m = regex.exec(str)) !== null) {
		console.log("Caught match: ", m);
		matches.push(m);
	}
	return matches;
}

function convert_text() {
	// perform conversion with selected text and cues.
	let cues = ["#question_header", "#answer1_header", "#answer2_header", "#answer3_header", "#answer4_header"].map(id => $(id).val().trim());
	let cue_is_regex = $("#cue_is_regex").is(":checked");
	// console.log("Handle locally: ", current_text, cues, cue_is_regex);
	if(cue_is_regex) {
		if(cues[0].trim() != "") {
			cues = cues.map(val => new RegExp(val, "g"));
		} else {
			cues = cues.map(val => new RegExp(val, "g"));
			cues[0] = null; // if the question cue is not available; in ignore mode 
		}
	} else {
		// TODO find indices by string instead
	}
	let aw1_cue = cues[1];
	let question_indices = null;
	if(cues[0] !== null) {
		question_indices = [...current_text.matchAll(cues[0])].map(m => m.index);
	}
	let aw_indices = cues.slice(2).map(c => [...current_text.matchAll(c)].map(m => m.index));
	let problems = [];
	for(const match of current_text.matchAll(aw1_cue)) {
		// with every match position, attempt to find nearby cues and grab them into one region 
		let current_qidx = question_indices.filter(i => i < match.index).slice(-1)[0];
		let p = {"question": current_text.slice(current_qidx, match.index).replace(cues[0], "").trim()};
		let next_qidx = question_indices.filter(i => i > match.index)[0];
		if(next_qidx === undefined) {
			// found no next question, use maximum edge as default 
			next_qidx = current_text.length;
		}
		let aw2_index = aw_indices[0].filter(i => i > match.index)[0];
		let aw3_index = aw_indices[1].filter(i => i > match.index)[0];
		let aw4_index = aw_indices[2].filter(i => i > match.index)[0];
		// console.log("Indices: ", match.index, aw2_index, aw3_index, aw4_index, current_qidx, next_qidx);
		if(aw2_index !== undefined && aw2_index < next_qidx) {
			// a valid aw2 index found; cut and continue 
			p["answer1"] = current_text.slice(match.index, aw2_index).replace(cues[1], "").trim();
		} else {
			// defer to aw2 
			p["answer1"] = "";
			aw2_index = match.index;
		}
		if(aw3_index !== undefined && aw3_index < next_qidx) {
			// a valid aw3 index found; cut and continue 
			p["answer2"] = current_text.slice(aw2_index, aw3_index).replace(cues[2], "").trim();
		} else {
			// defer to aw3 
			p["answer2"] = "";
			aw3_index = aw2_index;
		}
		if(aw4_index !== undefined && aw4_index < next_qidx) {
			// a valid aw4 index found; cut and continue 
			p["answer3"] = current_text.slice(aw3_index, aw4_index).replace(cues[3], "").trim();
		} else {
			// defer to aw4 
			p["answer3"] = "";
			aw4_index = aw3_index;
		}
		// always cut the last answer out 
		p["answer4"] = current_text.slice(aw4_index, next_qidx).replace(cues[4], "").trim();
		// push in 
		problems.push(p);
	}
	// console.log(problems);
	populate_table(problems);
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
	download_blob(blob, filename);
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
		let correct = $(this).find("#correct").text();
		if(correct == "?") {
			// not selected; write as blank instead 
			correct = "";
		}
		row.push(correct);
		row.push($(this).find(".category").val(), $(this).find(".tag").val() );
		// console.log(row);
		rows.push(row);
	});
	if(rows.length > 0) {
		// console.log(rows);
		filename = $("#file_import")[0].files[0].name.replaceAll(" ", "_").split(".")[0] + ".csv";
		export_to_csv(filename, rows, ["question", "answer1", "answer2", "answer3", "answer4", "correct_id", "category", "tag", "special", "variable_limitation"]);
		$("#save_status").show().text("Exported to \"" + filename + "\"");
	} else {
		alert("No row selected; cannot export");
	}
}

// toggle selection of the use field
function toggle_use(event) {
	var all_use_checkboxes = $("#parse_table").find("input:checkbox");
	// to_state is true when at least one checkbox is unclicked, and false otherwise
	// console.log(all_use_checkboxes.toArray());
	let to_state = all_use_checkboxes.toArray().some(node => !$(node).is(":checked"));
	// console.log(all_use_checkboxes, to_state);
	all_use_checkboxes.each(function() { $(this).prop("checked", to_state); })
}

// select specific answer as correct.
function select_correct_id(event) {
	let value = $(event.currentTarget).text();
	// console.log("Clicked: ", event.currentTarget, value);
	$(event.currentTarget).closest(".correct_dropdown").find("#correct").text(value);
}

// editing shared category box; all other rows will follow
function update_category_all(event) {
	$(".category").val($(event.currentTarget).val());
}

function update_tag_all(event) {
	$(".tag").val($(event.currentTarget).val());
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
	// reset beforehand; reloads will need to re-specify again 
	$("#category_all").val(""); $("#tag_all").val("");
	// attach to category_all & tag_all
	$("#category_all").change(update_category_all);
	$("#tag_all").change(update_tag_all);
	// first reset 
	allow_upload();
});
