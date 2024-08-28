from h_litp.core.execution_manager import ConfigTask
from h_litp.core.litp_logging import LitpLogger
from h_litp.core.plugin import Plugin

logger = LitpLogger('PkgMgmtRepoPlugin')


class PkgMgmtRepoPlugin(Plugin):
    YUM_REPO_MANIFEST = 'yum::assure_yum_repos'
    RESOURCE_REPOSITORY = 'repository'

    def info(self, message):
        logger.trace.info('PkgMgmtRepoPlugin - {0}'.format(message))

    def create_configuration(self, plugin_api_context):
        # Look for all objects of type 'node' in the model
        nodes = plugin_api_context.query("node") + plugin_api_context.query("ms")
        task_list = []
        # Get tasks to create all newly defined repos in the model
        self._add_repo_tasks(nodes, task_list)
        # Get tasks to remove deconfigured repos in the model
        self._remove_repo_tasks(nodes, task_list)
        return task_list

    def _remove_repo_tasks(self, managed_node_list, task_list):
        for cluster_node in managed_node_list:
            # Look for deleted/deconfigures objects of type 'repository' in the model user a node
            node_repos = cluster_node.query(self.RESOURCE_REPOSITORY, is_for_removal=True)
            for node_repo in node_repos:
                puppet_manifest_args = {
                    'name': node_repo.properties['name'],
                    'ensure': 'absent',
                }
                info = 'Remove remote YUM repo {0} from host {1}'.format(node_repo.properties['name'],
                                                                         cluster_node.properties['hostname'])
                self.info(info)
                task = ConfigTask(cluster_node, node_repo, info, self.YUM_REPO_MANIFEST,
                                  id=node_repo.properties['name'],
                                  **puppet_manifest_args)
                task_list.append(task)

    def _add_repo_tasks(self, managed_node_list, task_list):
        for cluster_node in managed_node_list:
            # Look for create objects of type 'repository' in the model user a node
            node_repos = cluster_node.query(self.RESOURCE_REPOSITORY, is_initial=True)
            _hostname = cluster_node.properties['hostname']
            for node_repo in node_repos:
                info = 'Create remote YUM repo {0} on host {1}'.format(node_repo.properties['name'], _hostname)
                self.info(info)
                puppet_manifest_args = {
                    'name': node_repo.properties['name'],
                    'url': node_repo.properties['url'],
                    'ensure': 'present',
                }
                task = ConfigTask(cluster_node, node_repo, info, self.YUM_REPO_MANIFEST,
                                  id=node_repo.properties['name'],
                                  **puppet_manifest_args)
                task_list.append(task)

    def validate_model(self, plugin_api_context):
        return []