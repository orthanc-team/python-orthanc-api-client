import unittest

from orthanc_api_client import OrthancApiClient


class TestInstantiate(unittest.TestCase):

    def test_instantiate(self):
        # check it does not raise an exception
        OrthancApiClient('http://localhost:8042')


if __name__ == '__main__':
    unittest.main()

