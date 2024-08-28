%define	_version		1.0.8
%define _prefix_dir		/opt/ericsson/test_java_app

Name:		test_java_app
Version:	%{_version}
Release:	1
Prefix:		%{_prefix_dir}
Summary:	test LITP package for a simple LSB service
Group:		Applications/System
License:	EEI
Buildroot:	/
BuildArch: noarch

%description

#%post
#/sbin/chkconfig --add test_java_app

#%preun
#if [ $1 = 0 ]; then
#  /sbin/chkconfig --del test_java_app
#fi

%files
%attr(754, root, root) /opt/ericsson/test_java_app
%attr(754, root, root) /opt/ericsson/test_java_app/lib/test_java_app.jar
%attr(754, root, root) /etc/init.d/test_java_app


