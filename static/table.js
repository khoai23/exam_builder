function get_selected_question_ids() {
	var valid_id = [];
	var checklist = $("#question_table").find("[id^=use_question_]");
	// find all use_question_ item in the table 
	//console.log(checklist);
	checklist.each(function(index) {
//		console.log($(this)); // dunno why each returned an object though
		if($(this)[0].checked) valid_id.push(index); 
	});
	return valid_id;
}

function select_category(event) {
	// select a category depending on the clicked button 
	var category = event.currentTarget.innerText;
	// filter all fields that does not contain this category 
	$("tbody").find("tr").each(function(index) {
		let row_cat = $(this).find(".category_cell").first().text().trim();
		console.log(row_cat);
		if(row_cat !== category) 
			$(this).hide();
		else 
			$(this).show();
	});
	// update the clear filter and show it 
	$("#filter_category_clear").text(category + "(X)");
	$("#filter_category_clear").show();
}

// clear out the selected category 
function clear_category(event) {
	$("tbody").find("tr").each(function(index) { $(this).show(); });
	// hide the clear filter 
	$("#filter_category_clear").hide();
}

function toggle_select_tag(event) {
	// select/deselect all items by a chosen tag. if not all items selected, use select mode
	var target_tag = event.currentTarget.innerText;
	// get all same-tag row; extract the checkboxes
	var boxes = $("tbody").find("tr").filter(function(index) {
		return $(this).find(".tag_cell:contains('" + target_tag + "')").length > 0;
	}).find("[id^=use_question_]");
	console.log(boxes);
	if(boxes.filter(":checked").length == boxes.length) {
		// all box checked; deselect 
		boxes.each(function() { $(this).prop("checked", false); })
	} else {
		// zero/some box checked; select
		boxes.each(function() { $(this).prop("checked", true); })
	}
}

function toggle_all_tag(event) {
	// select/deselect the visible items.
	var boxes = $("tbody").find("tr").filter(function(index) {
		return $(this).is(":visible"); // get only the visible boxes
	}).find("[id^=use_question_]");
	if(boxes.filter(":checked").length == boxes.length) {
		// all box checked; deselect 
		boxes.each(function() { $(this).prop("checked", false); })
	} else {
		// zero/some box checked; select
		boxes.each(function() { $(this).prop("checked", true); })
	}
}



