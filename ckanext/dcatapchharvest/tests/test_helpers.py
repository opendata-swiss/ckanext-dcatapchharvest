from ckanext.dcatapchharvest.harvest_helper import check_package_change


class TestHarvestHelpersUnit(object):
    def test_check_package_change_no_change(self):
        existing_package = {
            "modified": "2020-01-02T00:00:00",
            "resources": [
                {
                    "url": "http://example.org/resource-1",
                    "download_url": "http://example.org/resource-1/download",
                    "modified": "2020-01-02T00:00:00",
                },
            ],
        }
        dataset_dict = {
            "modified": "2020-01-02T00:00:00",
            "resources": [
                {
                    "url": "http://example.org/resource-1",
                    "download_url": "http://example.org/resource-1/download",
                    "modified": "2020-01-02T00:00:00",
                },
            ],
        }

        assert check_package_change(existing_package, dataset_dict) == (False, None)

    def test_check_package_change_new_modified_time(self):
        existing_package = {
            "modified": "2020-01-02T00:00:00",
        }
        dataset_dict = {
            "modified": "2020-01-02T12:00:00",
        }

        assert check_package_change(existing_package, dataset_dict) == (
            True,
            "dataset modified date changed: 2020-01-02T12:00:00",
        )

    def test_check_package_change_new_resource_modified_time(self):
        existing_package = {
            "resources": [
                {
                    "modified": "2020-01-02T00:00:00",
                },
            ],
        }
        dataset_dict = {
            "resources": [
                {
                    "modified": "2020-01-02T12:00:00",
                },
            ],
        }

        assert check_package_change(existing_package, dataset_dict) == (
            True,
            "resource modified date changed: 2020-01-02T12:00:00",
        )

    def test_check_package_change_new_url(self):
        existing_package = {
            "url": "http://example.org/landing",
        }
        dataset_dict = {
            "url": "http://example.org/new/landing",
        }

        assert check_package_change(existing_package, dataset_dict) == (
            True,
            "dataset url value changed from 'http://example.org/landing' to 'http://example.org/new/landing'",
        )

    def test_check_package_change_empty_new_url(self):
        existing_package = {
            "url": "http://example.org/landing",
        }
        dataset_dict = {
            "url": "",
        }

        assert check_package_change(existing_package, dataset_dict) == (
            True,
            "dataset url value changed from 'http://example.org/landing' to ''",
        )

    def test_check_package_change_new_resource_url(self):
        existing_package = {
            "resources": [
                {
                    "url": "http://example.org/resource-1",
                },
            ],
        }
        dataset_dict = {
            "resources": [
                {
                    "url": "http://example.org/new/resource-1",
                },
            ],
        }

        assert check_package_change(existing_package, dataset_dict) == (
            True,
            "resource access url changed: http://example.org/new/resource-1",
        )

    def test_check_package_change_new_resource_download_url(self):
        existing_package = {
            "resources": [
                {
                    "download_url": "http://example.org/resource-1/download",
                },
            ],
        }
        dataset_dict = {
            "resources": [
                {
                    "download_url": "http://example.org/new/resource-1/download",
                },
            ],
        }

        assert check_package_change(existing_package, dataset_dict) == (
            True,
            "resource download url changed: http://example.org/new/resource-1/download",
        )

    def test_check_package_change_different_resource_count(self):
        existing_package = {
            "resources": [
                {
                    "url": "http://example.org/resource-1",
                    "download_url": "http://example.org/resource-1/download",
                    "modified": "2020-01-02T00:00:00",
                },
                {
                    "url": "http://example.org/resource-2",
                    "download_url": "http://example.org/resource-2/download",
                    "modified": "2020-01-02T00:00:00",
                },
            ],
        }
        dataset_dict = {
            "resources": [
                {
                    "url": "http://example.org/resource-1",
                    "download_url": "http://example.org/resource-1/download",
                    "modified": "2020-01-02T00:00:00",
                },
            ],
        }

        assert check_package_change(existing_package, dataset_dict) == (
            True,
            "resource count changed: 1",
        )

    def test_check_package_change_multiple_resources_changed(self):
        """All the urls, download urls and modified dates of the resources
        have changed, but we should only get a message about the first
        resource that is different.
        """
        existing_package = {
            "resources": [
                {
                    "url": "http://example.org/resource-1",
                    "download_url": "http://example.org/resource-1/download",
                    "modified": "2020-01-02T00:00:00",
                },
                {
                    "url": "http://example.org/resource-2",
                    "download_url": "http://example.org/resource-2/download",
                    "modified": "2020-01-02T00:00:00",
                },
            ],
        }
        dataset_dict = {
            "resources": [
                {
                    "url": "http://example.org/new/resource-1",
                    "download_url": "http://example.org/new/resource-1/download",
                    "modified": "2020-01-02T12:00:00",
                },
                {
                    "url": "http://example.org/new/resource-2",
                    "download_url": "http://example.org/new/resource-2/download",
                    "modified": "2020-01-02T12:00:00",
                },
            ],
        }

        assert check_package_change(existing_package, dataset_dict) == (
            True,
            "resource access url changed: http://example.org/new/resource-1",
        )
