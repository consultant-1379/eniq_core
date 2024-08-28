%define	_version		%_version_%
%define _prefix_dir		%_prefix_dir_%

Name:		litp_plugin_assure_yumrepo
Version:	%{_version}
Release:	1
Prefix:		%{_prefix_dir}
Summary:	Simple YUM repo management plugins for LITP 2
Group:		Applications/System
License:	EEI
Buildroot:	/
BuildArch: noarch

%description

%files
%attr(754, root, root) /opt/ericsson/nms/litp/etc/extensions/pkgmgmt_repo_extensions.conf
%attr(754, root, root) /opt/ericsson/nms/litp/etc/plugins/pkgmgmt_repo_plugin.conf
%attr(754, root, root) /opt/ericsson/nms/litp/lib/assure/__init__.py
%attr(754, root, root) /opt/ericsson/nms/litp/lib/assure/extensions/__init__.py
%attr(754, root, root) /opt/ericsson/nms/litp/lib/assure/extensions/pkgmgmt_repo_extensions.py
%attr(754, root, root) /opt/ericsson/nms/litp/lib/assure/plugin/__init__.py
%attr(754, root, root) /opt/ericsson/nms/litp/lib/assure/plugin/pkgmgmt_repo_plugin.py
%attr(754, root, root) /opt/ericsson/nms/litp/etc/puppet/modules/yum/manifests/assure_yum_repos.pp


