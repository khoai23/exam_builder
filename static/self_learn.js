var bpmnViewer = new BpmnJS({container: "#bpmn_canvas"});

async function load_graph_fron_xml(xml_content_or_json, clear_mode=false) {
	let xml_content = (typeof xml_content_or_json === 'string' || xml_content_or_json instanceof String) ? xml_content_or_json : xml_content_or_json.data;
	// console.log(xml_content);
	if(xml_content === undefined) {
		// if data is not available on disk; hack by getting from online link & then clear it 
		return open_graph_from_online_link(null, link=test_graph, mode="text", clear_mode=true);
	}
	try {
		await bpmnViewer.importXML(xml_content);
		// access viewer components
		var canvas = bpmnViewer.get('canvas');
		var overlays = bpmnViewer.get('overlays');
		// zoom to fit full viewport
		canvas.zoom('fit-viewport');
		if(clear_mode) {
			bpmnViewer.clear();
			console.log("Clear executed.");
		}
	} catch (err) {
		console.error('could not import BPMN 2.0 diagram', err);
	}
}


var test_graph = 'https://cdn.statically.io/gh/bpmn-io/bpmn-js-examples/dfceecba/starter/diagram.bpmn';
function open_graph_from_online_link(event, link=test_graph, mode="text", clear_mode=false) {
	$.get(link, result => load_graph_fron_xml(result, clear_mode=clear_mode), mode);
}

function open_graph_from_server(event) {
	return open_graph_from_online_link(event, "self_learn_download", "json");
}

function export_graph(event, graph_name="graph.bpmn") {
	// just console.log for now 
	bpmnViewer.saveXML({ format: true }).then(function(result) {
		console.log(result.xml)
		const blob = new Blob([result.xml], {type: 'text/plain'});
		let url = window.URL.createObjectURL(blob);
		let link = $("#hidden_xml_link");
		link.attr("href", url).attr("download", graph_name);
		link[0].click();
	});
	console.log("Export should be done now");
}

function upload_graph_into_server(event, server_location="") {
	// guess I can just push the entire thing as string; what's the harm?
	bpmnViewer.saveXML({ format: true}).then(function(result) {
		$.post({
			url: "self_learn_upload",
			data: result.xml,
			contentType: "text/html",
			dataType: "html"
		}, function(data, status) {
			console.log("Upload done", data, status);
		})
	});
}
