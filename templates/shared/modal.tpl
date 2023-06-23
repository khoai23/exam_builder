<div class="modal fade" id="confirmation_modal" tabindex="-1" role="dialog" aria-labelledby="confirmation_title" aria-hidden="true">
	<div class="modal-dialog" role="document">
		<div class="modal-content">
			<div class="modal-header">
				<h5 class="modal-title" id="confirmation_title">Confirm</h5>
				<button type="button" class="close" data-dismiss="modal" aria-label="Close">
					<span aria-hidden="true">&times;</span>
				</button>
			</div>
			<div class="modal-body" id="modal_body">
			</div>
			<div class="modal-footer">
				<button id="confirmation_cancel" type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
				<button id="confirmation_submit" type="button" class="btn btn-primary" data-dismiss="modal" onclick="perform_confirm_modal(event)">OK</button>
			</div>
		</div>
	</div>
</div>
