import unittest
import subprocess
import logging
from orthanc_api_client import OrthancApiClient
import orthanc_api_client.exceptions as api_exceptions
import pathlib
import os

here = pathlib.Path(__file__).parent.resolve()



class TestApiClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        subprocess.run(["docker-compose", "down", "-v"], cwd=here/"docker-setup")
        subprocess.run(["docker-compose", "up", "-d"], cwd=here/"docker-setup")

        cls.orthanc_a = OrthancApiClient('http://localhost:10042', user='test', pwd='test')
        cls.orthanc_a.wait_started()

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["docker-compose", "down", "-v"], cwd=here/"docker-setup")

    def test_is_alive(self):
        self.assertTrue(self.orthanc_a.is_alive())

    def test_upload_valid_dicom(self):
        instances_ids = self.orthanc_a.upload_file( here / "stimuli/CT_small.dcm")

        self.assertEqual('f689ddd2-662f8fe1-8b18180d-ec2a2cee-937917af', instances_ids[0])

    def test_upload_invalid_file(self):
        with self.assertRaises(api_exceptions.BadFileFormat):
            self.orthanc_a.upload_file( here / "__init__.py")   # __init__.py is not a valid DICOM file :-)

    def test_upload_valid_zip(self):
        instances_ids = self.orthanc_a.upload_file( here / "stimuli/CT_small.zip")

        self.assertEqual('f689ddd2-662f8fe1-8b18180d-ec2a2cee-937917af', instances_ids[0])

    def test_upload_folder(self):
        instances_ids = self.orthanc_a.upload_folder( here / "stimuli", skip_extensions = ['.zip'])

        self.assertGreaterEqual(1, len(instances_ids))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    unittest.main()

