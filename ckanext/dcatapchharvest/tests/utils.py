import os


def get_file_contents(file_name):
    path = os.path.join(os.path.dirname(__file__),
                        'fixtures',
                        file_name)
    with open(path, 'r') as f:
        return f.read()

def get_dataset_extras(dataset):
    extras = {}
    for extra in dataset.get('extras'):
        extras[extra['key']] = extra['value']
    return extras
