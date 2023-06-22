// works for both session_manager and normal manager 
var current_delete_session_key = null;
var current_delete_admin_key = null;

function show_confirmation_delete_session(session_key, admin_key) {
	current_delete_session_key = session_key;
	current_delete_admin_key = admin_key;
	var current_name = $("tr" + ".session_" + session_key).find("#session_name").text();
	//console.log(current_name, session_key, admin_key);
	$("#confirm_session_name").text(current_name);
	$("#confirm_session_id").text(current_delete_session_key);
	$("#confirm_modal").modal('show');
};

function delete_session() {
	// todo add confirmation
	$.ajax({
		url: "delete_session?template_key=" + current_delete_session_key + "&key=" + current_delete_admin_key,
		type: "DELETE",
		success: function(data, textStatus, jqXHR) {
			console.log(data);
			if(data["deleted"]) {
				// is true means session no longer exist; remove corresponding rows 
				$("tr.session_" + current_delete_session_key).remove();
			}
			if(data["result"]) {
				$("#status_text").removeClass("text-danger").addClass("text-success").text("Session deleted.");
			} else {
				$("#status_text").removeClass("text-success").addClass("text-danger").text("Error: " + data["error"]);
			}
			// regardless of result, this will clear out the current session key & admin key 
			current_delete_session_key = null;
			current_delete_admin_key = null;
		},
		error: function(jqXHR, textStatus, error){
			console.log("Received error:", error);
			$("#status_text").removeClass("text-success").addClass("text-danger").text("Internet error: " + error.toString());
		}
	});
	// also hide the modal
	$("#confirm_modal").modal('hide');
}

function update_id_col(event) {
	$("#id_col_dropdown").text($(event.currentTarget).text().trim());
}

function update_fill_col(event) {
	$("#fill_col_dropdown").text($(event.currentTarget).text().trim());
}

function retrieve_student_score() {
	// retrieve score from shown table, and throw it into a dictionary
	let student_data = $("tbody").find("tr").map((index, node)=> [[$(node).attr("st_id"), $(node).attr("st_sc")]]);
	return Object.fromEntries(student_data)
}

function open_fill_target(event) {
	// check if column/row is correct 
	if($("#id_col_dropdown").text().trim() == "?") {
		$("#status_label").text("Must select ID column before using fill mode.").show();
	} else if($("#fill_col_dropdown").text().trim() == "?") {
		$("#status_label").text("Must select Fill column before using fill mode.").show();
	} else {
		// clicking the hidden file input to allow upload. Chain to fill_target_selected
		$("#fill_target").click()
	}
}


function fill_target_selected(event) {
	// upon change, open the file in XLSX
	const target_file = event.currentTarget.files[0];
	// console.log(target_file, target_file.name);
	var reader = new FileReader();
	reader.onload = function(e) {
		var data = reader.result;
		var workbook = XLSX.read(data, {type: "binary"});
		var first_sheet = workbook.Sheets[workbook.SheetNames[0]];
		// read values for 100 rows for now, and with any matched result, put the corresponding score into the file 
		let id_col =  $("#id_col_dropdown").text();
		let fill_col = $("#fill_col_dropdown").text();
		let scores = retrieve_student_score();
		for(const index of [...Array(100).keys()]) {
			let cell = first_sheet[id_col + index.toString()];
			if(cell !== undefined && cell.w in scores) {
				// console.log(cell.w, scores[cell.w]);
				// write value into cell 
				XLSX.utils.sheet_add_aoa(first_sheet, [[scores[cell.w]]], {origin: fill_col + index.toString()});
				first_sheet[fill_col + index.toString()].w = scores[cell.w]
				console.log("Written to", fill_col + index.toString(), "with", scores[cell.w], "true", first_sheet[fill_col + index.toString()]);
			}
			// console.log(cell);
		}
		// upon finish; create a blob object for this new file 
		// cool, actually have no need to run blob conversion
		XLSX.writeFileXLSX(workbook, target_file.name.split(".")[0] + "_filled.xlsx");
	};
	reader.onerror = function(e) {
		console.log("Encounter read error: ", e);
		$("#status_label").text("Error: " + e.toString());
	};
	reader.readAsBinaryString(target_file);
}

// retrieve_session_data; default to 3s timeout, can be extended
function retrieve_session_data(timeout=3) {
	$.ajax({
		url: "single_session_data?key=" + getUrlParameter("key") + "&template_key=" + getUrlParameter("template_key"),
		type: "GET",
		success: function(data, textStatus, jqXHR){
			if(data["result"]) {
				data = data["data"]; // access internal field
				// console.log("Received data: ", data);
				// populate everything here.
				let question_template = data["template"];
				// console.log(data["student"]);
				for(const [student_key, student_data] of Object.entries(data["student"])) {
					// console.log("Drawing for ", student_key, " with data", student_data, "and template", question_template);
					add_new_student(student_key, student_data);
					draw_for_student(student_key, student_data, question_template, data["maximum_score"]);
				}
			} else {
				console.log("Cannot get session data, error: ", data["error"]);
			}
		},
		error: function(jqXHR, textStatus, error){
			console.log("Received error:", error);
		},
		timeout: timeout * 1000
	})
}

// try to add a new student with specific key into existing table.
// student will be in "Working" state, as draw_for_student will switch it over anyway 
function add_new_student(key, obj) {
	if($("#" + key).length == 0) {
		console.log("Detected student with no corresponding row", key);
		// only attempt to add when there is no such row 
		// create row and respective cells
		let row = $("<tr id=\"" + key +"\" st_id=\"" + obj["student_id"] + "\" st_sc=\"" + obj["score"] + "\"></tr>");
		row.append( [  
			$("<td>" + key + "</td>"),
			$("<td>" + obj["student_name"] + "</td>"),
			$("<td colspan=\"2\" id=\"working_" + key + "\"> Working </td>"),
			$("<td><a href=\"enter?key=" + key + "\">Exam Link</a></td>"),
		]);
		// append the row to the tbody 
		$("tbody").append(row);
	}
}

// loop variant of retrieve_session_data; will trigger the function every {interval}s.
var current_retrieve_id = null;
function autoupdate_session_data(interval=30, start_first=true) {
	if(current_retrieve_id !== null) {
		console.log("Interval already set, interval id", current_retrieve_id);
		return;
	}
	if(start_first) { // with this enable; run an instance immediately
		retrieve_session_data();
	}
	current_retrieve_id = setInterval(retrieve_session_data, interval * 1000);
}

// removing the autoupdate; useful for later as toggle option
function remove_autoupdate() {
	if(current_retrieve_id === null) {
		console.log("Interval is not set, nothing to clear");
		return;
	}
	clearInterval(current_retrieve_id);
	current_retrieve_id = null;
}

function draw_for_student(key, obj, question_template, maximum_score=10) {
	// retrieve corresponding div to draw
	if(obj["score"] === undefined) {
		// No score; student should still be working 
		console.log("Student with key " + key + " haven't submitted yet; ignoring")
		return;
	}
	var graph_slot;
	if($("#working_" + key).length > 0) {
		// is a working slot; update it with graph+number 
		let working_cell = $("#working_" + key);
		graph_slot = $("<div id=\"graph_" + key + "\" style=\"max-width: 120px; max-height: 120px\"></div>");
		let graph_cell = $("<td></td>").append(graph_slot);
		graph_cell.insertAfter(working_cell);
		let score_cell = $("<td><span class=\"text-success\"> " + obj["score"].toFixed(2) + " </span><span> / " + maximum_score.toFixed(2) + " </span></td>");
		score_cell.insertAfter(graph_cell);
		// insertion complete; throwing the original away
		working_cell.remove();
	} else {
		graph_slot = $("#graph_" + key); 
	}
	if(graph_slot.length == 0) {
		// No valid slot 
		console.log("No valid slot for key " + key + ", check for failure");
	} else if(graph_slot.attr("drawn")) {
		// Slot found but already drawn
		// console.log("Already drawn data for key " + key + "; ignoring");
	} else {
		// Slot found and draw-able; starting
		// parsing data depending on the template 
		let index = 0;
		let detailed_score = obj["detailed_score"];
		let draw_data = [["Section", "Score"]];
		for(const [number, ppc, _] of question_template) {
			let correct_score = 0; let wrong_score = 0;
			for(let i=index; i < index + number; i++) {
				if(detailed_score[i] == 0) {
					wrong_score += ppc;
				} else {
					correct_score += ppc;
				}
				// TODO check score is equal to ppc in non-multiple, non-partialscore
			}
			let secname = "Section_" + (index+1).toString() + "_" + (index+number+1).toString();
			draw_data.push( [secname + "_correct", correct_score], [secname + "_wrong", wrong_score] );
			// set the index to the last 
			index = index + number;
		}
		// draw the image appropriately; hiding the _wrong sections 
		const data = google.visualization.arrayToDataTable(draw_data);
		const options = {
			legend: 'none',
			tooltip: { trigger: 'none' },
			slices: Object.fromEntries( [...draw_data.keys()].filter(x => (x % 2 == 1)).map(x => [x, {color: 'transparent'}]) ),
			width: 100,
			height: 100,
		};
		const chart = new google.visualization.PieChart(graph_slot[0]);
		chart.draw(data, options);
		// mark the slot drawn, so subsequent run dont waste effort
		graph_slot.attr("drawn", true);
	}
}


// draw a chart by a specified elements. Test function, throw away soon
function draw_chart_for_student(element) {
	let student_key = element.attr("id").replace("graph_");
	if(student_key.length > 0) {
		// valid key, started retrieving data 
		let chart_type = element.attr("chart_type");
		//let chart = bb.generate({
		//	bindto: "#" + element.attr("id"),
		//	data: {
		//		x: "x",
		//		columns: [
		//			["x", "Subject A", "Subject B", "Subject C"],
		//			["Student", 5, 8, 5]
		//		],
		//		type: "radar",
		//		labels: true
		//	},
		//	radar: {
		//		axis: { max: 10 },
		//		level: { depth: 5 }
		//	}
		//});
		//chart.load();
		const data = google.visualization.arrayToDataTable([
			["Student Name", "Student Score"],
			["Subject A", 5],
			["Subject A Loss", 5],
			["Subject B", 7],
			["Subject B Loss", 3],
			["Subject C", 8],
			["Subject C Loss", 2],
		]);
		const options = { 
			legend: 'none',
			slices: {
				1: { color: 'transparent' },
				3: { color: 'transparent' },
				5: { color: 'transparent' }
			}
		};
		const chart = new google.visualization.PieChart(element[0]);
		chart.draw(data, options);
	} else {
		console.log("No valid student key for ", element.attr("id"));
	}
}

