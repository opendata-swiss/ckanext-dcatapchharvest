import os

import ckan.plugins as plugins
from ckanext.dcat.interfaces import IDCATURIGenerator
from ckanext.dcat.plugins import DCATPlugin

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class OgdchDcatPlugin(DCATPlugin):
    plugins.implements(IDCATURIGenerator, inherit=True)

    def after_show(self, context, data_dict):
        """
        Override after_show from ckanext_dcat as the set_titles() here
        destroyed our custom theme
        """
        pass
