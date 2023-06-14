<nav class="navbar navbar-expand-md bg-dark navbar-dark">
	<a class="navbar-brand" href="/">Navbar</a>
	<button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#collapsibleNavbar">
		<span class="navbar-toggler-icon"></span>
	</button>
	<div class="collapse navbar-collapse" id="collapsibleNavbar">
		<ul class="navbar-nav">
			{% if True or admin_right is defined %}
			<li class="nav-item" id="manage_session_link_wrapper">
				<a class="nav-link" id="manage_session_link" href="session_manager">Manage Sessions</a>
			</li>
			<li class="nav-item">
				<a class="nav-link" href="data">Data</a>
			</li>
			{% endif %}
			<li class="nav-item">
				<a class="nav-link" href="convert">Converter Tool</a>
			</li>
		</ul>
	</div>
</nav> 
