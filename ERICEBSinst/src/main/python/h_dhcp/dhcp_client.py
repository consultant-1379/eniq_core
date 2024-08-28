from time import sleep
import sys
from h_util.SSHSocket import SSHSocket


class dhcp_client:
    def log(self, message):
        sys.stdout.write('{0}\n'.format(message))
        sys.stdout.flush()

    def do_dhcp(self, dhcp_server, username, password):
        ssh = SSHSocket()
        ssh.setHost(dhcp_server)
        ssh.setUser(username)
        ssh.setPasswd(password)
        ssh.connect()
        try:
            try:
                self.log('Stopping dhcpd')
                ssh.execute(' '.join(['/etc/init.d/dhcpd', 'status']))
                ssh.execute(' '.join(['/etc/init.d/dhcpd', 'stop']))
            except IOError as ioe:
                if ioe.errno == 3:
                    # already stopped
                    pass
            self.log('Removing dchp template')
            ssh.execute('/bin/rm -f /etc/cobbler/dhcp.template')
            self.log('Restarting puppet ...')
            ssh.execute('/etc/init.d/puppet restart')
            self.log('Waiting for dhcpd process ...')
            time = 0
            while True:
                sleep(1)
                time += 1
                try:
                    line = '\tTime elapsed: %02d:%02d%40s' % \
                           ((time / 60), (time % 60), ' ')
                    sys.stdout.write('{0}\r'.format(line))
                    sys.stdout.flush()
                    ssh.execute('/sbin/pidof dhcpd')
                    self.log('\nCobbler is now ready for distro import')
                    break
                except IOError:
                    pass
        finally:
            ssh.disconnect()