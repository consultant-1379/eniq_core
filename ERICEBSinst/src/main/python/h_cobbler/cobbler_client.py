import xmlrpclib


class cobbler_client:
    def __init__(self, cobbler_host, username, password, debug=False):
        self.cobbler_host = cobbler_host
        self.username = username
        self.password = password
        self.DEBUG = debug
        self.server = xmlrpclib.Server(
            'http://{0}/cobbler_api'.format(self.cobbler_host))
        self.token = self.server.login(self.username, self.password)

    def find_distro(self, name='*'):
        args = {'name': name}
        return self.server.find_distro(args)

    def find_system(self, name='*'):
        args = {'name': name}
        return self.server.find_system(args)
