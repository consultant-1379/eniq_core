#!/bin/bash

set -x

# COBBLER
for sysname in $(cobbler system list); do
	cobbler system remove --name "$sysname"
done

for distroname in $(cobbler distro list); do
	cobbler distro remove --name "$distroname"
done

# PUPPET
puppet cert clean node1
puppet cert clean node2
service puppet stop
rm -fr /opt/ericsson/nms/litp/etc/puppet/manifests/plugins/*
service puppet start

rm -f /root/.ssh/known_hosts

# MODEL
service litpd stop
rm -f /var/lib/litp/*
service litpd start

# LIBVIRT
for vmname in `virsh list --all | grep -i node |gawk '{print $2}'`; do
virsh destroy $vmname
virsh undefine $vmname
done
rm -fr /var/lib/libvirt/images/*
rm -rf /var/www/html/MN_APP_SW/
