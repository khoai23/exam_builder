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
