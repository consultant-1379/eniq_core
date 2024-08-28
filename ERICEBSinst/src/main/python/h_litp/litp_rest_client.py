from ConfigParser import ConfigParser
from base64 import encodestring
from httplib import OK, ACCEPTED, CREATED, NOT_FOUND
from httplib import HTTPSConnection, HTTPException
from httplib import BAD_REQUEST
from os.path import expanduser, exists, join
import sys

from simplejson import loads, dumps


def read_litprc(litprc=None):
    if not litprc:
        HOME = expanduser("~")
        litprc = join(HOME, '.litprc')
    if not exists(litprc):
        raise IOError(1, 'File {0} not found'.format(litprc))
    reader = ConfigParser()
    reader.read(litprc)
    data = {}
    for section in reader.sections():
        data[section] = {
            'username': reader.get(section, 'username'),
            'password': reader.get(section, 'password')
        }
    return data


class LitpException(Exception):
    pass


class litp_rest_client:
    DEFAULT_LITPD_HOST = 'localhost'
    DEFAULT_LITPD_PORT = 9999
    DEFAULT_REST_VERSION = 'v1'

    def __init__(self, litpd_host=DEFAULT_LITPD_HOST,
                 litpd_port=DEFAULT_LITPD_PORT,
                 litp_version=DEFAULT_REST_VERSION, debug=False):
        self.litpd_host = litpd_host
        self.litpd_port = litpd_port
        self.litp_version = litp_version
        self.DEBUG = debug
        self.BASE_REST_PATH = '/litp/rest/{0}'.format(self.litp_version)
        self.CONFIG_REST_PATH = '/litp/config/'
        litprc_data = read_litprc()
        if 'litp-client' not in litprc_data:
            raise LitpException(1, 'No litp-client entry in ~/.litprc file')
        self.https_user = litprc_data['litp-client']
        self.https = HTTPSConnection(self.litpd_host, self.litpd_port)

    @staticmethod
    def xstr(s):
        if s is None:
            return '{}'
        return str(s)

    def debug(self, message):
        if self.DEBUG:
            sys.stdout.write('{0}\n'.format(message))
            sys.stdout.flush()

    def log(self, message):
        sys.stdout.write('{0}\n'.format(message))
        sys.stdout.flush()

    def get_headers(self, content_length=0):
        encoded = encodestring(
            "{0}:{1}".format(self.https_user['username'].strip(),
                             self.https_user['password'].strip())).strip()
        return {'Content-Type': 'application/json',
                'content-length': content_length,
                'Authorization': 'Basic {0}'.format(encoded)}

    def https_request(self, request_type, model_path, data=None,
                      base_rest_path=None):
        if not base_rest_path:
            base_rest_path = self.BASE_REST_PATH
        rest_path = '{0}{1}'.format(base_rest_path, model_path)
        self.debug('HTTPS {0} request @ {1}'.format(request_type, rest_path))
        content_length = 0
        body = None
        if data:
            body = dumps(data)
            content_length = len(body)
        headers = self.get_headers(content_length)
        try:
            self.https.request(request_type, rest_path, body=body,
                               headers=headers)
            response = self.https.getresponse()
            response_data = response.read()
        except HTTPException as httpe:
            raise LitpException(1, {'error': str(httpe), 'reason': httpe})
        if response.status == BAD_REQUEST:
            raise LitpException(response.status, response_data)
        results = loads(response_data)
        if response.status not in [OK, CREATED, ACCEPTED]:
            messages = None
            if results['messages']:
                messages = results['messages']
            raise LitpException(response.status,
                                {'reason': response.reason, 'path': model_path,
                                 'messages': messages})
        self.debug(results)
        return results

    def update(self, node_path, properties):
        self.log('litp update -p {0} -o {1}'.format(node_path,
                                                    self.xstr(properties)))
        self.https_request('PUT', node_path, data={'properties': properties})

    def create(self, parent_node, object_id, object_type, properties=None):
        node_path = '{0}/{1}'.format(parent_node, object_id)
        if self.exists(node_path) is False:
            self.log('litp create '
                     '-p {0} -t {1} -p {2}'.format(node_path,
                                                   object_type,
                                                   self.xstr(properties)))
            data = {'id': object_id, 'type': object_type}
            if properties is not None:
                data['properties'] = properties
            self.https_request('POST', parent_node, data=data)
        elif properties is not None:
            self.update(node_path, properties)
        return node_path

    def remove(self, model_path):
        self.log('litp remove -p {0}'.format(model_path))
        self.https_request('DELETE', model_path)

    def exists(self, model_path):
        try:
            self.https_request('GET', model_path)
            return True
        except LitpException as le:
            _code = le.args[0]
            if _code == NOT_FOUND:
                return False
            else:
                raise le

    def link(self, model_path, object_type, properties):
        if self.exists(model_path) is True:
            self.remove(model_path)
        self.log(
            'litp link -p {0} -t {1} -o {2}'.format(model_path, object_type,
                                                    self.xstr(properties)))
        path, oid = model_path.rsplit('/', 1)
        data = {'link': object_type, 'id': oid, 'properties': properties}
        self.https_request('POST', path, data=data)

    def get(self, model_path, log=True):
        if log is True:
            self.log('litp show -p {0}'.format(model_path))
        return self.https_request('GET', model_path)

    def get_children(self, model_path):
        data = self.get(model_path, log=False)
        child_paths = []
        if '_embedded' in data:
            for child in data['_embedded']['item']:
                if model_path == '/':
                    _path = '/{1}'.format(model_path, child['id'])
                else:
                    _path = '{0}/{1}'.format(model_path, child['id'])
                child_paths.append({'path': _path, 'data': child})
        return child_paths

    def create_plan(self, plan_name):
        self.log('litp create_plan {0}'.format(plan_name))
        self.https_request('POST', '/plans',
                           data={'id': plan_name, 'type': 'plan'})

    def get_plan_status(self, plan_name):
        plan_path = '/plans/{0}'.format(plan_name)
        phase_path = '{0}/phases'.format(plan_path)
        phase_list = self.get_children(phase_path)
        if len(phase_list) == 0:
            print('No phases found in plan \'{0}\'!'.format(phase_path))
            exit(0)
        plan_status = []
        for phase in phase_list:
            task_path = '{0}/tasks'.format(phase['path'])
            tasks = self.get_children(task_path)
            for task in tasks:
                task_info = self.get(task['path'], log=False)
                plan_status.append({
                    'path': task['path'],
                    'state': task_info['state'],
                    'description': task_info['properties']['description']
                })
        return plan_status

    def set_plan_state(self, plan_name, state):
        plan_path = '/plans/{0}'.format(plan_name)
        self.https_request('PUT', plan_path, data={'state': state})

    def set_debug(self, state):
        self.https_request('PUT', 'debug', data={'debug': state},
                           base_rest_path=self.CONFIG_REST_PATH)

    def find(self, start_path, object_type):
        found = {}
        data = self.get(start_path, log=False)
        if '_embedded' in data:
            for item in data['_embedded']['item']:
                if item['item-type-name'] == object_type:
                    path = '{0}/{1}'.format(start_path, item['id'])
                    found[path] = item

        children = self.get_children(start_path)
        for child in children:
            _found = self.find(child['path'], object_type)
            if _found:
                found.update(_found)
        return found