<div class="container-fluid" id="disposition"> 
	<div class="row align-middle col-sm-12 m-1">Composition (score &amp; count):</div>
	<div class="row">
	{% for i in ["undefined"] + (range(1, 11) | list) %}
		<div id="score_section_{{i}}" class="col-sm-4 col-2 p-1">
			<div class="border hardness_{{i}}_border p-1 input-group">
				<span class="p-2">Hardness {{i}}:</span>
				<input type="number" class="form-control" id="group_{{i}}" maxlength="2" /> 
				<div class="input-group-append">
					<div class="input-group-text"> 
						<span>question /</span> <b><span id="group_count_{{i}}">0</span></b> <span>&nbsp;total with&nbsp;</span>
					</div>
				</div>
				<input type="number" class="form-control" id="score_{{i}}" maxlength="5" />
				<div class="input-group-append">
					<div class="input-group-text"> 
						 <span>PPC</span>
					</div>
				</div>
			</div>
		</div>
	{% endfor %}
	</div>
	<div class="row align-middle col-sm-12 m-1"><i>*PPC: Point per Correct answer in category</i></div>
</div>
<div class="container-fluid" id="setting">
	<div class="row align-middle col-sm-12 m-1">Setting:</div>
	<div class="row my-2">
		<div class="col-sm-12 col-md-6 input-group">
			<div class="input-group-prepend">
				<span class="input-group-text" for="session_name">Exam name</span>
			</div>
			<input type="text" class="form-control" id="session_name"></input>
		</div>
		<div class="col-sm-12 col-md-6 input-group">
			<div class="input-group-prepend">
				<span class="input-group-text" for="id_name">Identification field</span>
			</div>
			<input type="text" class="form-control" id="id_name" value="Student Name" disabled></input>
		</div>
	</div>
	<div class="row my-2">
		<div class="col-sm-12 col-md-6 input-group">
			<div class="input-group-prepend">
				<span class="input-group-text" for="session_duration">Exam length</span>
			</div>
			<input type="number" class="form-control" id="session_duration"></input>
			<div class="input-group-append">
				<span class="input-group-text" for="session_duration">min</span>
			</div>
		</div>
		<div class="col-sm-12 col-md-6 input-group">
			<div class="input-group-prepend">
				<span class="input-group-text" for="grace_duration">Grace
					<input type="checkbox" id="allow_grace" for="grace_duration" class="mx-1"></input>
				</span>
			</div>
			<input type="number" class="form-control" id="grace_duration"></input>
			<div class="input-group-append">
				<span class="input-group-text" for="grace_duration">min</span>
			</div>
		</div>
	</div>
	<div class="row my-2">
		<div class="col-sm-12 col-md-6 input-group date" id="start_date_picker">
			<div class="input-group-prepend">
				<span class="input-group-text" for="start_exam_time"> Exam start </span>
			</div>
			<input type="time" class="form-control" id="start_exam_time">
			<input data-provide="datepicker" class="form-control" id="start_exam_date"  data-date-format="dd/mm/yyyy">
			<div class="input-group-addon" />
				<span class="glyphicon glyphicon-calendar" />
			</div>
		</div>
		<div class="col-sm-12 col-md-6 input-group date" id="end_date_picker">
			<div class="input-group-prepend">
				<span class="input-group-text" for="end_exam_date"> Exam end </span>
			</div>
			<!-- <input type="text" class="form-control" id="end_date_text"/> -->
			<input type="time" class="form-control" id="end_exam_time">
			<input data-provide="datepicker" class="form-control" id="end_exam_date"  data-date-format="dd/mm/yyyy">
			<div class="input-group-addon" />
				<span class="glyphicon glyphicon-calendar" />
			</div>
		</div>
	</div>
	<div class="row my-2">
		<div class="col-sm-12 col-md-3 pl-2">
			<div class="form-check">
				<input class="form-check-input" type="checkbox" value="" id="allow_result">
				<label class="form-check-label" for="allow_result">Show correct answers when exam finishes</label>
			</div>
		</div>
		<div class="col-sm-12 col-md-3 pl-2">
			<div class="form-check">
			<input class="form-check-input" type="checkbox" value="" id="allow_score">
			<label class="form-check-label" for="allow_score">Show score when exam finishes</label>
			</div>
		</div>
		<div class="col-sm-12 col-md-3 pl-2">
			<div class="form-check">
			<input class="form-check-input" type="checkbox" value="" id="show_score">
			<label class="form-check-label" for="show_score">Show each question's score during exam</label>
			</div>
		</div>
		<div class="col-sm-12 col-md-3 pl-2">
			<div class="form-check">
			<input class="form-check-input" type="checkbox" value="" id="partial_mq">
			<label class="form-check-label" for="partial_mq">Points for incomplete answer on multiple-choice</label>
			</div>
		</div>
	</div>
	<div class="row my-2">
		<div class="input-group col-sm-12 col-md-6 pl-2 dropup">
			<div class="input-group-prepend">
				<button class="btn btn-outline-secondary dropdown-toggle" id="toggle_student_list" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" disabled>View Student List</button>
				<div class="dropdown-menu" id="student_list"">
				</div>
			</div>
			<div class="custom-file">
				<input type="file" class="custom_file_input" id="load_student_list" onchange="update_student_list(event)" accept=".csv,.xlsx"></input>
				<label class="custom-file-label" for="load_student_list" id="load_student_list_result"></label>
			</div>
		</div>
	</div>
</div>
