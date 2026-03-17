import os

import ckan.plugins as plugins
from rdflib import URIRef

from ckanext.dcat.interfaces import IDCATURIGenerator
from ckanext.dcat.plugins import DCATPlugin

from . import dcat_helpers

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


class OgdchDcatPlugin(DCATPlugin):
    plugins.implements(IDCATURIGenerator, inherit=True)

    def dataset_uri(self, dataset_dict, default_uri):
        """
        Return the dataset URI for RDF serializations (make sure the URL matches
        the environment and that we use the permalink).
        """
        dataset_ref = URIRef(default_uri) if default_uri else None
        return dcat_helpers.dataset_uri(dataset_dict, dataset_ref)

    def resource_uri(self, resource_dict, default_uri):
        """
        Return the resource URI for RDF serializations (make sure the URL matches
        the environment).
        """
        distribution = URIRef(default_uri) if default_uri else None
        return dcat_helpers.resource_uri(resource_dict, distribution)

    def after_show(self, context, data_dict):
        """
        Override after_show from ckanext_dcat as the set_titles() here
        destroyed our custom theme
        """
        pass
