from h_litp.core.extension import ModelExtension
from h_litp.core.litp_logging import LitpLogger
from h_litp.core.model_type import ItemType, Property

logger = LitpLogger('PkgMgmtRepoExtension')


class PkgMgmtRepoExtension(ModelExtension):
    def __init__(self):
        logger.trace.info('<PkgMgmtRepoExtension>')

    def define_property_types(self):
        return []

    def define_item_types(self):
        return [ItemType('repository',
                         extend_item='software-item',
                         item_description='Assure YUM repo',
                         name=Property('basic_string', prop_description='The YUM repo name', required=True),
                         url=Property('any_string', prop_description='The YUM repo path')
        )]
