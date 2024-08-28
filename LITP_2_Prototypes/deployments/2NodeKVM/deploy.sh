#!/bin/bash

AWK=/bin/awk
BASENAME=/bin/basename
CAT=/bin/cat
CP=/bin/cp
CREATEREPO=/usr/bin/createrepo
DIRNAME=/usr/bin/dirname
ECHO=/bin/echo
EXPECT=/usr/bin/expect
GETOPT=/usr/bin/getopt
GREP=/bin/grep
LITP=/usr/bin/litp
LS=/bin/ls
MOUNT=/bin/mount
MOUNTPOINT=/bin/mountpoint
MKDIR=/bin/mkdir
MV=/bin/mv
RM=/bin/rm
SED=/bin/sed
SSH=/usr/bin/ssh
SSH_COPY_ID=/usr/bin/ssh-copy-id
SSH_KEYGEN=/usr/bin/ssh-keygen
TAIL=/usr/bin/tail
TEE=/usr/bin/tee
TR=/usr/bin/tr
RPM=/bin/rpm
UMOUNT=/bin/umount
YUM=/usr/bin/yum

_dir_=`${DIRNAME} $0`
THIS_SCRIPTHOME=`cd ${_dir_}/ 2>/dev/null && pwd || ${ECHO} ${_dir_}`
unset _dir_

if [ ! ${SCRIPTHOME} ] ; then
  SCRIPTHOME=${THIS_SCRIPTHOME}/../../
fi


PWSCRIPT="${SCRIPTHOME}/bin/plan_watcher.bsh"
if [ ! -f ${PWSCRIPT} ] ; then
  ${ECHO} "Cant find file ${PWSCRIPT}"
  exit 3
fi

LOGFILE="$0.log"
${ECHO} > ${LOGFILE}

log()
{
  ${ECHO} "$*" | ${TEE} -a ${LOGFILE}
}

litp()
{
	log "litp $*"
	${LITP} $* 2>&1 | ${TEE} -a ${LOGFILE}
	if [ ${PIPESTATUS[0]} -ne 0 ] ; then
		exit 1
	fi
}

path_exists()
{
  local _path_=$1
  ${LITP} show -p ${_path_} > /dev/null 2>&1
  return $?
}

create_2n_kvm()
{
  local _sitefile_=$1
  get_site_value ${_sitefile_} "node_list" "_node_list_"

  litp create -p /software/profiles/rhel_6_4 -t os-profile -o name='sample-profile' version='rhel6' \
    path='/profiles/node-iso/' arch='x86_64' breed='redhat' kopts_post='console=ttyS0,115200'
  litp create -p /infrastructure/system_providers/libvirt1 -t libvirt-provider -o name='libvirt1'


  for _node_ in ${_node_list_} ; do
    litp create -p /infrastructure/system_providers/libvirt1/systems/${_node_} -t libvirt-system -o \
      system_name="${_node_}" ram="2048M"
    litp create -p /infrastructure/system_providers/libvirt1/systems/${_node_}/disks/disk0 -t disk \
      -o name=sda size=28G bootable=true uuid="SATA_QEMU_HARDDISK_QM00001"


    get_site_value ${_sitefile_} "${_node_}_mac" "_node_mac_"

    litp create -p /infrastructure/system_providers/libvirt1/systems/${_node_}/network_interfaces/nic0 -t nic \
      -o interface_name='eth0' macaddress=${_node_mac_}

  done

  get_site_value ${_sitefile_} "ms_internal_mac" "_ms_int_mac_"
  get_site_value ${_sitefile_} "ms_internal_device" "_ms_int_dev_"
  get_site_value ${_sitefile_} "ms_internal_ip" "_ms_int_ip_"
  get_site_value ${_sitefile_} "ms_external_mac" "_ms_ext_mac_"
  get_site_value ${_sitefile_} "ms_external_device" "_ms_ext_dev_"
  get_site_value ${_sitefile_} "ms_external_ip" "_ms_ext_ip_"
  get_site_value ${_sitefile_} "ms_external_subnet" "_ms_ext_snet_"
  get_site_value ${_sitefile_} "ms_external_gw" "_ms_ext_gw_"

  litp create -p /infrastructure/systems/ms_system -t system -o system_name='MS'
  litp create -p /infrastructure/systems/ms_system/network_interfaces/nic0 -t nic -o interface_name=${_ms_int_dev_} macaddress=${_ms_int_mac_}
  litp create -p /infrastructure/systems/ms_system/network_interfaces/nic1 -t nic -o interface_name=${_ms_ext_dev_} macaddress=${_ms_ext_mac_}

  get_site_value ${_sitefile_} "nodes_start" "_node_rng_start_"
  get_site_value ${_sitefile_} "nodes_end" "_node_rng_end_"
  get_site_value ${_sitefile_} "nodes_subnet" "_node_rng_snet_"


  litp create -p /infrastructure/networking/ip_ranges/range1 -t ip-range -o network_name='nodes' \
    start=${_node_rng_start_} end=${_node_rng_end_} subnet=${_node_rng_snet_} gateway=${_ms_int_ip_}
  litp create -p /infrastructure/networking/ip_ranges/range3 -t ip-range -o network_name='ms_external' \
    start=${_ms_ext_ip_} end=${_ms_ext_ip_} subnet=${_ms_ext_snet_} gateway=${_ms_ext_gw_}


  litp create -p /infrastructure/networking/network_profiles/nodes -t network-profile -o name='node_profile' management_network='nodes'
  litp create -p /infrastructure/networking/network_profiles/nodes/networks/network0 -t network -o interface='if0' network_name='nodes'
  litp create -p /infrastructure/networking/network_profiles/nodes/interfaces/if0 -t interface -o interface_basename='eth0'

  litp create -p /infrastructure/networking/network_profiles/libvirt_provider -t network-profile -o name='libvirt_provider' management_network='nodes'
  litp create -p /infrastructure/networking/network_profiles/libvirt_provider/networks/network0 -t network -o network_name='nodes' bridge='br0'
  litp create -p /infrastructure/networking/network_profiles/libvirt_provider/interfaces/if0 -t interface -o interface_basename=${_ms_int_dev_}
  litp create -p /infrastructure/networking/network_profiles/libvirt_provider/bridges/br0 -t bridge -o bridge_name='br0' interfaces='if0' stp='on' forwarding_delay='0'
  litp create -p /infrastructure/networking/network_profiles/libvirt_provider/networks/network1 -t network -o network_name='ms_external' interface='if1' default_gateway='true'
  litp create -p /infrastructure/networking/network_profiles/libvirt_provider/interfaces/if1 -t interface -o interface_basename=${_ms_ext_dev_}

  litp create -p /infrastructure/storage/storage_profiles/blade_local_storage -t storage-profile -o storage_profile_name=blade_local_storage
  litp create -p /infrastructure/storage/storage_profiles/blade_local_storage/volume_groups/vg_root -t volume-group -o volume_group_name="vg_root"
  litp create -p /infrastructure/storage/storage_profiles/blade_local_storage/volume_groups/vg_root/file_systems/root -t file-system -o type=ext4 mount_point=/ size=16G
  litp create -p /infrastructure/storage/storage_profiles/blade_local_storage/volume_groups/vg_root/file_systems/swap -t file-system -o type=swap mount_point=swap size=2G
  litp create -p /infrastructure/storage/storage_profiles/blade_local_storage/volume_groups/vg_root/physical_devices/internal -t physical-device -o device_name=sda name=disk0

  litp link -p /ms/ipaddresses/external_ip -t ip-range -o network_name='ms_external' address=${_ms_ext_ip_}
  litp link -p /ms/ipaddresses/internal_ip -t ip-range -o network_name='nodes' address=${_ms_int_ip_}

  litp create -p /ms/services/cobbler -t cobbler-service -o boot_network='nodes'
  litp link -p /ms/network_profile -t network-profile -o name='libvirt_provider'
  litp link -p /ms/libvirt -t libvirt-provider -o name='libvirt1'
  litp link -p /ms/system -t system -o system_name='MS'

  litp create -p /deployments/single_blade -t deployment
  litp create -p /deployments/single_blade/clusters/cluster1 -t cluster
  for _node_ in ${_node_list_} ; do
    get_site_value ${_sitefile_} "${_node_}_hostname" "_node_hostname_"
    get_site_value ${_sitefile_} "${_node_}_ip" "_node_ip_"

    litp create -p /deployments/single_blade/clusters/cluster1/nodes/${_node_} -t node -o \
      hostname=${_node_hostname_} domain='local'
    litp link -p /deployments/single_blade/clusters/cluster1/nodes/${_node_}/system -t libvirt-system \
      -o system_name=${_node_}
    litp link -p /deployments/single_blade/clusters/cluster1/nodes/${_node_}/os -t os-profile \
      -o name='sample-profile' version='6.4'
    litp link -p /deployments/single_blade/clusters/cluster1/nodes/${_node_}/ipaddresses/ip1 -t ip-range \
      -o network_name='nodes' address=${_node_ip_}

    litp link -p /deployments/single_blade/clusters/cluster1/nodes/${_node_}/network_profile -t network-profile \
      -o name='node_profile'
    litp link -p /deployments/single_blade/clusters/cluster1/nodes/${_node_}/storage_profile -t storage-profile \
      -o storage_profile_name='blade_local_storage'
  done
}

create_and_run_plan()
{
  litp create_plan
  litp show_plan
  litp run_plan
}

dos2unix()
{
  local _file_=$1
  if [ ! -f ${_file_} ] ; then
    log "dos2unix: input file ${_file_} not found"
    exit 3
  fi
  ${CAT} ${_file_} | ${TR} -d '\015' >${_file_}.$$
  if [ $? -ne 0 ] ; then
    log "dos2unix failed"
    ${RM} -rf ${_file_}.$$
    exit 3
  fi
  ${MV} ${_file_}.$$ ${_file_} >> ${LOGFILE}
  if [ $? -ne 0 ] ; then
    log "dos2unix: failed to move temp file to original"
    exit 3
  fi
}

get_site_value()
{
  local _siteconf_=$1
  local _key_=$2
  local _returnvar_="$3"
  local _value_
  _value_=`${GREP} -E "^${_key_}=.*" ${_siteconf_}`
  if [ $? -ne 0 ] ; then
    log "Key '${_key_}' not found in file ${_siteconf_}"
    exit 3
  fi
  _value_=`${ECHO} ${_value_} | ${AWK} -F= '{print $2}'`
  _value_=`eval ${ECHO} -e "${_value_}"`
  eval ${_returnvar_}='${_value_}'
}

wait_for_plan_completion()
{
  if [ ! -f ${PWSCRIPT} ] ; then
    log "Cant find file ${PWSCRIPT}"
    exit 1
  fi
  litp show_plan >> ${LOGFILE}
  ${BASH} ${PWSCRIPT}
  litp show_plan >> ${LOGFILE}
}

create_rhel_media_ms()
{
  local _conffile_=$1
  local _name_=$2
  local _repofile_="/etc/yum.repos.d/${_name_}.repo"
  local _rhelrepo_="/var/www/html/${_name_}"
  ${ECHO} "[${_name_}]
name = ${_name_}
baseurl = file://${_rhelrepo_}
enabled = 1
gpgcheck = 0 " > ${_repofile_}
  get_site_value ${_conffile_} "jump.media.local" "_jump_media_local_"
  ${MOUNTPOINT} -q ${_jump_media_local_} >> ${LOGFILE}
  if [ $? -ne 0 ] ; then
    get_site_value ${_conffile_} "jump.media.remote" "_jump_media_remote_"
    get_site_value ${_conffile_} "jump.media.server" "_jump_media_server_"
    log "Mounting jump media ${_jump_media_server_}:${_jump_media_remote_} to ${_jump_media_local_}"
		if [ ! -d ${_jump_media_local_} ] ; then
			${MKDIR} -p ${_jump_media_local_}
		fi
    ${MOUNT} -o nolock ${_jump_media_server_}:${_jump_media_remote_} ${_jump_media_local_} >> ${LOGFILE} 2>&1
  fi
  ${MKDIR} -p ${_rhelrepo_}
  log "Creating local RHEL repo from ${_jump_media_local_}"
  log "Copying new/updated packages from ${_jump_media_local_}/Packages/ to ${_rhelrepo_}"
  ${CP} -n ${_jump_media_local_}/Packages/*.rpm ${_rhelrepo_}
  ${UMOUNT} ${_jump_media_local_} >> ${LOGFILE} 2>&1
  log "Creating repo ${_name_}"
  ${CREATEREPO} --workers 5 ${_rhelrepo_} >> ${LOGFILE} 2>&1
  ${YUM} clean all >> ${LOGFILE} 2>&1
  ${YUM} repolist 2>&1 | ${TEE} -a ${LOGFILE}
}

create_rhel_yum_repos()
{
  local _conffile_=$1
  get_site_value ${_conffile_} "rhel.repo.name" "_ms_repo_"
  create_rhel_media_ms ${_conffile_} ${_ms_repo_}
}

create_app_yum_repos()
{
  local _conffile_=$1
  get_site_value ${_conffile_} "repo.base" "_repobase_"
  get_site_value ${_conffile_} "appsw.repo.name" "_name_"
  if [ ! -d ${_repobase_}/${_name_} ] ; then
    log "No source repo found at ${_repobase_}/${_name_}"
    exit 3
  fi
  ${CP} -rv ${_repobase_}/${_name_}/ /var/www/html/ 2>&1 | ${TEE} -a ${LOGFILE}
  ${CREATEREPO} /var/www/html/${_name_} >> ${LOGFILE} 2>&1
}

link_managed_node_repos()
{
  local _conffile_=$1
  local _sitefile_=$2
  get_site_value ${_conffile_} "appsw.repo.name" "_appsw_repo_name_"
  get_site_value ${_conffile_} "rhel.repo.name" "_rhel_repo_name_"
  get_site_value ${_sitefile_} "ms_hostname" "_mshostname_"
  get_site_value ${_sitefile_} "node_list" "_node_list_"
  for _repo_ in ${_appsw_repo_name_} ${_rhel_repo_name_} ; do
    litp create -p /software/items/${_repo_} -t repository -o name=${_repo_} -o url="http://${_mshostname_}/${_repo_}"
    for _node_ in ${_node_list_} ; do
      litp link -p /deployments/single_blade/clusters/cluster1/nodes/${_node_}/items/${_repo_} -t repository -o name=${_repo_}
    done
  done
}

install_packages()
{
  local _conffile_=$1
  local _sitefile_=$2
  get_site_value ${_conffile_} "appsw.repo.name" "_name_"
  get_site_value ${_sitefile_} "node_list" "_node_list_"
  local _location_=${SCRIPTHOME}/etc/repos/${_name_}
  for _rpm_ in `${LS} ${_location_}/*.rpm` ; do
    local _pkgname_=`${RPM} -qp --queryformat "%{NAME}" ${_rpm_}`
    litp create -p /software/items/${_pkgname_} -t package -o name=${_pkgname_}
    for _node_ in ${_node_list_} ; do
      litp link -p /deployments/single_blade/clusters/cluster1/nodes/${_node_}/items/${_pkgname_} -t package -o name=${_pkgname_}
    done
  done

  get_site_value ${_conffile_} "jdk.package" "_jdk_"
  local _jdkname_
  _jdkname_=`${ECHO} "${_jdk_}" | ${SED} -e 's/[\.|-]/_/g'`
	litp create -p /software/items/${_jdkname_} -t package -o name="${_jdk_}"
	for _node_ in ${_node_list_} ; do
		litp link -p /deployments/single_blade/clusters/cluster1/nodes/${_node_}/items/${_jdkname_} \
		  -t package -o name="${_jdk_}"
	done
}

clean_plan()
{
  if path_exists "/plans/plan" ; then
    litp remove -p /plans/plan
  fi
}

usage()
{
  ${ECHO} "${0} -site <site_file>"
}

# Execute getopt
ARGS=`${GETOPT} -o "s:" -l "site:" -n "$0" -- "$@"`
#Bad arguments
if [ $? -ne 0 ] ; then
  usage
  exit 2
fi

# A little magic
eval set -- "$ARGS"
_SITE_CONF_=
while true ; do
  case "$1" in
    --site|-s)
      _SITE_CONF_=${2}
      shift 2
      ;;
    --)
      shift
      break;;
	esac
done

if [ ! ${_SITE_CONF_} ] ; then
  _SITE_CONF_=${THIS_SCRIPTHOME}/site.conf
  log "Defaulting site file to ${_SITE_CONF_}"
else
  log "Using site file ${_SITE_CONF_}"
fi

if [ ! -f ${_SITE_CONF_} ] ; then
  log "Site file ${_SITE_CONF_} not found!"
  exit 2
fi

INSTALLER_CONF=${SCRIPTHOME}/etc/installer.conf
if [ ! -f ${INSTALLER_CONF} ] ; then
  log "File ${INSTALLER_CONF} not found!"
  exit 3
fi
log "Using ${INSTALLER_CONF}"

dos2unix ${_SITE_CONF_}
dos2unix ${INSTALLER_CONF}

# Basic node install: OS,LVM,Network
clean_plan
create_2n_kvm ${_SITE_CONF_}

exit 0
create_and_run_plan
wait_for_plan_completion

# Create some repos on the MS and updated nodes with links to them
create_rhel_yum_repos ${INSTALLER_CONF}
create_app_yum_repos ${INSTALLER_CONF}
clean_plan
link_managed_node_repos ${INSTALLER_CONF} ${_SITE_CONF_}
create_and_run_plan
wait_for_plan_completion

# Install some packages (avaialble in repos created/linked above)
clean_plan
install_packages ${INSTALLER_CONF} ${_SITE_CONF_}
create_and_run_plan
wait_for_plan_completion

# Done.
clean_plan
log "Install complete."
