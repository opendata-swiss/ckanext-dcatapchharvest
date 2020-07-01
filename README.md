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
