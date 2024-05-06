<div class="modal fade" id="editModal" tabindex="-1" role="dialog" aria-labelledby="editModalTitle" aria-hidden="true">
  <div class="modal-dialog" role="document">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="editModalTitle">New message</h5>
        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
      <div class="modal-body">
        <form>
          <div class="form-group">
            <label for="edit_true_text" class="col-form-label">True Input:</label>
            <textarea class="form-control tex2jax_ignore" id="edit_true_text"></textarea>
          </div>
          <div class="form-group">
            <label for="edit_display" class="col-form-label">Display</label>
            <div id="edit_display" style="white-space: pre-wrap"></div>
          </div>
        </form>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
        <button type="button" class="btn btn-primary" onclick="_submit_edit_modal()">Update</button>
      </div>
    </div>
  </div>
