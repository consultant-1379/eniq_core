from genericpath import exists
from os.path import dirname, normpath
from subprocess import Popen, PIPE
import sys


class rpm_helper:
    h_NAME = 'Name'
    h_VERSION = 'Version'
    h_RELEASE = 'Release'
    h_PACKAGER = 'Packager'
    h_FILENAMES = 'Filenames'

    def __init__(self, debug=False):
        self.DEBUG = debug

    def debug(self, message):
        if self.DEBUG:
            sys.stdout.write('{0}\n'.format(message))
            sys.stdout.flush()

    def execute_process(self, args, wd=None):
        self.debug(' '.join(args))
        process = Popen(args, stdout=PIPE, cwd=wd, stderr=PIPE, shell=False)
        stdout, stderr = process.communicate()
        if process.returncode:
            raise IOError(
                'Error executing command {0}\n{1}'.format(args, stderr))
        return stdout.split('\n')

    def h_format(self, header_name):
        return header_name + ':%{' + header_name + '}'

    def get_rpm_header(self, rpm_path):
        if sys.platform.startswith('win'):
            from os.path import splitunc

            if splitunc(rpm_path)[0] == '':
                rpm_path = 'C:{0}'.format(normpath(rpm_path))
            rpm_path = '{0}'.format(rpm_path.replace('\\', '/'))
        if not exists(rpm_path):
            raise IOError('File \'{0}\' not found'.format(rpm_path))
        query_format = self.h_format(self.h_NAME)
        query_format = '{0}\n{1}'.format(query_format,
                                         self.h_format(self.h_VERSION))
        query_format = '{0}\n{1}'.format(query_format,
                                         self.h_format(self.h_RELEASE))
        query_format = '{0}\n{1}'.format(query_format,
                                         self.h_format(self.h_PACKAGER))
        if sys.platform.startswith('win'):
            query_format = '\'{0}\''.format(query_format)
        args = ['rpm', '-q', '-p', '--queryformat', query_format, rpm_path]
        result = self.execute_process(args, wd=dirname(rpm_path))
        header = {}
        for line in result:
            parts = line.split(':', 1)
            header[parts[0]] = parts[1]
        self.debug('Header for {0} {1}'.format(rpm_path, header))
        return header