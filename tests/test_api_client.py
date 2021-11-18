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

        cls.oa = OrthancApiClient('http://localhost:10042', user='test', pwd='test')
        cls.oa.wait_started()

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["docker-compose", "down", "-v"], cwd=here/"docker-setup")

    def test_is_alive(self):
        self.assertTrue(self.oa.is_alive())

    def test_upload_valid_dicom_and_delete(self):
        self.oa.delete_all_content()
        self.assertEqual(0, len(self.oa.studies.get_all_ids()))

        instances_ids = self.oa.upload_file( here / "stimuli/CT_small.dcm")

        self.assertEqual('f689ddd2-662f8fe1-8b18180d-ec2a2cee-937917af', instances_ids[0])
        self.assertEqual(1, len(self.oa.studies.get_all_ids()))

        self.oa.delete_all_content()
        self.assertEqual(0, len(self.oa.studies.get_all_ids()))

    def test_upload_invalid_file(self):
        with self.assertRaises(api_exceptions.BadFileFormat):
            self.oa.upload_file( here / "__init__.py")   # __init__.py is not a valid DICOM file :-)

    def test_upload_invalid_file_while_ignoring_errors(self):
        self.oa.upload_file( here / "__init__.py", ignore_errors=True)   # __init__.py is not a valid DICOM file :-)
        # should not throw !

    def test_upload_valid_zip(self):
        instances_ids = self.oa.upload_file( here / "stimuli/CT_small.zip")

        self.assertEqual('f689ddd2-662f8fe1-8b18180d-ec2a2cee-937917af', instances_ids[0])

    def test_upload_folder(self):
        instances_ids = self.oa.upload_folder( here / "stimuli", skip_extensions=['.zip'])

        self.assertLessEqual(1, len(instances_ids))


    def test_upload_folder_ignore_errors(self):
        instances_ids = self.oa.upload_folder( here , skip_extensions=['.zip'], ignore_errors=True)  # here contains __init__.py which is invalid

        self.assertLessEqual(1, len(instances_ids))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    unittest.main()

