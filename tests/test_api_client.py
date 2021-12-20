import unittest
import subprocess
import logging
from orthanc_api_client import OrthancApiClient, generate_test_dicom_file, ChangeType, ResourceType
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

        cls.ob = OrthancApiClient('http://localhost:10043', user='test', pwd='test')
        cls.ob.wait_started()

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

    def test_generate_and_upload_test_file_find_study(self):
        self.oa.delete_all_content()

        study_id = self.oa.studies.find('1.2.3')
        self.assertIsNone(study_id)

        dicom = generate_test_dicom_file(width=32, height=32, StudyInstanceUID='1.2.3')

        instances_ids = self.oa.upload(dicom)
        study_id = self.oa.studies.find('1.2.3')

        self.assertLessEqual(1, len(instances_ids))
        self.assertIsNotNone(study_id)

    def test_get_parents(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file( here / "stimuli/CT_small.dcm")

        instance_id = self.oa.instances.get_all_ids()[0]
        series_id = self.oa.series.get_all_ids()[0]
        study_id = self.oa.studies.get_all_ids()[0]

        self.assertEqual(instance_id, instances_ids[0])
        self.assertEqual(series_id, self.oa.instances.get_parent_series_id(instance_id))
        self.assertEqual(study_id, self.oa.instances.get_parent_study_id(instance_id))

    def test_stow_rs(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()

        dicom = generate_test_dicom_file(width=33, height=33, StudyInstanceUID='1.2.3')
        instances_ids = self.oa.upload(dicom)
        dicom = generate_test_dicom_file(width=33, height=33, StudyInstanceUID='1.2.3')
        instances_ids.extend(self.oa.upload(dicom))

        study_id = self.oa.studies.find('1.2.3')

        self.oa.dicomweb_servers.send('orthanc-b', study_id)

        study_id = self.ob.studies.find('1.2.3')
        self.assertIsNotNone(study_id)


    def test_attachments(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file( here / "stimuli/CT_small.dcm")

        content = b'123456789'
        self.oa.instances.set_attachment(
            id=instances_ids[0],
            attachment_name=1025,
            content = content,
            content_type = 'application/octet-stream'
            )

        content_readback = self.oa.instances.get_attachment(
            id=instances_ids[0],
            attachment_name=1025
        )

        self.assertEqual(content, content_readback)


    def test_attachments_with_revision(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file( here / "stimuli/CT_small.dcm")

        content = b'123456789'
        self.oa.instances.set_attachment(
            id=instances_ids[0],
            attachment_name=1025,
            content = content,
            content_type = 'application/octet-stream'
            )

        # get current revision
        content_readback, revision = self.oa.instances.get_attachment_with_revision(
            id=instances_ids[0],
            attachment_name=1025
        )

        self.assertEqual(content, content_readback)

        updated_content = b'abcdefg'

        # update if match current revision
        self.oa.instances.set_attachment(
            id=instances_ids[0],
            attachment_name=1025,
            content = updated_content,
            content_type = 'application/octet-stream',
            match_revision = revision
            )

        # tye to update if match another revision -> fails
        with self.assertRaises(api_exceptions.HttpError):
            self.oa.instances.set_attachment(
                id=instances_ids[0],
                attachment_name=1025,
                content = updated_content,
                content_type = 'application/octet-stream',
                match_revision = '"1-bad-checksum"'
                )

        # get current revision
        content_readback, revision = self.oa.instances.get_attachment_with_revision(
            id=instances_ids[0],
            attachment_name=1025
        )

        self.assertEqual(updated_content, content_readback)

    def test_metadata_with_revision(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file( here / "stimuli/CT_small.dcm")

        content = b'123456789'
        self.oa.instances.set_metadata(
            id=instances_ids[0],
            metadata_name=1025,
            content = content
            )

        # get current revision
        content_readback, revision = self.oa.instances.get_metadata_with_revision(
            id=instances_ids[0],
            metadata_name=1025
        )

        self.assertEqual(content, content_readback)

        updated_content = b'abcdefg'

        # update if match current revision
        self.oa.instances.set_metadata(
            id=instances_ids[0],
            metadata_name=1025,
            content = updated_content,
            match_revision = revision
            )

        # tye to update if match another revision -> fails
        with self.assertRaises(api_exceptions.HttpError):
            self.oa.instances.set_metadata(
                id=instances_ids[0],
                metadata_name=1025,
                content = updated_content,
                match_revision = '"1-bad-checksum"'
                )

        # get current revision
        content_readback, revision = self.oa.instances.get_metadata_with_revision(
            id=instances_ids[0],
            metadata_name=1025
        )

        self.assertEqual(updated_content, content_readback)


    def test_changes(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file( here / "stimuli/CT_small.dcm")

        changes, seq_id, done = self.oa.get_changes()

        self.assertEqual(ChangeType.NEW_INSTANCE, changes[0].change_type)
        self.assertEqual(ChangeType.INSTANCE, changes[0].resource_type)
        self.assertEqual(instances[0], changes[0].resource_id)

        changes, seq_id, done = self.oa.get_changes(since=seq_id)
        self.assertEqual(0, len(changes))
        self.assertTrue(done)



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    unittest.main()

