<div class="table-responsive card-body p-1">
	<table class="table table-hover table-bordered" id="question_table" style="display: block; max-height: 600px; overflow: auto;">
		<thead class="thead-light">
			<tr>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">ID</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Question</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Answer 1</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Answer 2</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Answer 3</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Answer 4</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Correct Answer</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Category &nbsp;
					<button id="filter_category_clear" class="m-0 p-0 btn btn-link" onclick="clear_category(event)" style="display: none;">
						(X)
					</button>
				</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Tag</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">
					<button class="btn btn-link p-0" onclick="toggle_all_tag(event)">Use</button>
				</th>
			</tr>    
		</thead>    
		<tbody>     
			{% for  q in questions %}
			<tr>    
				<td>{{q["id"]}}</td>
				<td>{{q["question"]}}</td>
				{% if "is_single_equation" in q or q["is_single_equation"] %}
					<td colspan='5'> {{ q["answer1"] }}</td>
				{% else %}
					{% for i in range(1, 5) %}
						{% if q["correct_id"] == i %} 
							<td class="table-success"> 
						{% elif q["correct_id"] is iterable and i in q["correct_id"] %} 
							<td class="table-info"> 
						{% else %}
							<td> 
						{% endif %} 
						{% if "|||" not in q["answer{}".format(i)] %}
							{{q["answer{}".format(i)]}}
						{% else %}
							<img src="{{q["answer{}".format(i)] | replace("|||", "")}}" class="img-thumbnail" style="max-width: 300px;"></img>
						{% endif %}
						</td>
					{% endfor %}
					<td>{{q["correct_id"]}}</td>
				{% endif %}
				<td class="category_cell">
					<button class="m-0 p-0 btn btn-link" onclick="select_category(event)">
						{{q.get("category", "N/A")}}
					</button>
				</td>
				<td>
					{% if "tag" in q %}
						{% for tag in q["tag"] %}
							<button class="m-0 p-0 btn btn-link tag_cell" onclick="toggle_select_tag(event)">{{tag}}</button>&nbsp;
						{% endfor %}
					{% else %} 
						-
					{% endif %}
				</td>
				<td class="custom-checkbox">
					<input type="checkbox" class="custom-control" id="use_question_{{q["id"]}}">
				</td>
			</tr>
			{% endfor %}
		</tbody>
	</table>
</div>
