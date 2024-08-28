from datetime import datetime
from genericpath import exists
from optparse import OptionParser
from os.path import expandvars, join
import sys
from time import sleep, clock
import traceback
from h_litp.litp_crypt import litp_crypt
from h_litp.litp_rest_client import litp_rest_client, LitpException
from h_util.h_utils import Formatter, decode, ENC_KEY
from h_util.ini import ini_reader


class DeployerException(Exception):
    pass


class deployer():
    INST_UPG_PLAN_NAME = 'plan'
    HWTYPE_LIBVIRT = 'libvirt'
    HWTYPE_REAL = 'real'
    HWTYPE_CLOUD = 'cloud'

    def __init__(self, deployment_id, site_description, hw_type,
                 litpd_host='localhost',
                 litpd_port=litp_rest_client.DEFAULT_LITPD_PORT,
                 debug=False):
        self.litpd_host = litpd_host
        self.litpd_port = litpd_port
        self.hw_type = hw_type
        self.deployment_id = deployment_id
        self.DEBUG = debug
        if litpd_host != 'localhost':
            self.REMOTE_EXECUTION = True
        self.litp = litp_rest_client(litpd_host=self.litpd_host,
                                     litpd_port=self.litpd_port,
                                     debug=self.DEBUG)
        self.CONF_DIR = expandvars('${CONF_DIR}')
        if not exists(site_description):
            _site_description = join(self.CONF_DIR, site_description)
            if not exists(_site_description):
                raise IOError(
                    'Cant find a file called {0}'.format(site_description))
            else:
                site_description = _site_description
        self.siteini = ini_reader(site_description)
        self.storageini = ini_reader(
            join(self.CONF_DIR, 'storage_profiles.ini'))
        self.LMS_SYSTEM_NAME = 'ms_system_ebs'

    def enable_litp_debug(self):
        self.litp.set_debug('override')

    def reset_litp_debug(self):
        self.litp.set_debug('normal')

    def get_cluster_nodes(self, cluster_name):
        return self.siteini.get_option(cluster_name, 'nodes', seperator=',')

    def define_os_profile(self, profile_ini_name):
        data = self.siteini.get_section(profile_ini_name)
        self.litp.create('/software/profiles', object_id=data['name'],
                         object_type='os-profile', properties=data)

    def define_node_systems(self):
        if self.hw_type == self.HWTYPE_LIBVIRT:
            self._define_libvirt_node_systems()
        elif self.hw_type == self.HWTYPE_REAL:
            self._define_real_node_systems()
        else:
            raise DeployerException(1,
                                    'Unsupported hardware type \'{0}\''.format(
                                        self.hw_type))

    def _define_libvirt_node_systems(self):
        deployment_name = self.siteini.get_option(self.deployment_id,
                                                  'deployment_name')
        system_providers = '/infrastructure/system_providers'
        libvirt = self.litp.create(system_providers,
                                   object_type='libvirt-provider',
                                   object_id=deployment_name,
                                   properties={'name': deployment_name})
        clusters = self.siteini.get_option(self.deployment_id, 'clusters',
                                           seperator=',')
        for cluster in clusters:
            for node in self.get_cluster_nodes(cluster):
                systems = '{0}/systems'.format(libvirt)
                properties = {'system_name': node, 'ram': '2048M'}
                node_path = self.litp.create(systems, object_id=node,
                                             object_type='libvirt-system',
                                             properties=properties)
                properties = {'name': 'sda', 'size': '28G', 'bootable': 'true',
                              'uuid': 'SATA_QEMU_HARDDISK_QM00001'}
                disks_path = '{0}/disks'.format(node_path)
                self.litp.create(disks_path, object_id='disk0',
                                 object_type='disk',
                                 properties=properties)
                nic_path = '{0}/network_interfaces'.format(node_path)
                eth0_mac = self.siteini.get_option(node, 'eth0_mac')
                properties = {'interface_name': 'eth0', 'macaddress': eth0_mac}
                self.litp.create(nic_path, object_id='nic0',
                                 object_type='nic',
                                 properties=properties)

    def _define_real_node_systems(self):

        clusters = self.siteini.get_option(self.deployment_id, 'clusters',
                                           seperator=',')
        for cluster in clusters:
            for node in self.get_cluster_nodes(cluster):
                bserial = self.siteini.get_option(node, 'enclosure_serial')
                eth0_mac = self.siteini.get_option(node, 'eth0_mac')
                system_path = self.litp.create('/infrastructure/systems',
                                               object_id=bserial,
                                               object_type='blade',
                                               properties={
                                                   'system_name': node})
                self.litp.create('{0}/network_interfaces'.format(system_path),
                                 object_type='nic', object_id='eth0',
                                 properties={
                                     'interface_name': 'eth0',
                                     'macaddress': eth0_mac})
                ilo_address = self.siteini.get_option(node, 'ilo_address')
                ilo_username = self.siteini.get_option(node, 'ilo_username')
                ilo_password = decode(ENC_KEY,
                                      self.siteini.get_option(node,
                                                              'ilo_password'))
                lms_password = decode(ENC_KEY,
                                      self.siteini.get_option('LMS',
                                                              'root_password'))
                if self.hw_type == self.HWTYPE_REAL:
                    bcp_service = 'bcp-key-{0}'.format(node)
                    keygen = litp_crypt(self.DEBUG)
                    lms_details = None
                    if self.REMOTE_EXECUTION:
                        lmsaddr = self.siteini.get_option('LMS',
                                                          'eth0_ipv4_address')
                        lms_details = {
                            'host': lmsaddr,
                            'username': 'root',
                            'password': lms_password
                        }
                    keygen.set(bcp_service, ilo_username, ilo_password,
                               lms_details)
                    self.litp.create(system_path,
                                     object_type='bmc', object_id='bmc',
                                     properties={
                                         'username': ilo_username,
                                         'ipaddress': ilo_address,
                                         'password_key': bcp_service})

                uuid_sda = self.siteini.get_option(node, 'sda_uuid')
                sda_size = self.siteini.get_option(node, 'sda_size')
                self.litp.create('{0}/disks'.format(system_path),
                                 object_type='disk', object_id='disk',
                                 properties={
                                     'name': 'hd0',
                                     'bootable': 'true',
                                     'size': sda_size,
                                     'uuid': uuid_sda})

    def define_ms_system(self):
        if self.hw_type == self.HWTYPE_LIBVIRT:
            self._define_ms_libvirt_system()
        elif self.hw_type == self.HWTYPE_REAL:
            self._define_ms_real_system()
        elif self.hw_type == self.HWTYPE_CLOUD:
            self._define_ms_cloud_system()
        else:
            raise DeployerException(1,
                                    'Unsupported hardware type \'{0}\''.format(
                                        self.hw_type))

    def _define_ms_real_system(self):
        self.__define_ms_system('blade')

    def _define_ms_cloud_system(self):
        self.__define_ms_system('system')

    def __define_ms_system(self, hy_type):
        bserial = self.siteini.get_option('LMS', 'enclosure_serial')
        eth0_mac = self.siteini.get_option('LMS', 'eth0_mac')
        system_path = self.litp. \
            create('/infrastructure/systems',
                   object_id=bserial,
                   object_type=hy_type,
                   properties={
                       'system_name': self.LMS_SYSTEM_NAME})
        self.litp.create('{0}/network_interfaces'.format(system_path),
                         object_id='eth0', object_type='nic',
                         properties={'interface_name': 'eth0',
                                     'macaddress': eth0_mac})

    def _define_ms_libvirt_system(self):
        systems = '/infrastructure/systems'
        ms_system = self.litp.create(systems, object_type='system',
                                     object_id=self.LMS_SYSTEM_NAME,
                                     properties={
                                         'system_name': self.LMS_SYSTEM_NAME})
        network_interfaces = '{0}/network_interfaces'.format(ms_system)
        for index in range(0, 2, 1):
            mac_key = 'eth{0}_mac'.format(index)
            mac = self.siteini.get_option('LMS', mac_key)
            nic_id = 'nic{0}'.format(index)
            iface_name = 'eth{0}'.format(index)
            self.litp.create(network_interfaces, object_id=nic_id,
                             object_type='nic',
                             properties={'interface_name': iface_name,
                                         'macaddress': mac})

    def define_node_volume_groups(self, vol_group_name, profile_path):
        volume_groups = '{0}/volume_groups'.format(profile_path)
        volgrp_name = self.storageini.get_option(vol_group_name, 'name')
        volgrp_devlist = self.storageini.get_option(vol_group_name,
                                                    'device_list')
        vg_path = self.litp. \
            create(volume_groups,
                   object_id=volgrp_name,
                   object_type='volume-group',
                   properties={
                       'volume_group_name': volgrp_name})
        self.litp.create('{0}/physical_devices'.format(vg_path),
                         object_type='physical-device',
                         object_id='devices',
                         properties={'device_name': volgrp_devlist})
        return vg_path

    def define_node_file_systems(self, volgrp_path, filesystem_ini_name):
        file_systems = '{0}/file_systems'.format(volgrp_path)

        fs_name = self.storageini.get_option(filesystem_ini_name, 'name')
        fs_type = self.storageini.get_option(filesystem_ini_name, 'type')
        fs_size = self.storageini.get_option(filesystem_ini_name, 'size')
        fs_mp = self.storageini.get_option(filesystem_ini_name, 'mount_point')

        self.litp.create(file_systems, object_id=fs_name,
                         object_type='file-system',
                         properties={'type': fs_type, 'mount_point': fs_mp,
                                     'size': fs_size})

    def define_storage_profile(self, profile_ini_name):
        profile_name = self.storageini.get_option(profile_ini_name,
                                                  'profile_name')
        storage_profiles = '/infrastructure/storage/storage_profiles'
        profile_path = self.litp. \
            create(storage_profiles,
                   object_id=profile_name,
                   object_type='storage-profile',
                   properties={
                       'storage_profile_name': profile_name})

        vol_group = self.storageini.get_option(profile_ini_name,
                                               'volume_group')
        vg_path = self.define_node_volume_groups(vol_group, profile_path)
        for fs in self.storageini.get_option(profile_ini_name, 'file_systems',
                                             seperator=','):
            self.define_node_file_systems(vg_path, fs)

    def link_node_system(self, node_path, system_name):
        object_type = None
        if self.hw_type == self.HWTYPE_LIBVIRT:
            object_type = 'libvirt-system'
        elif self.hw_type == self.HWTYPE_REAL:
            object_type = 'blade'
        elif self.hw_type == self.HWTYPE_CLOUD:
            object_type = 'system'

        self.litp.link('{0}/system'.format(node_path),
                       object_type=object_type,
                       properties={'system_name': system_name})

    def _define_ms_libvirt_deployment(self):
        deployment_name = self.siteini.get_option(self.deployment_id,
                                                  'deployment_name')
        self.litp.link('/ms/libvirt', object_type='libvirt-provider',
                       properties={'name': deployment_name})

        eth1_ipv4_address = self.siteini.get_option('LMS', 'eth1_ipv4_address')
        network_id = self.siteini.get_option(self.deployment_id,
                                             'managed_node_network_id')
        self.assign_node_address('/ms', network_id, eth1_ipv4_address,
                                 'internal_ip')

    def define_ms_deployment(self):
        if self.hw_type == self.HWTYPE_LIBVIRT:
            self._define_ms_libvirt_deployment()
        elif self.hw_type not in [self.HWTYPE_REAL, self.HWTYPE_CLOUD]:
            raise DeployerException(1,
                                    'Unsupported hardware type \'{0}\''.format(
                                        self.hw_type))

        hostname = self.siteini.get_option('LMS', 'hostname')
        self.litp.update('/ms', properties={'hostname': hostname})
        self.litp.link('/ms/system', object_type='system',
                       properties={
                           'system_name': self.LMS_SYSTEM_NAME
                       })

        self.litp.link('/ms/system', object_type='system',
                       properties={
                           'system_name': self.LMS_SYSTEM_NAME
                       })
        cobbler_boot_network = self.siteini.get_option('LMS',
                                                       'cobbler_boot_network')
        self.litp.create('/ms/services', object_type='cobbler-service',
                         object_id='cobbler',
                         properties={'boot_network': cobbler_boot_network})

        eth0_ipv4_address = self.siteini.get_option('LMS', 'eth0_ipv4_address')
        network_id = self.siteini.get_option(self.deployment_id,
                                             'managed_node_network_id')
        self.assign_node_address('/ms', network_id, eth0_ipv4_address,
                                 'external_ip')

    def link_node_os_profile(self, node_path, node):
        osprofile = self.siteini.get_option(node, 'os_profile')
        osprofile_name = self.siteini.get_option(osprofile, 'name')
        osprofile_version = self.siteini.get_option(osprofile,
                                                    'version')
        self.litp.link('{0}/os'.format(node_path),
                       object_type='os-profile',
                       properties={'name': osprofile_name,
                                   'version': osprofile_version})

    def link_node_storage_profile(self, node_path, node):
        storageprofile = self.siteini.get_option(node, 'local_storage_profile')
        storageprofile_name = self.storageini.get_option(storageprofile,
                                                         'profile_name')
        self.litp.link('{0}/storage_profile'.format(node_path),
                       object_type='storage-profile',
                       properties={
                           'storage_profile_name': storageprofile_name})

    def link_node_network_profile(self, node_path):
        self.litp.link('{0}/network_profile'.
                       format(node_path),
                       object_type='network-profile',
                       properties=
                       {'name': 'node_network_profile'})

    def define_deployment(self):
        self.define_ms_deployment()

        deployment_name = self.siteini.get_option(self.deployment_id,
                                                  'deployment_name')

        managed_node_network_id = self.siteini. \
            get_option(self.deployment_id,
                       'managed_node_network_id')

        deploy_path = self.litp.create('/deployments',
                                       object_type='deployment',
                                       object_id=deployment_name)

        clusters = self.siteini.get_option(self.deployment_id, 'clusters',
                                           seperator=',')

        rstart = self.siteini.get_option('LMS', 'blade_pool_range_start')
        rend = self.siteini.get_option('LMS', 'blade_pool_range_end')
        rsubnet = self.siteini.get_option('LMS', 'blade_pool_range_subnet')
        rgateway = self.siteini.get_option('LMS', 'blade_pool_range_gateway')
        self.litp.create('/infrastructure/networking/ip_ranges/',
                         object_type='ip-range',
                         object_id=managed_node_network_id,
                         properties={'network_name': managed_node_network_id,
                                     'start': rstart, 'end': rend,
                                     'subnet': rsubnet, 'gateway': rgateway})

        for cluster in clusters:
            cluster_path = self.litp.create('{0}/clusters'.format(deploy_path),
                                            object_type='cluster',
                                            object_id=cluster)

            for node in self.get_cluster_nodes(cluster):
                hostname = self.siteini.get_option(node, 'hostname')
                node_path = self.litp.create('{0}/nodes'.format(cluster_path),
                                             object_type='node',
                                             object_id=node,
                                             properties={'hostname': hostname})

                self.link_node_system(node_path, node)

                self.link_node_os_profile(node_path, node)

                self.link_node_storage_profile(node_path, node)

                self.link_node_network_profile(node_path)

                eth0_ipv4 = self.siteini.get_option(node, 'eth0_ipv4')
                self.assign_node_address(node_path, managed_node_network_id,
                                         eth0_ipv4, '{0}_ip'.format(node))

    def assign_node_address(self, node_path, network_id, ipv4, address_id):
        self.litp.link('{0}/ipaddresses/{1}'.
                       format(node_path, address_id),
                       object_type='ip-range',
                       properties=
                       {'network_name': network_id,
                        'address': ipv4})

    def _define_lms_bridged_network_profile(self):
        deploy_network = self.siteini.get_option(self.deployment_id,
                                                 'managed_node_network_id')

        profile_path = self.litp. \
            create('/infrastructure/networking/network_profiles',
                   object_id='lms_network_profile',
                   object_type='network-profile',
                   properties={'name': 'lms_network_profile',
                               'management_network': deploy_network})

        self.litp.create('{0}/networks'.format(profile_path),
                         object_type='network',
                         object_id='network_internal',
                         properties={'network_name': deploy_network,
                                     'bridge': 'br0'})
        self.litp.create('{0}/bridges'.format(profile_path),
                         object_type='bridge',
                         object_id='br0',
                         properties={'bridge_name': 'br0',
                                     'interfaces': 'if0',
                                     'stp': 'on', 'forwarding_delay': '0'})
        self.litp.create('{0}/interfaces'.format(profile_path),
                         object_type='interface',
                         object_id='if0',
                         properties={'interface_basename': 'eth1'})

        self.litp.create('{0}/networks'.format(profile_path),
                         object_type='network',
                         object_id='lms_network_external',
                         properties={'network_name': 'lms_network_external',
                                     'interface': 'if1',
                                     'default_gateway': 'true'})
        self.litp.create('{0}/interfaces'.format(profile_path),
                         object_type='interface',
                         object_id='if1',
                         properties={'interface_basename': 'eth0'})

    def _define_lms_real_network_profile(self):
        deploy_network = self.siteini.get_option(self.deployment_id,
                                                 'managed_node_network_id')

        profile_path = self.litp. \
            create('/infrastructure/networking/network_profiles',
                   object_id='lms_network_profile',
                   object_type='network-profile',
                   properties={'name': 'lms_network_profile',
                               'management_network': deploy_network})

        self.litp.create('{0}/networks'.format(profile_path),
                         object_type='network',
                         object_id='lms_network_external',
                         properties={'network_name': deploy_network,
                                     'interface': 'if0'})
        self.litp.create('{0}/interfaces'.format(profile_path),
                         object_type='interface',
                         object_id='if0',
                         properties={'interface_basename': 'eth0'})

    def _define_lms_network_profile(self):
        if self.hw_type == self.HWTYPE_LIBVIRT:
            self._define_lms_bridged_network_profile()
        elif self.hw_type in [self.HWTYPE_REAL, self.HWTYPE_CLOUD]:
            self._define_lms_real_network_profile()
        else:
            raise DeployerException(1,
                                    'Unsupported hardware type \'{0}\''.format(
                                        self.hw_type))

    def _define_node_network_profile(self):
        deploy_network = self.siteini.get_option(self.deployment_id,
                                                 'managed_node_network_id')
        profile_path = self.litp. \
            create('/infrastructure/networking/network_profiles',
                   object_id='node_network_profile',
                   object_type='network-profile',
                   properties={'name': 'node_network_profile',
                               'management_network': deploy_network})

        self.litp.create('{0}/networks'.format(profile_path),
                         object_type='network',
                         object_id='network_external',
                         properties={'network_name': deploy_network,
                                     'interface': 'if0'})
        self.litp.create('{0}/interfaces'.format(profile_path),
                         object_type='interface',
                         object_id='if0',
                         properties={'interface_basename': 'eth0'})

    def define_network_profiles(self):
        self._define_lms_network_profile()
        self._define_node_network_profile()

    def define_storage_profiles(self):
        clusters = self.siteini.get_option(self.deployment_id, 'clusters',
                                           seperator=',')
        already_defined = []
        for cluster in clusters:
            nodes = self.siteini.get_option(cluster, 'nodes', seperator=',')
            for node in nodes:
                profile = self.siteini.get_option(node,
                                                  'local_storage_profile')
                if profile not in already_defined:
                    self.define_storage_profile(profile)
                    already_defined.append(profile)

    def define_os_profiles(self):
        clusters = self.siteini.get_option(self.deployment_id, 'clusters',
                                           seperator=',')
        already_defined = []
        for cluster in clusters:
            nodes = self.siteini.get_option(cluster, 'nodes', seperator=',')
            for node in nodes:
                os_profile = self.siteini.get_option(node, 'os_profile')
                if os_profile not in already_defined:
                    self.define_os_profile(os_profile)
                    already_defined.append(os_profile)

    def create_plan(self):
        self.litp.create_plan(self.INST_UPG_PLAN_NAME)

    def show_plan(self):
        data = self.litp.get_plan_status(self.INST_UPG_PLAN_NAME)
        for task in data:
            task_path = task['path']
            task_state = task['state']
            _color = Formatter.PLAN_STATE_COLORMAP['default']
            _path = Formatter.format_color(task_path, _color)
            if task_state in Formatter.PLAN_STATE_COLORMAP:
                task_color = Formatter.PLAN_STATE_COLORMAP[task_state]
            else:
                task_color = Formatter.PLAN_STATE_COLORMAP['default']
            task_string = Formatter.format_color(task_state, task_color)
            msg = '{0} {1} ({2})'.format(task_string, task['description'],
                                         _path)
            print(msg)

    def run_plan(self):
        self.litp.set_plan_state(self.INST_UPG_PLAN_NAME, 'running')

    def wait_plan_complete(self):
        task_states = {}

        def format_state_string(task_state):
            if task_state in Formatter.PLAN_STATE_COLORMAP:
                task_color = Formatter.PLAN_STATE_COLORMAP[task_state]
            else:
                task_color = Formatter.PLAN_STATE_COLORMAP['default']
            return Formatter.format_color(task_state, task_color)

        while True:
            success_tasks = 0
            rtc = 0
            while True:
                try:
                    rtc += 1
                    tasks = self.litp.get_plan_status(self.INST_UPG_PLAN_NAME)
                    break
                except LitpException as le:
                    if rtc > 3:
                        raise le
                    else:
                        sleep(1)
            diffs = False
            failed_tasks = 0
            plan_overview = ''
            changes = []
            for task in tasks:
                task_path = task['path']
                task_state = task['state']
                if task_path in task_states:
                    if task_state != task_states[task_path]:
                        _old = task_states[task_path]
                        _new = format_state_string(task_state)
                        _color = Formatter.PLAN_STATE_COLORMAP['default']
                        _desc = task['description']
                        _path = Formatter.format_color(task_path, _color)
                        changes.append('{0} -> {1} {2} [{3}]'.format(
                            _old, _new, _desc, _path))
                        diffs = True
                        task_states[task_path] = task_state
                else:
                    task_states[task_path] = task_state
                    diffs = True
                if task_state == 'Success':
                    success_tasks += 1
                elif task_state == 'Failed':
                    failed_tasks += 1

                task_string = format_state_string(task_state)
                _color = Formatter.PLAN_STATE_COLORMAP['default']
                _path = Formatter.format_color(task_path, _color)
                plan_overview += '\n{0} {1} ({2})'.format(task_string,
                                                          task['description'],
                                                          _path)
            if failed_tasks > 1:
                raise LitpException(1, 'Plan execution failed')

            if diffs or success_tasks == len(tasks):
                print(plan_overview)

            if len(changes) > 0:
                print('State Transitions:')
                for change in changes:
                    print('\t{0}'.format(change))

            if success_tasks == len(tasks):
                print('All plan tasks complete')
                return
            sleep(1)

    def get_site_value(self, section, option, seperator=None):
        return self.siteini.get_option(section, option, seperator=seperator)

    def define_systems(self):
        if self.hw_type == self.HWTYPE_LIBVIRT:
            self._define_libvirt_node_systems()
        elif self.hw_type in [self.HWTYPE_REAL, self.HWTYPE_CLOUD]:
            self._define_real_node_systems()
        else:
            raise DeployerException(1,
                                    'Unsupported hardware type \'{0}\''.format(
                                        self.hw_type))

    def define_ntp(self):
        nodes = self.litp.find('/deployments', object_type='node').keys()
        servers = self.litp.create('/software/items', object_id='net_servers',
                                   object_type='ntp-service',
                                   properties={'ensure': 'present'})
        servers = '{0}/servers'.format(servers)
        ntp_servers = self.siteini.get_site_section_keys(self.deployment_id,
                                                         key_filter='ntp_*')

        for ntp in ntp_servers:
            address = self.siteini.get_option(self.deployment_id, ntp)
            self.litp.create(servers, object_id=ntp, object_type='ntp-server',
                             properties={'server': address})
            self.litp.link('/ms/items/{0}'.format(ntp),
                           object_type='ntp-service',
                           properties={'ensure': 'present'})
            for node in nodes:
                self.litp.link('{0}/items/{1}'.format(node, ntp),
                               object_type='ntp-service',
                               properties={'ensure': 'present'})


def main(argv):
    arg_parser = OptionParser()
    arg_parser.add_option('--litpd_host', dest='litpd_host',
                          default='localhost', help='LITPD host')
    arg_parser.add_option('--site', dest='site_file',
                          help='Site desciption file')
    arg_parser.add_option('--hw_type', dest='hw_type',
                          help='The type of hardware being deployed, '
                               'values can one of [real|libvirt|cloud]')
    (options, args) = arg_parser.parse_args()
    if len(argv) == 0:
        arg_parser.print_help()
        exit(2)
    if not options.site_file:
        arg_parser.print_help()
        exit(2)
    if not options.hw_type:
        arg_parser.print_help()
        exit(2)

    deployment_id = 'DEPLOYMENT'
    deployment_description = options.site_file
    deployment_hwtype = options.hw_type

    de = deployer(deployment_id, deployment_description, deployment_hwtype,
                  litpd_host=options.litpd_host)

    de.enable_litp_debug()
    try:
        print('Starting Install/Upgrade at {0}'.format(datetime.now()))
        de.define_network_profiles()
        de.define_storage_profiles()
        de.define_os_profiles()
        de.define_ms_system()
        de.define_node_systems()
        de.define_deployment()
        de.define_ntp()
        de.create_plan()
        de.show_plan()
        de.run_plan()
        de.wait_plan_complete()
    finally:
        de.reset_litp_debug()
    print('Completed Install/Upgrade at {0}'.format(datetime.now()))



if __name__ == '__main__':
    try:
        main(sys.argv)
    except KeyboardInterrupt as e:
        pass
    except LitpException as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, '{0}'.format(exc_value.args[1]),
                                  exc_traceback, file=sys.stderr)
        if e.args[1]['messages']:
            for error in e.args[1]['messages']:
                for key, value in error.items():
                    sys.stderr.write('\t{0} -> {1}\n'.format(key, value))
        exit(exc_value.args[0])
