// Implement arbitrary drag and drop to help making the scenario map. Extend later if needed to be used elsewhere
// Requirement - item must be absolute or relative
var startX=0, startY=0, dragX=0, dragY=0;
var dragElement = null;

var dragStartCallback = null; // this function if exist will be ran on first binding.
function dragMouseDown(event, mouseup_fn=dragMouseUp, mousemove_fn=dragPerform) {
	event = event || window.event;
	event.preventDefault();
	// record what is being affected.
	dragElement = $(event.target);
	// keep the mouse position
	startX = event.clientX;
	startY = event.clientY;
	// rebind for whole document
	$(document).on("mouseup", mouseup_fn);
	$(document).on("mousemove", mousemove_fn);
	if(dragStartCallback !== null) {
		dragStartCallback(dragElement, startX, startY);
	}
}

var dragFinishCallback = null; // this function if exist will be called with the released binding of all relevant functions. 
function dragMouseUp(event) {
	if(dragFinishCallback !== null) {
		dragFinishCallback(dragElement);
	}
	dragElement = null;
	$(document).off("mouseup", dragMouseUp);
	$(document).off("mousemove", dragPerform);
}

var dragPerformCallback = null; // this function if exist will be called during all dragPerform iteration. Use to update the properties
function dragPerform(event) {
	event = event || window.event;
	event.preventDefault();
	// calculate the delta movement and move the item accordingly 
	dragX = startX - event.clientX;
	dragY = startY - event.clientY;
	startX = event.clientX;
	startY = event.clientY;
	// use jquery's offset to do this movement thingie
	let offset = dragElement.offset();
	offset.left -= dragX;
	offset.top -= dragY;
	dragElement.offset(offset);
	if(dragPerformCallback != null) {
		dragPerformCallback(dragElement, offset);
	}
}

function setElementDragable(element) {
	element.on("mousedown", dragMouseDown);
}
