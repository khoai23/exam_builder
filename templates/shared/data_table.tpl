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
	<div class="dropleft">
		<button class="btn btn-secondary dropdown-toggle" type="button" id="hardness_dropdown" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
			Hardness
		</button>
		<div class="dropdown-menu" aria-labelledby="hardness_dropdown" id="hardness_dropdown_menu" style="z-index: 10; max-height: 350px; overflow: auto;">
			<button class="btn btn-link dropdown-item" onclick=select_hardness(0)>All</button>
			<button class="btn btn-link dropdown-item" onclick=select_hardness(-1)>Unrated</button>
			<button class="btn btn-link dropdown-item" onclick=select_hardness(-2)>Rated</button>
			{% for i in range(1, 11) %}
				<button class="btn btn-link dropdown-item" onclick=select_hardness({{i}})>{{i}}</button>
			{% endfor %}
		</div>
	</div>
	<span class="h3 m-2">Hardness:</span>
	<div class="dropleft">
		<button class="btn btn-secondary dropdown-toggle" type="button" id="sizeperpage_dropdown" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
			N/A
		</button>
		<div class="dropdown-menu" aria-labelledby="sizeperpage_dropdown" id="sizeperpage_dropdown_menu" style="z-index: 10; max-height: 350px; overflow: auto;">
			<button class="btn btn-link dropdown-item" onclick=select_sizeperpage(1000)>1000</button>
			<button class="btn btn-link dropdown-item" onclick=select_sizeperpage(500)>500</button>
			<button class="btn btn-link dropdown-item" onclick=select_sizeperpage(200)>200</button>
			<button class="btn btn-link dropdown-item" onclick=select_sizeperpage(100)>100</button>
		</div>
	</div>
	<span class="h3 m-2">Row per Page:</span>
</div>
<div class="table-responsive card-body w-100 d-md-table">
	<table class="table table-hover table-bordered" id="question_table" style="display: block; max-height: 700px; overflow: auto;">
		<thead class="thead-light">
			<tr>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">ID</th>
				<th class="align-top" style="position: sticky; top: 0; z-index: 5;">Hardness</th>
				<th colspan='2' class="align-top" style="position: sticky; top: 0; z-index: 5;">Question</th>
				<th class="align-top d-none d-lg-table-cell d-xl-table-cell" style="position: sticky; top: 0; z-index: 5;">Answer 1</th>
				<th class="align-top d-none d-lg-table-cell d-xl-table-cell" style="position: sticky; top: 0; z-index: 5;">Answer 2</th>
				<th class="align-top d-none d-lg-table-cell d-xl-table-cell" style="position: sticky; top: 0; z-index: 5;">Answer 3</th>
				<th class="align-top d-none d-lg-table-cell d-xl-table-cell" style="position: sticky; top: 0; z-index: 5;">Answer 4</th>
				<th class="align-top d-none d-lg-table-cell d-xl-table-cell" style="position: sticky; top: 0; z-index: 5;">Correct Answer</th>
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
			<!-- Will not has jinja autopopulated content anymore to avoid confusion. -->
		</tbody>
	</table>
	<div class="container-fluid d-flex p-1">
		<div id="legend" {% if not display_legend %} style="display: none;" {% endif %}>
			<div class="d-flex">
				<span class="m-1"><b>Correct Answer:</b></span>
				<div class="m-1 bg-success border" style="width: 25px; height: 25px;"></div>
				<span class="m-1">Single Choice</span>
				<div class="m-1 bg-info border" style="width: 25px; height: 25px;"></div>
				<span class="m-1">Multiple Choice</span>
				<span class="m-1 pl-3"><b>Duplicate:</b></span>
				<div class="m-1 bg-warning border" style="width: 25px; height: 25px;"></div>
				<span class="m-1">Older</span>
				<div class="m-1 bg-danger border" style="width: 25px; height: 25px;"></div>
				<span class="m-1">Newer</span>
			</div>
		</div>
		<div class="ml-auto" id="table_button_bar">
			<button class="btn btn-primary ml-auto m-1" id="table_button_first">1</button>
			<span class="p-1" id="elipse_start">...</span>
			<button class="btn btn-outline-primary m-1" id="table_button_previous">2</button>
			<button class="btn btn-outline-primary m-1" id="table_button_current">3</button>
			<button class="btn btn-outline-primary m-1" id="table_button_next">4</button>
			<span class="p-1" id="elipse_end">...</span>
			<button class="btn btn-outline-primary m-1" id="table_button_last">5</button>
		</div>
	</div>
</div>
