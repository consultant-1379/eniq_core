from h_util.SSHSocket import SSHSocket
from h_util.h_utils import exec_process


class litp_crypt:
    def __init__(self, debug=False):
        self.DEBUG = debug

    def debug(self, msg):
        if self.DEBUG:
            print(msg)

    def _build_command(self, cmd_type, service, user, password):
        if cmd_type == 'set':
            return '/usr/bin/litpcrypt set {0} {1} "{2}"'.format(service, user,
                                                                 password)
        else:
            return 'exit 1'

    def _set_local(self, service, user, password):
        command = self._build_command('set', service, user, password)
        self.debug(command)
        results = exec_process(command)
        self.debug(results)

    def _set_remote(self, service, user, password, rconn_details):
        ssh = SSHSocket()
        ssh.setUser(rconn_details['username'])
        ssh.setPasswd(rconn_details['password'])
        ssh.setHost(rconn_details['host'])
        try:
            command = self._build_command('set', service, user, password)
            ssh.connect()
            self.debug(command)
            results = ssh.execute(command)
            self.debug(results)
        finally:
            ssh.disconnect()

    def set(self, service, user, password, remote_details=None):
        if remote_details:
            self._set_remote(service, user, password, remote_details)
        else:
            self._set_local(service, user, password)