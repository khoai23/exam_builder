<div class="modal fade" id="edit_modal" tabindex="-1" role="dialog" aria-labelledby="editModalTitle" aria-hidden="true">
  <div class="modal-dialog" role="document">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="edit_modal_title">New message</h5>
        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
      <div class="modal-body">
        <form id="edit_single_value">
          <div class="form-group">
            <label for="edit_true_text" class="col-form-label">True Input:</label>
            <textarea class="form-control tex2jax_ignore" id="edit_true_text"></textarea>
          </div>
          <div class="form-group">
            <label for="edit_display" class="col-form-label">Display</label>
            <div id="edit_display" style="white-space: pre-wrap"></div>
          </div>
        </form>
        <form id="edit_full_question" class="d-flex">
          <ul class="nav nav-tabs flex-column mr-2" id="question_type_tab" role="tablist">
          {% for question_type, question_type_label in [["generic", "Default"], ["is_single_equation", "Single Equation"], ["is_fixed_equation", "Fixed Equation"], ["is_single_option", "Randomized Pairs"]] %}
            <li class="nav-item" role="presentation">
              <button class="nav-link" id="{{question_type}}_tab" role="tab" onclick="switch_question_mode(event)">{{question_type_label}}</button>
            </li>
          {% endfor %}
          </ul>
          <div id="edit_content" class="tab-content">
            <!-- question - full row always -->
            <div class="form-group">
              <label for="edit_question">Question</label>
              <textarea class="form-control tex2jax_ignore" id="edit_question"></textarea>
              <div id="edit_question_display" style="white-space: pre-wrap"></div>
            </div>
            <!-- answer block - 2 per row on larger form -->
            <div id="edit_answer_set_1" class="row">
              <div class="form-group col-md-6 col-sm-12">
                <label for="edit_answer1">Answer 1</label>
                <textarea class="form-control tex2jax_ignore" id="edit_answer1"></textarea>
                <div id="edit_answer1_display" style="white-space: pre-wrap"></div>
              </div>
              <div class="form-group col-md-6 col-sm-12">
                <label for="edit_answer2">Answer 2</label>
                <textarea class="form-control tex2jax_ignore" id="edit_answer2"></textarea>
                <div id="edit_answer2_display" style="white-space: pre-wrap"></div>
              </div>
            </div>
            <div id="edit_answer_set_2" class="row">
              <div class="form-group col-md-6 col-sm-12">
                <label for="edit_answer3">Answer 3</label>
                <textarea class="form-control tex2jax_ignore" id="edit_answer3"></textarea>
                <div id="edit_answer3_display" style="white-space: pre-wrap"></div>
              </div>
              <div class="form-group col-md-6 col-sm-12">
                <label for="edit_answer4">Answer 4</label>
                <textarea class="form-control tex2jax_ignore" id="edit_answer4"></textarea>
                <div id="edit_answer4_display" style="white-space: pre-wrap"></div>
              </div>
            </div>
            <!-- answer section; if select more than 1, this will automatically becomes an is_multiple_choice question. Will throw error if none/all are selected  -->
            <div id="edit_correct_answer" class="form-group">
              <label class="mr-3">Correct: </label>
              {% for _ in range(4) %}
                <input type="checkbox" id="edit_correct_answer_{{loop.index}}" class="mx-2">{{loop.index}}</input>
              {% endfor %}
              <br>
              <label id="edit_correct_answer_invalid" class="text-danger fst-italic"></label>
            </div>
            <!-- special answer block span entire row, used for is_single_equation to highlight it not needing any choices -->
            <div id="edit_answer_single" class="form-group">
              <label for="edit_answer_single_equation">Single Equation Answer</label>
              <textarea class="form-control tex2jax_ignore" id="edit_answer_single_equation"></textarea>
              <div id="edit_answer_single_equation_display" style="white-space: pre-wrap"></div>
            </div>
            <!-- special-only field "variable_limitation" -->
            <div id="edit_limitation" class="form-group">
              <label for="edit_variable_limitation" id="edit_variable_limitation_lbl">Variable Limitations</label>
              <textarea class="form-control tex2jax_ignore" id="edit_variable_limitation"></textarea>
            </div>
            <div class="form-group">
              <label for="edit_hardness">Hardness: <span id="edit_hardness_display">N/A</span></label>
              <input type="range" class="form-range" id="edit_hardness" min="0" max="10"></input>
          </div>
        </form>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
        <button type="button" id="edit_submit_button" class="btn btn-primary" onclick="_submit_edit_modal()">Update</button>
      </div>
    </div>
  </div>
