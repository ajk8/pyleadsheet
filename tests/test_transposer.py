import doctest
from pyleadsheet import transposer


def test_doctest():
    results = doctest.testmod(transposer)
    if results.failed:
        raise Exception(results)
