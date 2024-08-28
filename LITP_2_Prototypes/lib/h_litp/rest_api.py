from ConfigParser import SafeConfigParser
from base64 import encodestring
from httplib import HTTPSConnection
import os
from time import sleep
from simplejson import dumps, loads


class rest_client():
    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 9999
    DEFAULT_REST_VERSION = 'v1'

    def debug(self, message):
        if self.DEBUG:
            print(message)

    def __init__(self, rest_user, rest_passwd, rest_host=DEFAULT_HOST, rest_port=DEFAULT_PORT,
                 rest_version=DEFAULT_REST_VERSION,
                 _debug=False):
        self.rest_user = rest_user
        self.rest_passwd = rest_passwd
        self.rest_host = rest_host
        self.rest_port = rest_port
        self.rest_version = rest_version
        self.DEBUG = _debug
        self.BASE_URL = 'https://{0}:{1}'.format(self.rest_host, self.rest_port)
        self.debug('REST URI is {0}'.format(self.BASE_URL))
        self.conn = HTTPSConnection(host=self.rest_host, port=self.rest_port)

    def get_headers(self):
        val = encodestring('{0}:{1}'.format(self.rest_user, self.rest_passwd)).replace('\n', '')
        return {'Authorization': 'Basic {0}'.format(val), 'Content-Type': 'application/json', 'content-length': 0}

    def get_version_path(self, model_path):
        return '/litp/rest/{0}{1}'.format(self.rest_version, model_path)

    def _op(self, model_path, crud_op, request_body=None):
        headers = self.get_headers()
        rest_path = self.get_version_path(model_path)
        data = None
        length = 0
        if request_body is not None:
            data = dumps(request_body)
            length = len(data)
        headers['Content-Length'] = length
        self.conn.request(crud_op, rest_path, data, headers)
        _response = self.conn.getresponse()
        response = _response.read()
        json = loads(response)
        if json['messages']:
            raise IOError(3, json['messages'])
        return _response.status, json['data']

    def get(self, model_path):
        code, data = self._op(model_path, 'GET')
        return data

    def get_children(self, model_path):
        data = self.get(model_path)
        child_paths = []
        for child in data['links']['children']:
            if model_path == '/':
                _path = '/{1}'.format(model_path, child['id'])
            else:
                _path = '{0}/{1}'.format(model_path, child['id'])
            child_paths.append({'path': _path, 'data': child})
        return child_paths

    def get_attributes(self, model_path, attributes=None):
        code, data = self._op(model_path, 'GET')
        if attributes:
            rlist = {}
            for att in attributes:
                if att.startswith('properties.'):
                    pkey = att.split('.', 1)[1]
                    rlist[att] = data['properties'][pkey]
                else:
                    rlist[att] = data[att]
            return rlist
        else:
            return data

    def get_plan_status(self):
        plans = self.get_children('/plans')
        if len(plans) == 0:
            print('No plans found!')
            exit(0)
        phase_path = '{0}/phases'.format(plans[0]['path'])
        phase_list = self.get_children(phase_path)
        if len(phase_list) == 0:
            print('No phases found in plan \'{0}\'!'.format(phase_path))
            exit(0)
        plan_status = []
        for phase in phase_list:
            task_path = '{0}/tasks'.format(phase['path'])
            tasks = self.get_children(task_path)
            for task in tasks:
                task_info = self.get_attributes(task['path'], ['state', 'properties.description'])
                plan_status.append({
                    'path': task['path'],
                    'state': task_info['state'],
                    'description': task_info['properties.description']
                })
        return plan_status

    def _get_type(self, data):
        types = data['type']
        if 'collection' in types:
            types = types['collection']['type']
        return types['name']

    def _find_type(self, model_path, path_list=None, r_type=None):
        if path_list is None:
            path_list = []
        _this_node = self.get(model_path)
        _this_node_type = self._get_type(_this_node)
        if r_type is None or '*' == r_type or str(_this_node_type) == str(r_type):
            path_list.append(model_path)
        children = self.get_children(model_path)
        if len(children) > 0:
            for child in children:
                self._find_type(child['path'], path_list, r_type)

    def find_type(self, model_path, r_type=None):
        path_list = []
        self._find_type(model_path, path_list, r_type)
        return path_list

    def watch_plan(self):
        states = self.get_plan_status()
        state_colormap = {
            'Success': '\033[36m',
            'Running': '\033[7m',
            'Initial': '\033[33m',
            'default': '\033[37m'
        }

        def format_color(text, color):
            return '{0}{1}{2} '.format(color, text, '\033[0m')

        task_states = {}
        while True:
            success_tasks = 0
            tasks = self.get_plan_status()
            diffs = False
            failed_tasks = 0
            _buffer = ''
            for task in tasks:
                task_path = task['path']
                task_state = task['state']
                if task_path in task_states:
                    if task_state != task_states[task_path]:
                        diffs = True
                else:
                    task_states[task_path] = task_state
                    diffs = True
                if task_state == 'Success':
                    success_tasks += 1
                elif task_state == 'Failed':
                    failed_tasks += 1
                if task_state in state_colormap:
                    task_color = state_colormap[task_state]
                else:
                    task_color = state_colormap['default']
                task_string = format_color(task_state, task_color)
                _path = format_color(task_path, state_colormap['default'])
                _buffer += '\n{0} {1} ({2})'.format(task_string, task['description'], _path)
            if success_tasks == len(tasks):
                print(_buffer)
                print('All plan tasks complete')
                return
            if failed_tasks > 1:
                print(_buffer)
                print('Stopping due to failed tasks.')
                return
            if diffs:
                print(_buffer)
            sleep(1)


if __name__ == '__main__':
    try:
        litprc = os.path.expanduser("~/.litprc")
        if os.path.exists(litprc):
            parser = SafeConfigParser()
            parser.read(litprc)
            expected_options = ['username', 'password']
            _user = parser.get('litp-client', 'username')
            _password = parser.get('litp-client', 'password')
        else:
            _user = 'litp-admin'
            _password = '4lackwar31'
        cli = rest_client(_user, _password, rest_host='localhost')
        cli.watch_plan()
    except KeyboardInterrupt:
        pass
