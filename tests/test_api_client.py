import time
import unittest
import subprocess
import logging
from orthanc_api_client import OrthancApiClient, generate_test_dicom_file, ChangeType, ResourceType
import orthanc_api_client.exceptions as api_exceptions
import pathlib
import asyncio
import os

here = pathlib.Path(__file__).parent.resolve()



class TestApiClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        subprocess.run(["docker-compose", "down", "-v"], cwd=here/"docker-setup")
        subprocess.run(["docker-compose", "up", "--build", "-d"], cwd=here/"docker-setup")

        cls.oa = OrthancApiClient('http://localhost:10042', user='test', pwd='test')
        cls.oa.wait_started()

        cls.ob = OrthancApiClient('http://localhost:10043', user='test', pwd='test')
        cls.ob.wait_started()

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["docker-compose", "down", "-v"], cwd=here/"docker-setup")

    def test_is_alive(self):
        self.assertTrue(self.oa.is_alive())

    def test_api_token_ctor(self):
        # first retrieve the token through a special route implemented by a plugin (not safe ! don't run this experiment at home !)
        auth_token = self.ob.get_binary('/api-token').decode('utf-8')

        o = OrthancApiClient('http://localhost:10043', api_token=auth_token)
        r = o.get('/system')
        self.assertEqual(200, r.status_code)


    def test_upload_valid_dicom_and_delete(self):
        self.oa.delete_all_content()
        self.assertEqual(0, len(self.oa.studies.get_all_ids()))

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")

        self.assertEqual('f689ddd2-662f8fe1-8b18180d-ec2a2cee-937917af', instances_ids[0])
        self.assertEqual(1, len(self.oa.studies.get_all_ids()))

        self.oa.instances.delete(orthanc_id=instances_ids[0])
        self.assertEqual(0, len(self.oa.studies.get_all_ids()))

    def test_instances_get_tags(self):
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        tags = self.oa.instances.get_tags(instances_ids[0])

        self.assertEqual("1CT1", tags['PatientID'])
        self.assertEqual("CompressedSamples^CT1", tags['0010,0010'])
        self.assertEqual("O", tags['0010-0040'])
        self.assertEqual('072731', tags['InstanceCreationTime'])

    def test_studies_get_tags(self):
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])
        tags = self.oa.studies.get_tags(study_id)

        # study tags only contain study + patient module tags
        self.assertEqual("1CT1", tags['PatientID'])
        self.assertEqual("e+1", tags['StudyDescription'])
        self.assertEqual(None, tags['InstanceCreationTime'])

    def test_upload_invalid_file(self):
        with self.assertRaises(api_exceptions.BadFileFormat):
            self.oa.upload_file(here / "__init__.py")   # __init__.py is not a valid DICOM file :-)

    def test_upload_invalid_file_while_ignoring_errors(self):
        self.oa.upload_file(here / "__init__.py", ignore_errors=True)   # __init__.py is not a valid DICOM file :-)
        # should not throw !

    def test_upload_valid_zip(self):
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.zip")

        self.assertEqual('f689ddd2-662f8fe1-8b18180d-ec2a2cee-937917af', instances_ids[0])

    def test_upload_folder(self):
        self.oa.delete_all_content()
        instances_ids = self.oa.upload_folder(here / "stimuli", skip_extensions=['.zip'])

        self.assertLessEqual(1, len(instances_ids))
        self.oa.instances.delete(orthanc_ids=instances_ids)
        self.assertEqual(0, len(self.oa.studies.get_all_ids()))

    def test_upload_folder_ignore_errors(self):
        instances_ids = self.oa.upload_folder(here, skip_extensions=['.zip'], ignore_errors=True)  # here contains __init__.py which is invalid

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

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")

        instance_id = self.oa.instances.get_all_ids()[0]
        series_id = self.oa.series.get_all_ids()[0]
        study_id = self.oa.studies.get_all_ids()[0]

        self.assertEqual(instance_id, instances_ids[0])
        self.assertEqual(series_id, self.oa.instances.get_parent_series_id(instance_id))
        self.assertEqual(study_id, self.oa.instances.get_parent_study_id(instance_id))

    def test_get_ordered_slices(self):
        self.oa.delete_all_content()
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")

        instance_id = self.oa.instances.get_all_ids()[0]
        series_id = self.oa.series.get_all_ids()[0]

        # we trust orthanc API to return the ordered slices correctly, so this test is very "basic" and just check we are parsing the response correctly !!
        ordered_instances_ids = self.oa.series.get_ordered_instances_ids(orthanc_id=series_id)
        self.assertEqual(1, len(ordered_instances_ids))
        self.assertEqual(instance_id, ordered_instances_ids[0])

        middle_instance_id = self.oa.series.get_middle_instance_id(orthanc_id=series_id)
        self.assertEqual(instance_id, middle_instance_id)

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

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")

        content = b'123456789'
        self.oa.instances.set_attachment(
            orthanc_id=instances_ids[0],
            attachment_name=1025,
            content = content,
            content_type = 'application/octet-stream'
            )

        content_readback = self.oa.instances.get_attachment(
            orthanc_id=instances_ids[0],
            attachment_name=1025
        )

        self.assertEqual(content, content_readback)


    def test_attachments_with_revision(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")

        content = b'123456789'
        self.oa.instances.set_attachment(
            orthanc_id=instances_ids[0],
            attachment_name=1025,
            content=content,
            content_type='application/octet-stream'
            )

        # get current revision
        content_readback, revision = self.oa.instances.get_attachment_with_revision(
            orthanc_id=instances_ids[0],
            attachment_name=1025
        )

        self.assertEqual(content, content_readback)

        updated_content = b'abcdefg'

        # update if match current revision
        self.oa.instances.set_attachment(
            orthanc_id=instances_ids[0],
            attachment_name=1025,
            content=updated_content,
            content_type='application/octet-stream',
            match_revision=revision
            )

        # tye to update if match another revision -> fails
        with self.assertRaises(api_exceptions.HttpError):
            self.oa.instances.set_attachment(
                orthanc_id=instances_ids[0],
                attachment_name=1025,
                content=updated_content,
                content_type='application/octet-stream',
                match_revision='"1-bad-checksum"'
                )

        # get current revision
        content_readback, revision = self.oa.instances.get_attachment_with_revision(
            orthanc_id=instances_ids[0],
            attachment_name=1025
        )

        self.assertEqual(updated_content, content_readback)

    def test_metadata_with_revision(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")

        # try to read a metadata that does not exist
        value = self.oa.instances.get_metadata(
            instances_ids[0],
            metadata_name=1024,
            default_value=None
        )
        self.assertEqual(None, value)

        content = b'123456789'
        self.oa.instances.set_metadata(
            orthanc_id=instances_ids[0],
            metadata_name=1025,
            content=content
            )

        # get current revision
        content_readback, revision = self.oa.instances.get_metadata_with_revision(
            orthanc_id=instances_ids[0],
            metadata_name=1025
        )

        self.assertEqual(content, content_readback)

        updated_content = b'abcdefg'

        # update if match current revision
        self.oa.instances.set_metadata(
            orthanc_id=instances_ids[0],
            metadata_name=1025,
            content=updated_content,
            match_revision=revision
            )

        # tye to update if match another revision -> fails
        with self.assertRaises(api_exceptions.HttpError):
            self.oa.instances.set_metadata(
                orthanc_id=instances_ids[0],
                metadata_name=1025,
                content=updated_content,
                match_revision='"1-bad-checksum"'
                )

        # get current revision
        content_readback, revision = self.oa.instances.get_metadata_with_revision(
            orthanc_id=instances_ids[0],
            metadata_name=1025
        )

        self.assertEqual(updated_content, content_readback)


    def test_changes(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")

        changes, seq_id, done = self.oa.get_changes()

        self.assertEqual(ChangeType.NEW_INSTANCE, changes[0].change_type)
        self.assertEqual(ResourceType.INSTANCE, changes[0].resource_type)
        self.assertEqual(instances_ids[0], changes[0].resource_id)

        changes, seq_id, done = self.oa.get_changes(since=seq_id)
        self.assertEqual(0, len(changes))
        self.assertTrue(done)


    def test_anonymize_study(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        # default anonymize
        anon_study_id = self.oa.studies.anonymize(
            orthanc_id=study_id,
            keep_tags=['PatientName'],
            replace_tags={
                'PatientID': 'ANON'
            },
            force=True,
            delete_original=False
        )

        self.assertEqual(self.oa.studies.get_tags(study_id)['PatientName'], self.oa.studies.get_tags(anon_study_id)['PatientName'])
        self.assertNotEqual('ANON', self.oa.studies.get_tags(anon_study_id)['PatientName'])

        instances_ids = self.oa.upload_folder(here / "stimuli", skip_extensions=['.zip'])

    def test_asyncio(self):
        self.oa.delete_all_content()

        dicoms = []

        for i in range(1, 10):
            dicoms.append(generate_test_dicom_file(width=3200, height=3200, StudyInstanceUID='1.2.3'))

        ##### upload synchronous
        s = time.perf_counter()
        # upload files one by one
        instances_ids = []
        for dicom in dicoms:
            instances_ids.extend(self.oa.upload(buffer=dicom))
        elapsed = time.perf_counter() - s

        print(f"synchronous upload took: {elapsed:0.3f} seconds")

        self.oa.delete_all_content()

        ##### upload asynchronous
        s = time.perf_counter()
        # upload files one by one
        future_instance_ids = []
        for dicom in dicoms:
            future_instance_ids.append(asyncio.to_thread(self.oa.upload, buffer=dicom))
        result_list = asyncio.get_event_loop().run_until_complete(asyncio.gather(*future_instance_ids))
        instances_ids = [i for r in result_list for i in r]
        elapsed = time.perf_counter() - s

        print(f"asynchronous upload took: {elapsed:0.3f} seconds")




if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    unittest.main()

