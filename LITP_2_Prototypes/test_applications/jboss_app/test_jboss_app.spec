%define	_version		%_version_%
%define _prefix_dir		%_prefix_dir_%

Name:		test_jboss_app
Version:	%{_version}
Release:	1
Prefix:		%{_prefix_dir}
Summary:	test LITP package for a simple JBoss application
Group:		Applications/System
License:	EEI
Buildroot:	/

%description

%postun
/bin/rm -rf /opt/ericsson/test_jboss_app

%files

/opt/ericsson/test_jboss_app/lib/JBossHelloWorld_war.war
