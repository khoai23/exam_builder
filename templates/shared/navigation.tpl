<nav class="navbar navbar-expand-md bg-dark navbar-dark">
	<a class="navbar-brand" href="/">8th Circle</a>
	<button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#collapsibleNavbar">
		<span class="navbar-toggler-icon"></span>
	</button>
	<div class="collapse navbar-collapse" id="collapsibleNavbar">
		<ul class="navbar-nav flex-row container-fluid">
			{% if current_user.is_authenticated %}
				{% if current_user.can_do("modify") %}
				<li class="nav-item">
					<a class="nav-link" href="edit">Modify</a>
				</li>
				<li class="nav-item">
					<a class="nav-link" href="convert">Converter Tool</a>
				</li>
				{% endif %}
				{% if current_user.can_do("create_exam") %}
				<li class="nav-item">
					<a class="nav-link" href="build">Build</a>
				</li>
				<li class="nav-item" id="manage_session_link_wrapper">
					<a class="nav-link" id="manage_session_link" href="session_manager">Manage Sessions</a>
				</li>
				{% endif %}
			{% endif %}
			<li class="nav-item">
				<a class="nav-link" href="play">Map Game</a>
			</li>
			{% if current_user.is_authenticated %}
			<li class="nav-item nav-link ml-auto">
				Hello, <b><u>{{current_user.name}}</u></b>
			</li>
			<li class="nav-item">
				<a class="nav-link" href="logout">
					<span class="bi-box-arrow-right"></span>
				</a>
			</li>
			{% endif %}
		</ul>
	</div>
</nav> 
