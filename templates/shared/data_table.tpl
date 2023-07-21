<div class="container-fluid d-flex flex-row-reverse m-2">
	<div class="dropleft">
		<button class="btn btn-secondary dropdown-toggle" type="button" id="category_dropdown" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
			Category
		</button>
		<div class="dropdown-menu" aria-labelledby="category_dropdown" id="category_dropdown_menu" style="z-index: 10; max-height: 350px; overflow: auto;">
			<button class="btn btn-link dropdown-item" onclick=select_category(event)>All</button>
		</div>
	</div>
	<span class="h3 m-2">Category:</span>
</div>
<div class="table-responsive card-body p-1">
	<table class="table table-hover table-bordered" id="question_table" style="display: block; max-height: 700px; overflow: auto;">
		<thead class="thead-light">
			<tr>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">ID</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Question</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Answer 1</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Answer 2</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Answer 3</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Answer 4</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Correct Answer</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">
					<div class="dropdown">
						<button class="btn btn-secondary dropdown-toggle" type="button" id="tag_dropdown" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
							Tag
						</button>
						<div class="dropdown-menu" aria-labelledby="tag_dropdown" id="tag_dropdown_menu" style="z-index: 10; max-height: 350px; overflow: auto;">
						</div>
					</div>
				</th>
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
		<tfoot id="table_button_bar">
			<tr>
				<th colspan='10' class="align-bottom bg-white" style="position: sticky; bottom: 0; z-index: 5;">
					<div class="d-flex p-1">
						<div class="ml-auto">
							<button class="btn btn-primary ml-auto m-1" id="table_button_first">1</button>
							<span class="p-1" id="elipse_start">...</span>
							<button class="btn btn-outline-primary m-1" id="table_button_previous">2</button>
							<button class="btn btn-outline-primary m-1" id="table_button_current">3</button>
							<button class="btn btn-outline-primary m-1" id="table_button_next">4</button>
							<span class="p-1" id="elipse_end">...</span>
							<button class="btn btn-outline-primary m-1" id="table_button_last">5</button>
						</div>
					</div>
				</th>
			</tr>
		</tfoot>
	</table>
</div>
