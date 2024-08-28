%define	_version		%_version_%
%define _prefix_dir		%_prefix_dir_%

Name:		test_lsb_app
Version:	%{_version}
Release:	1
Prefix:		%{_prefix_dir}
Summary:	test LITP package for a simple LSB service
Group:		Applications/System
License:	EEI
Buildroot:	/
BuildArch: noarch

%description

%post
/sbin/chkconfig --add test_lsb_app

%preun
if [ $1 = 0 ]; then
  /sbin/chkconfig --del test_lsb_app
fi

%files
%attr(754, root, root) /opt/ericsson/test_lsb_app
%attr(754, root, root) /opt/ericsson/test_lsb_app/bin/test_lsb_app
%attr(754, root, root) /etc/init.d/test_lsb_app


