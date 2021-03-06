import time
import unittest
import subprocess
import logging
import datetime
from orthanc_api_client import OrthancApiClient, generate_test_dicom_file, ChangeType, ResourceType, Study, Job, JobStatus, JobType
from orthanc_api_client.helpers import to_dicom_date, wait_until
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

        cls.oc = OrthancApiClient('http://localhost:10044', user='test', pwd='test')
        cls.oc.wait_started()

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

        # make sure deleting an already deleted resource does not throw if ignore_errors is true
        self.oa.instances.delete(orthanc_id=instances_ids[0], ignore_errors=True)

        with self.assertRaises(api_exceptions.ResourceNotFound):
            self.oa.instances.delete(orthanc_id=instances_ids[0], ignore_errors=False)

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

        self.assertEqual("1CT1", tags['PatientID'])
        self.assertEqual("e+1", tags['StudyDescription'])

    def test_study(self):
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        study = self.oa.studies.get(study_id)
        self.assertEqual("1CT1", study.patient_main_dicom_tags.get('PatientID'))
        self.assertEqual("e+1", study.main_dicom_tags.get('StudyDescription'))
        self.assertEqual('1.3.6.1.4.1.5962.1.2.1.20040119072730.12322', study.dicom_id)
        self.assertEqual('8a8cf898-ca27c490-d0c7058c-929d0581-2bbf104d', study.orthanc_id)

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

        study_id = self.oa.studies.lookup('1.2.3')
        self.assertIsNone(study_id)

        dicom = generate_test_dicom_file(width=32, height=32, tags={'StudyInstanceUID': '1.2.3', 'StudyDate': to_dicom_date(datetime.date.today())})
        instances_ids = self.oa.upload(dicom)
        study_id = self.oa.studies.lookup('1.2.3')

        self.assertLessEqual(1, len(instances_ids))
        self.assertIsNotNone(study_id)

    def test_daily_stats(self):
        self.oa.delete_all_content()

        self.oa.upload(generate_test_dicom_file(width=32, height=32, tags={'StudyInstanceUID': '1.2.3', 'SeriesInstanceUID': '4.5.6', 'StudyDate': '20220205'}))
        self.oa.upload(generate_test_dicom_file(width=32, height=32, tags={'StudyInstanceUID': '1.2.3', 'SeriesInstanceUID': '4.5.7', 'StudyDate': '20220205'}))
        self.oa.upload(generate_test_dicom_file(width=32, height=32, tags={'StudyInstanceUID': '1.2.4', 'SeriesInstanceUID': '4.5.8', 'StudyDate': '20220206'}))
        self.oa.upload(generate_test_dicom_file(width=32, height=32, tags={'StudyInstanceUID': '1.2.4', 'SeriesInstanceUID': '4.5.8', 'StudyDate': '20220206'}))
        self.oa.upload(generate_test_dicom_file(width=32, height=32, tags={'StudyInstanceUID': '1.2.4', 'SeriesInstanceUID': '4.5.8', 'StudyDate': '20220206'}))

        self.oa.studies.print_daily_stats(from_date=datetime.date(2022, 2, 4), to_date=datetime.date(2022, 2, 8))
        self.oa.series.print_daily_stats(from_date=datetime.date(2022, 2, 4), to_date=datetime.date(2022, 2, 8))
        self.oa.instances.print_daily_stats(from_date=datetime.date(2022, 2, 4), to_date=datetime.date(2022, 2, 8))

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

        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids = self.oa.upload(dicom)
        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids.extend(self.oa.upload(dicom))

        study_id = self.oa.studies.lookup('1.2.3')

        job = self.oa.dicomweb_servers.send_asynchronous('orthanc-b', study_id)
        self.assertEqual(JobType.DICOM_WEB_STOW_CLIENT, job.info.type)
        wait_until(job.is_complete, 5)
        self.assertEqual(JobStatus.SUCCESS, job.refresh().info.status)

        study_id = self.ob.studies.lookup('1.2.3')
        self.assertIsNotNone(study_id)

    def test_modalities_send(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()

        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids = self.oa.upload(dicom)
        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids.extend(self.oa.upload(dicom))

        study_id = self.oa.studies.lookup('1.2.3')

        self.oa.modalities.send('orthanc-b', study_id)

        study_id = self.ob.studies.lookup('1.2.3')
        self.assertIsNotNone(study_id)

    def test_modalities_move(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()
        self.oc.delete_all_content()

        # upload a file to B
        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3', 'SeriesInstanceUID': '4.5.6', 'SOPInstanceUID': '7.8.9'})
        instances_ids = self.ob.upload(dicom)
        self.assertIsNotNone(self.ob.studies.lookup('1.2.3'))
        self.assertIsNotNone(self.ob.series.lookup('4.5.6'))
        self.assertIsNotNone(self.ob.instances.lookup('7.8.9'))

        #request C to move it from B to A
        self.oc.modalities.move_study(from_modality='orthanc-b', dicom_id='1.2.3', to_modality_aet='ORTHANCA')
        self.assertIsNotNone(1, self.oa.studies.lookup('1.2.3'))
        self.oa.delete_all_content()

        self.oc.modalities.move_series(from_modality='orthanc-b', dicom_id='4.5.6', study_dicom_id='1.2.3', to_modality_aet='ORTHANCA')
        self.assertIsNotNone(self.oa.series.lookup('4.5.6'))
        self.oa.delete_all_content()

        self.oc.modalities.move_instance(from_modality='orthanc-b', dicom_id='7.8.9', series_dicom_id='4.5.6', study_dicom_id='1.2.3', to_modality_aet='ORTHANCA')
        self.assertIsNotNone(self.oa.instances.lookup('7.8.9'))
        self.oa.delete_all_content()


        #request A to move it from B to A (retrieve)
        self.oa.modalities.move_study(from_modality='orthanc-b', dicom_id='1.2.3')
        self.assertIsNotNone(1, self.oa.studies.lookup('1.2.3'))
        self.oa.delete_all_content()

        self.oa.modalities.move_series(from_modality='orthanc-b', dicom_id='4.5.6', study_dicom_id='1.2.3')
        self.assertIsNotNone(self.oa.series.lookup('4.5.6'))
        self.oa.delete_all_content()

        self.oa.modalities.move_instance(from_modality='orthanc-b', dicom_id='7.8.9', series_dicom_id='4.5.6', study_dicom_id='1.2.3')
        self.assertIsNotNone(self.oa.instances.lookup('7.8.9'))
        self.oa.delete_all_content()

    def test_find_worklist(self):

        worklists = self.oa.modalities.find_worklist(
            modality='orthanc-b',
            query={
                'PatientID': "",
                "StudyInstanceUID": ""
            }
        )
        self.assertEqual(1, len(worklists))
        self.assertEqual('1.2.3.4', worklists[0]['StudyInstanceUID'])

    def test_transfers_send_study(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()

        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids = self.oa.upload(dicom)
        study_id = self.oa.studies.lookup('1.2.3')

        job = self.oa.transfers.send('orthanc-b', resources_ids=study_id, resource_type=ResourceType.STUDY, compress=False)

        self.assertEqual(JobType.PUSH_TRANSFER, job.info.type)
        wait_until(job.is_complete, 5)

        study_id = self.ob.studies.lookup('1.2.3')
        self.assertIsNotNone(study_id)

    def test_transfers_send_instances(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()

        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids = self.oa.upload(dicom)

        job = self.oa.transfers.send('orthanc-b', resources_ids=instances_ids, resource_type=ResourceType.INSTANCE, compress=True)

        self.assertEqual(JobType.PUSH_TRANSFER, job.info.type)
        wait_until(job.is_complete, 5)

        study_id = self.ob.studies.lookup('1.2.3')
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

    def test_modify_series_instance_by_instance(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        series_id = self.oa.instances.get_parent_series_id(instances_ids[0])

        original_tags = self.oa.series.get_tags(series_id)

        # default anonymize
        modified_series_id = self.oa.series.modify_instance_by_instance(
            orthanc_id=series_id,
            remove_tags=['InstitutionName'],
            replace_tags={
                'PatientID': 'modified-id',
                'PatientName': 'modified-name',
                'StudyInstanceUID': original_tags['StudyInstanceUID'],
                'SeriesInstanceUID': original_tags['SeriesInstanceUID'],
            },
            delete_original=True
        )

        modified_tags = self.oa.series.get_tags(modified_series_id)

        self.assertEqual(original_tags['StudyInstanceUID'], modified_tags['StudyInstanceUID'])
        self.assertEqual(original_tags['SeriesInstanceUID'], modified_tags['SeriesInstanceUID'])
        self.assertEqual('modified-id', modified_tags['PatientID'])

    def test_modify_study_instance_by_instance(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        original_tags = self.oa.studies.get_tags(study_id)

        # default anonymize
        modified_study_id = self.oa.studies.modify_instance_by_instance(
            orthanc_id=study_id,
            remove_tags=['InstitutionName'],
            replace_tags={
                'PatientID': 'modified-id',
                'PatientName': 'modified-name',
                'StudyInstanceUID': original_tags['StudyInstanceUID'],
                'SeriesInstanceUID': original_tags['SeriesInstanceUID'],
            },
            delete_original=True
        )

        modified_tags = self.oa.studies.get_tags(modified_study_id)

        self.assertEqual(original_tags['StudyInstanceUID'], modified_tags['StudyInstanceUID'])
        self.assertEqual(original_tags['SeriesInstanceUID'], modified_tags['SeriesInstanceUID'])
        self.assertEqual('modified-id', modified_tags['PatientID'])

    def test_modify_series(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        series_id = self.oa.instances.get_parent_series_id(instances_ids[0])

        original_tags = self.oa.series.get_tags(series_id)

        # default anonymize
        modified_series_id = self.oa.series.modify(
            orthanc_id=series_id,
            remove_tags=['InstitutionName'],
            replace_tags={
                'SeriesDate': '20220208'
            },
            delete_original=False
        )

        modified_tags = self.oa.series.get_tags(modified_series_id)

        self.assertFalse('InstitutionName' in modified_tags)
        self.assertEqual('20220208', modified_tags['SeriesDate'])

    def test_modify_study(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        original_tags = self.oa.studies.get_tags(study_id)

        # default anonymize
        modified_study_id = self.oa.studies.modify(
            orthanc_id=study_id,
            remove_tags=['InstitutionName'],
            replace_tags={
                'StudyInstanceUID': '1.2.3.4'
            },
            delete_original=False,
            force=True
        )

        modified_tags = self.oa.studies.get_tags(modified_study_id)

        self.assertFalse('InstitutionName' in modified_tags)
        self.assertEqual('1.2.3.4', modified_tags['StudyInstanceUID'])

    def test_asyncio(self):
        self.oa.delete_all_content()

        dicoms = []

        for i in range(1, 10):
            dicoms.append(generate_test_dicom_file(width=3200, height=3200, tags={'StudyInstanceUID': '1.2.3'}))

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

    def test_query_study(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        remote_studies = self.ob.modalities.query_studies(
            from_modality='orthanc-a',
            query={
                'PatientID': '1C*',
                'StudyDescription': ''
            }
        )

        self.assertEqual(1, len(remote_studies))
        self.assertEqual('1.3.6.1.4.1.5962.1.2.1.20040119072730.12322', remote_studies[0].dicom_id)
        self.assertEqual('orthanc-a', remote_studies[0].remote_modality_id)
        self.assertEqual("e+1", remote_studies[0].tags.get('StudyDescription'))

        self.ob.modalities.retrieve_study(
            from_modality=remote_studies[0].remote_modality_id,
            dicom_id=remote_studies[0].dicom_id
        )

        self.assertEqual(study_id, self.ob.studies.lookup(dicom_id='1.3.6.1.4.1.5962.1.2.1.20040119072730.12322'))

    def test_query_series_instances(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")

        remote_series = self.ob.modalities.query_series(
            from_modality='orthanc-a',
            query={
                'PatientID': '1C*',
                'StudyDescription': ''
            }
        )

        self.assertEqual(1, len(remote_series))
        self.assertEqual('1.3.6.1.4.1.5962.1.3.1.1.20040119072730.12322', remote_series[0].dicom_id)
        self.assertEqual('1.3.6.1.4.1.5962.1.2.1.20040119072730.12322', remote_series[0].tags.get('StudyInstanceUID'))
        self.assertEqual('orthanc-a', remote_series[0].remote_modality_id)
        self.assertEqual("e+1", remote_series[0].tags.get('StudyDescription'))

        remote_instances = self.ob.modalities.query_instances(
            from_modality='orthanc-a',
            query={
                'PatientID': '1C*',
                'StudyDescription': ''
            }
        )

        self.assertEqual(1, len(remote_instances))
        self.assertEqual('1.3.6.1.4.1.5962.1.1.1.1.1.20040119072730.12322', remote_instances[0].dicom_id)
        self.assertEqual('1.3.6.1.4.1.5962.1.2.1.20040119072730.12322', remote_instances[0].tags.get('StudyInstanceUID'))
        self.assertEqual('orthanc-a', remote_instances[0].remote_modality_id)
        self.assertEqual("e+1", remote_instances[0].tags.get('StudyDescription'))

    def test_find_study(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        studies = self.oa.studies.find(
            query={
                'PatientID': '1C*',
                'StudyDescription': ''
            }
        )

        self.assertEqual(1, len(studies))
        self.assertEqual('1.3.6.1.4.1.5962.1.2.1.20040119072730.12322', studies[0].dicom_id)
        self.assertEqual("e+1", studies[0].main_dicom_tags.get('StudyDescription'))

    def test_jobs(self):
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.zip")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        # create an async download job
        r = self.oa.post(
            endpoint=f"studies/{study_id}/archive",
            json={
                'Asynchronous': True
            })
        job_id = r.json()['ID']

        job = self.oa.jobs.get(orthanc_id=job_id)
        self.assertEqual(JobType.ARCHIVE, job.info.type)
        self.assertEqual(1, job.info.content.get('InstancesCount'))


    def test_merge_study(self):
        self.oa.delete_all_content()

        dicom1 = generate_test_dicom_file(width=32, height=32, tags={'StudyInstanceUID': '1', 'PatientID': '1', 'PatientName': 'A'})
        self.oa.upload(dicom1)
        dicom2 = generate_test_dicom_file(width=32, height=32, tags={'StudyInstanceUID': '2', 'PatientID': '2', 'PatientName': 'B', 'SeriesInstanceUID': '2.2'})
        self.oa.upload(dicom2)
        study_id = self.oa.studies.lookup('1')
        series_id = self.oa.series.lookup('2.2')

        r = self.oa.studies.merge(
            target_study_id=study_id,
            source_series_id=series_id,
            keep_source=False
        )

        self.assertEqual(1, len(self.oa.studies.get_all_ids()))
        self.assertEqual(2, len(self.oa.series.get_all_ids()))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    unittest.main()

