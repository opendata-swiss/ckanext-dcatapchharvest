import iribaker
from urlparse import urlparse


def uri_to_iri(uri):
    """
    convert URI to IRI (used for RDF)
    this function also validates the URI and throws a ValueError if the
    provided URI is invalid
    """
    result = urlparse(uri)
    if not result.scheme or not result.netloc or result.netloc == '-':
        raise ValueError("Provided URI does not have a valid schema or netloc")

    try:
        iri = iribaker.to_iri(uri)
        return iri
    except:
        raise ValueError("Provided URI can't be converted to IRI")


def get_langs():
    language_priorities = ['en', 'de', 'fr', 'it']
    return language_priorities
