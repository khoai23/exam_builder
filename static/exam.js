function runTimer(elapsed, remaining) {
	var total = elapsed + remaining;
	var id = setInterval(function() {
		let percentage = Math.min(elapsed / total, 100.0);
		if(elapsed >= total) {
			// quit increasing 
			clearInterval(id);
		}
		// set the value for the bar 
		$("#timer").attr('aria-valuenow', percentage);
		let rm = Math.floor(total - elapsed)
		$("#timer").text(`${Math.floor(rm / 60)}h${(rm % 60)}s`);
		elapsed += 1.0;
	}, 1000); // every one sec
}
