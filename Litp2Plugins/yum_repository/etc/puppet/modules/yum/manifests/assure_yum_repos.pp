
define yum::assure_yum_repos ($name, $url = undef, $ensure) {
	if $ensure == 'present' {
		file { "yum_${name}":
			ensure  => 'file',
			path    => "/etc/yum.repos.d/${name}.repo",
			content => template('yum/yum.repo.erb'),
		}
	}
	if $ensure == 'absent' {
		file { "/etc/yum.repos.d/${name}.rep":
			ensure  => 'absent',
		}
	}
}
