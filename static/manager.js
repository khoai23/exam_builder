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
