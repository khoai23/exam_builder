function run_lazyload() {
	// apparently chromiums support loading=lazy; let's use that and see if it works or we need library for this.
	$("img").each(function(i, it){ $(it).attr("loading", "lazy"); });
}

function create_accordion_section(base_item, section_tag="h2") {
	// lesson's h2 should indicate full sections; convert all children to matching items.
	all_data = base_item.children();
	// TODO should not trigger if amount of h2 items <= 1
	var current_section = null;
	// delete & re-add
	base_item.empty();
	if(!base_item.attr("id")) {
		base_item.attr("id", "base");
	}
	all_data.each(function (index, item){ 
		let current_item = $(item);
		if(current_item.is("h2")) {
			let section_name = "section_bvkwhs_" + index.toString(); // random text to avoid collision
			let current_section_wrapper = $("<div>").attr("class", "card");
			let current_section_button = $("<button>").attr("class", "btn btn-link").text(current_item.text());
			current_section = $("<div>").attr("class", "collapse").attr("id", section_name);
			let ref_current_section = current_section; // allow this variable in let to allow access from click
			current_section_wrapper.append($("<div>").attr("class", "card-header").append(current_section_button));
			current_section_wrapper.append(current_section);
			current_section_button.click(function(event) { 
				ref_current_section.collapse('toggle'); 
			})
			// put back 
			base_item.append(current_section_wrapper)
		} else {
			if(current_section === null) {
				// non-sectionized data; just add back 
				base_item.append(current_item);
			} else {
				// sectionized data; just add into it 
				current_section.append(current_item);
			}
		}
	});
}

function create_interactive_section(base_item, question_header="❔") {
	// lesson's h5/h6 is reserved to create an interactive question-answer pairing. The h5 when clicked will toggle the h6 to visible
	// TODO adding LN-esque point-based system on clicking.
	// console.log(base_item);
	all_data = base_item.children();
	all_data.each(function(index, item) {
		// console.log(index, item, $(item).prop("tagName"));
		let current_item = $(item);
		if(index > 0 && current_item.prev().is("h5")) {
			// detect prior H5;
			if(current_item.is("h6")) {
				// self is H6, in FAQ mode. Binding the collapse function accordingly.
				current_item.addClass("collapse");
				let question_badge = $("<span>").attr("class", "badge badge-info ml-2").text("?");
				current_item.prev().append(question_badge);
				// current_item.prev().text(question_header + " " + current_item.prev().text());
				current_item.prev().click(function() {
					// if click & item is collapsed, launch it; if not, just ignore 
					if(current_item.hasClass("collapse")) {
						current_item.collapse('show');
						question_badge.removeClass("badge-info").addClass("badge-success");
					}
				});
			}
		}
	});
}

function create_link_jump_section() {
	// end-of-section h5 can trigger the next section for now. TODO allow triggering abitrary sections
}
