ckanext-dcatapchharvest
=======================

CKAN extension for DCAT-AP-CH harvesting for [opendata.swiss](https://opendata.swiss).

## Requirements

- CKAN 2.8+
- ckanext-scheming
- ckanext-fluent

## Installation

To install ckanext-dcatapchharvest:

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-dcatapchharvest Python package into your virtual environment:

     pip install ckanext-dcatapchharvest

3. Add ``dcat_ch_rdf_harvester and ogdch_dcat`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     sudo service apache2 reload

## Development Installation

To install ckanext-dcatapchharvest for development, activate your CKAN virtualenv and
do:

    git clone https://github.com/ogdch/ckanext-dcatapchharvest.git
    cd ckanext-switzerland
    python setup.py develop
    pip install -r dev-requirements.txt
    pip install -r requirements.txt

## Configuration options for the Swiss DCAT Harevster

The Swiss DCAT Harvester inherits all configuration options from the DCAT rdf harvester. 
Additionally the following additional configuration options:

Exclude datasets from import: this will prevent the import of datasets with ceratin identifiers.

```
{"excluded_dataset_identifiers":["aaa@oevch", "fahrtprognose@oevch"]}
```

Exclude resource rights from import: this prevent the import of datasets with certain resource 
rights.

```
{"excluded_rights":["NonCommercialWithPermission-CommercialWithPermission-ReferenceRequired"]}
```

Both configurations only works on the first import. Once imported the harvest 
source must be cleared in order to prevent the import.
