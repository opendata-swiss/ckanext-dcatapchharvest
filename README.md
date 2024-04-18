ckanext-dcatapchharvest
=======================

CKAN extension for DCAT-AP-CH harvesting for [opendata.swiss](https://opendata.swiss).

## Requirements

- CKAN 2.8+
- ckanext-dcat
- ckanext-fluent
- ckanext-scheming

## Installation

To install ckanext-dcatapchharvest:

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-dcatapchharvest Python package into your virtual environment:

     pip install ckanext-dcatapchharvest

3. Add `dcat_ch_rdf_harvester ogdch_dcat` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/production.ini`).

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

## Mapping datetime fields from RDF

DCAT-AP CH allows the following date/datetime datatypes for datetime fields:

- xsd:dateTime
- xsd:date
- xsd:gYearMonth
- xsd:gYear
- schema:Date     } only for temporals specified as schema:startDate and schema:endDate (deprecated)
- schema:DateTime }

Values in any of the xsd datatypes above are automatically parsed as ISO-compatible datetimes or dates by rdflib
when the graph is created (i.e. before the ckanext-dcat RDFParser has access to it.) This limits the validation
we can perform on the data as published by data publishers.

We only consider the parts of the date that are expected from the given data_type, e.g. the year of an xsd:gYear,
even if the month and day have been included in the datetime_value. If a datetime_value with data_type of 
xsd:dateTime or schema:DateTime does not contain time information, we discard it.

In general, if a date is given without time data, we map it as the earliest possible point in that date.

   xsd:date       "2020-03-05"   => "2020-03-05T00:00:00"  
   xsd:gYearMonth "2020-03"      => "2020-03-01T00:00:00"  
   xsd:gYear      "2020"         => "2020-01-01T00:00:00"  

Temporal end dates are a special case: they are mapped as the latest possible point in that date.

   xsd:date       "2020-03-05"   => "2020-03-05T23:59:59"  
   xsd:gYearMonth "2020-03"      => "2020-03-31T23:59:59"  
   xsd:gYear      "2020"         => "2020-12-31T23:59:59"  

If malformed datetime values can be parsed somehow as ISO-compatible datetimes or dates, this is done automatically
by rdflib. If not (e.g. "2020-15-35"), they are not mapped at all.

## Configuration options for the Swiss DCAT Harvester

When importing data that contains URIs from a test environment, the harvester can be configured
to overwrite those URIs with ones containing the current `ckan.site_url`. Add any test urls to
the CKAN config file, comma separated:

    ckanext.dcat_ch_rdf_harvester.test_env_urls = https://test.example.com,https://staging.example.com 

The Swiss DCAT Harvester inherits all configuration options from the DCAT RDF harvester. 
It has the following additional configuration options:

Exclude datasets from import: this will prevent the import of datasets with certain identifiers.

```
{"excluded_dataset_identifiers":["aaa@oevch", "fahrtprognose@oevch"]}
```

Exclude resource license from import: this prevents the import of datasets with certain resource 
license.

```
{"excluded_license":["NonCommercialWithPermission-CommercialWithPermission-ReferenceRequired"]}
```

Both configurations only work on the first import. Once imported the harvest 
source must be cleared in order to prevent the import.

