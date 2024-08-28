from os.path import join
from tempfile import gettempdir
from unittest import TestCase
from h_litp.litp_rest_client import litp_rest_client


class litp_rest_client_test(TestCase):
    def test_xstr(self):
        _dict = None
        string = litp_rest_client.xstr(_dict)
        self.assertEquals(string, '{}')
        _dict = {}
        string = litp_rest_client.xstr(_dict)
        self.assertEquals(string, '{}')
        _dict['abc'] = '123'
        string = litp_rest_client.xstr(_dict)
        self.assertEquals(string, '{\'abc\': \'123\'}')

    def test_get_api_access_users(self):
        try:
            litp_rest_client.get_api_access_users(litprc='')
            self.fail('Exception should have been thrown for non'
                      ' existant .litprc file')
        except IOError as ioe:
            pass
        block = 'litp-client'
        user = 'some-user'
        passwd = 'some-password'
        litprc_path = join(gettempdir(), '.litprc')
        _file = open(litprc_path, 'w+')
        _file.write('[{0}]\n'.format(block))
        _file.write('username = {0}\n'.format(user))
        _file.write('password = {0}\n'.format(passwd))
        _file.close()
        data = litp_rest_client.get_api_access_users(litprc=litprc_path)
        self.assertTrue(block in data)
        self.assertEquals(data[block]['username'], user)
        self.assertEquals(data[block]['password'], passwd)
