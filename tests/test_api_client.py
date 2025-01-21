import time
import unittest
import subprocess
import logging
import datetime
import uuid

from orthanc_api_client import OrthancApiClient, generate_test_dicom_file, ChangeType, ResourceType, Study, Job, JobStatus, JobType, InstancesSet, LabelsConstraint, LogLevel, RemoteJob, RetrieveMethod
from orthanc_api_client.helpers import *
import orthanc_api_client.exceptions as api_exceptions
import pathlib
import asyncio
import tempfile
import shutil
import os

here = pathlib.Path(__file__).parent.resolve()



class TestApiClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        subprocess.run(["docker", "compose", "down", "-v"], cwd=here/"docker-setup")
        subprocess.run(["docker", "compose", "up", "--build", "-d"], cwd=here/"docker-setup")

        cls.oa = OrthancApiClient('http://localhost:10042', user='test', pwd='test')
        cls.oa.wait_started()

        cls.ob = OrthancApiClient('http://localhost:10043', user='test', pwd='test')
        cls.ob.wait_started()

        cls.oc = OrthancApiClient('http://localhost:10044', user='test', pwd='test')
        cls.oc.wait_started()

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["docker", "compose", "down", "-v"], cwd=here/"docker-setup")

    def test_is_alive(self):
        self.assertTrue(self.oa.is_alive())

    def test_api_token_ctor(self):
        # first retrieve the token through a special route implemented by a plugin (not safe ! don't run this experiment at home !)
        auth_token = self.ob.get_binary('api-token').decode('utf-8')

        o = OrthancApiClient('http://localhost:10043', api_token=auth_token)
        r = o.get('system')
        self.assertEqual(200, r.status_code)

    def test_upload_valid_dicom_and_delete(self):
        self.oa.delete_all_content()
        self.assertEqual(0, len(self.oa.studies.get_all_ids()))

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")

        self.assertEqual('f689ddd2-662f8fe1-8b18180d-ec2a2cee-937917af', instances_ids[0])
        self.assertEqual(1, len(self.oa.studies.get_all_ids()))
        self.assertTrue(self.oa.instances.exists(instances_ids[0]))

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

        instance_tags = self.oa.studies.get_first_instance_tags(study_id)
        self.assertEqual("19970430", instance_tags['ContentDate'])

        modalities = self.oa.studies.get_modalities(study_id)
        self.assertEqual(["CT"], list(modalities))

    def test_patients_get_tags(self):
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        patient_id = self.oa.instances.get_parent_patient_id(instances_ids[0])
        tags = self.oa.patients.get_tags(patient_id)

        self.assertEqual("1CT1", tags['PatientID'])
        self.assertEqual("CompressedSamples^CT1", tags['PatientName'])

        instance_tags = self.oa.patients.get_first_instance_tags(patient_id)
        self.assertEqual("19970430", instance_tags['ContentDate'])

        modalities = self.oa.patients.get_modalities(patient_id)
        self.assertEqual(["CT"], list(modalities))

    def test_patient(self):
        self.oa.delete_all_content()
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        patient_id = self.oa.instances.get_parent_patient_id(instances_ids[0])

        patient = self.oa.patients.get(patient_id)
        self.assertEqual("1CT1", patient.main_dicom_tags.get('PatientID'))
        self.assertEqual("CompressedSamples^CT1", patient.main_dicom_tags.get('PatientName'))
        self.assertEqual(1, patient.statistics.instances_count)
        self.assertEqual(1, self.oa.get_statistics().patients_count)
        self.assertEqual(patient.statistics.disk_size, self.oa.get_statistics().total_disk_size)
        self.assertEqual(datetime.date.today(), patient.last_update.date())

        with tempfile.NamedTemporaryFile() as file:
            self.assertTrue(os.path.getsize(file.name) == 0)
            self.oa.patients.download_archive(patient_id, file.name)
            self.assertTrue(os.path.exists(file.name))
            self.assertTrue(os.path.getsize(file.name) > 0)

        with tempfile.NamedTemporaryFile() as file:
            self.assertTrue(os.path.getsize(file.name) == 0)
            self.oa.patients.download_media(patient_id, file.name)
            self.assertTrue(os.path.exists(file.name))
            self.assertTrue(os.path.getsize(file.name) > 0)


    def test_study(self):
        self.oa.delete_all_content()
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        study = self.oa.studies.get(study_id)
        self.assertEqual("1CT1", study.patient_main_dicom_tags.get('PatientID'))
        self.assertEqual("e+1", study.main_dicom_tags.get('StudyDescription'))
        self.assertEqual('1.3.6.1.4.1.5962.1.2.1.20040119072730.12322', study.dicom_id)
        self.assertEqual('8a8cf898-ca27c490-d0c7058c-929d0581-2bbf104d', study.orthanc_id)
        self.assertEqual(1, study.statistics.instances_count)
        self.assertEqual(1, self.oa.get_statistics().instances_count)
        self.assertEqual(study.statistics.instances_count, self.oa.get_statistics().instances_count)
        self.assertEqual(datetime.date.today(), study.last_update.date())

        with tempfile.NamedTemporaryFile() as file:
            self.assertTrue(os.path.getsize(file.name) == 0)
            self.oa.studies.download_archive(study_id, file.name)
            self.assertTrue(os.path.exists(file.name))
            self.assertTrue(os.path.getsize(file.name) > 0)

        with tempfile.NamedTemporaryFile() as file:
            self.assertTrue(os.path.getsize(file.name) == 0)
            self.oa.studies.download_media(study_id, file.name)
            self.assertTrue(os.path.exists(file.name))
            self.assertTrue(os.path.getsize(file.name) > 0)

    def test_series(self):
        self.oa.delete_all_content()
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        series_id = self.oa.instances.get_parent_series_id(instances_ids[0])

        series = self.oa.series.get(series_id)
        self.assertEqual("CT", series.main_dicom_tags.get('Modality'))
        self.assertEqual('1.3.6.1.4.1.5962.1.3.1.1.20040119072730.12322', series.dicom_id)
        self.assertEqual('93034833-163e42c3-bc9a428b-194620cf-2c5799e5', series.orthanc_id)
        self.assertEqual(1, series.statistics.instances_count)
        self.assertEqual(1, self.oa.get_statistics().instances_count)
        self.assertEqual(1, self.oa.get_statistics().series_count)
        self.assertEqual(series.statistics.disk_size, self.oa.get_statistics().total_disk_size)

        study = series.study
        self.assertEqual("1CT1", study.patient_main_dicom_tags.get('PatientID'))
        self.assertEqual("e+1", study.main_dicom_tags.get('StudyDescription'))
        self.assertEqual('1.3.6.1.4.1.5962.1.2.1.20040119072730.12322', study.dicom_id)
        self.assertEqual('8a8cf898-ca27c490-d0c7058c-929d0581-2bbf104d', study.orthanc_id)

    def test_instance(self):
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        instance = self.oa.instances.get(instances_ids[0])

        self.assertEqual("113008", instance.tags.get('ContentTime'))
        self.assertEqual("1.3.6.1.4.1.5962.1.2.1.20040119072730.12322", instance.tags.get('StudyInstanceUID'))
        self.assertEqual('1.3.6.1.4.1.5962.1.1.1.1.1.20040119072730.12322', instance.dicom_id)
        self.assertEqual('f689ddd2-662f8fe1-8b18180d-ec2a2cee-937917af', instance.orthanc_id)

        series = instance.series
        self.assertEqual("CT", series.main_dicom_tags.get('Modality'))
        self.assertEqual('1.3.6.1.4.1.5962.1.3.1.1.20040119072730.12322', series.dicom_id)
        self.assertEqual('93034833-163e42c3-bc9a428b-194620cf-2c5799e5', series.orthanc_id)

        instance = series.instances[0]
        self.assertEqual("113008", instance.tags.get('ContentTime'))


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
        instances_ids = self.oa.upload_folder(here / "stimuli", skip_extensions=['.zip', '.pdf', '.png'])

        self.assertLessEqual(1, len(instances_ids))
        self.oa.instances.delete(orthanc_ids=instances_ids)
        self.assertEqual(0, len(self.oa.studies.get_all_ids()))

    def test_upload_folder_ignore_errors(self):
        instances_ids = self.oa.upload_folder(here, skip_extensions=['.zip'], ignore_errors=True)  # here contains __init__.py which is invalid

        self.assertLessEqual(1, len(instances_ids))

    def test_upload_folder_return_details(self):
        self.oa.delete_all_content()
        dicom_ids_set, orthanc_ids_set, rejected_files_list = self.oa.upload_folder_return_details(here / "stimuli")

        self.assertLessEqual(4, len(dicom_ids_set))
        self.oa.studies.delete(orthanc_ids=orthanc_ids_set)
        self.assertEqual(0, len(self.oa.studies.get_all_ids()))
        self.assertEqual(2, len(rejected_files_list))

    def test_upload_folder_return_details_unzip_before_upload(self):
        self.oa.delete_all_content()
        dicom_ids_set, orthanc_ids_set, rejected_files_list = self.oa.upload_folder_return_details(here / "stimuli", unzip_before_upload=True)

        self.assertLessEqual(4, len(dicom_ids_set))
        self.oa.studies.delete(orthanc_ids=orthanc_ids_set)
        self.assertEqual(0, len(self.oa.studies.get_all_ids()))
        self.assertEqual(2, len(rejected_files_list))

    def test_upload_folder_return_details_error_case(self):
        # Let's make orthanc unresponsive
        with open(here / "docker-setup/inhibit.lua", 'rb') as f:
            lua_script = f.read()
        self.oa.execute_lua_script(lua_script)

        dicom_ids_set, orthanc_ids_set, rejected_files_list = self.oa.upload_folder_return_details(here / "stimuli")

        self.assertEqual(0, len(dicom_ids_set))
        self.assertEqual(0, len(orthanc_ids_set))
        self.assertEqual(9, len(rejected_files_list))

        # let's uninhibit the destination
        with open(here / "docker-setup/uninhibit.lua", 'rb') as f:
            lua_script = f.read()
        self.oa.execute_lua_script(lua_script)

    def test_upload_file_dicom_web(self):
        self.oa.delete_all_content()

        self.oa.upload_files_dicom_web([here / "stimuli/CT_small.dcm"])

        self.assertEqual(1, len(self.oa.studies.get_all_ids()))


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
        patient_id = self.oa.patients.get_all_ids()[0]

        self.assertEqual(instance_id, instances_ids[0])
        self.assertEqual(series_id, self.oa.instances.get_parent_series_id(instance_id))
        self.assertEqual(study_id, self.oa.instances.get_parent_study_id(instance_id))
        self.assertEqual(patient_id, self.oa.instances.get_parent_patient_id(instance_id))

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

    def test_dicomweb_send_asynchronous(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()

        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids = self.oa.upload(dicom)
        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids.extend(self.oa.upload(dicom))

        study_id = self.oa.studies.lookup('1.2.3')

        job = self.oa.dicomweb_servers.send_async('orthanc-b', study_id)
        self.assertEqual(JobType.DICOM_WEB_STOW_CLIENT, job.info.type)
        wait_until(job.is_complete, 5)
        self.assertEqual(JobStatus.SUCCESS, job.refresh().info.status)

        study_id = self.ob.studies.lookup('1.2.3')
        self.assertIsNotNone(study_id)

    def test_dicomweb_send(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()

        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids = self.oa.upload(dicom)
        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids.extend(self.oa.upload(dicom))

        study_id = self.oa.studies.lookup('1.2.3')

        job = self.oa.dicomweb_servers.send('orthanc-b', study_id)

        study_id = self.ob.studies.lookup('1.2.3')
        self.assertIsNotNone(study_id)

    def test_modalities_send(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()

        self.assertEqual(3, len(self.oa.modalities.get_all_ids()))
        self.assertIn("orthanc-a", self.oa.modalities.get_all_ids())
        self.assertEqual("orthanc-a", self.oa.modalities.get_id_from_aet("ORTHANCA"))

        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids = self.oa.upload(dicom)
        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids.extend(self.oa.upload(dicom))

        study_id = self.oa.studies.lookup('1.2.3')

        self.oa.modalities.send('orthanc-b', study_id)

        study_id = self.ob.studies.lookup('1.2.3')
        self.assertIsNotNone(study_id)

    def test_modalities_send_asynchronous(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()

        self.assertEqual(3, len(self.oa.modalities.get_all_ids()))
        self.assertIn("orthanc-a", self.oa.modalities.get_all_ids())
        self.assertEqual("orthanc-a", self.oa.modalities.get_id_from_aet("ORTHANCA"))

        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids = self.oa.upload(dicom)
        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids.extend(self.oa.upload(dicom))

        study_id = self.oa.studies.lookup('1.2.3')

        job = self.oa.modalities.send_async('orthanc-b', study_id)

        self.assertEqual(JobType.DICOM_MODALITY_STORE, job.info.type)
        wait_until(job.is_complete, 5)
        self.assertEqual(JobStatus.SUCCESS, job.refresh().info.status)

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

        #request A to get it from B
        self.oa.modalities.get_study(from_modality='orthanc-b', dicom_id='1.2.3')
        self.assertIsNotNone(1, self.oa.studies.lookup('1.2.3'))
        self.oa.delete_all_content()

        self.oa.modalities.get_series(from_modality='orthanc-b', dicom_id='4.5.6', study_dicom_id='1.2.3')
        self.assertIsNotNone(self.oa.series.lookup('4.5.6'))
        self.oa.delete_all_content()

        self.oa.modalities.get_instance(from_modality='orthanc-b', dicom_id='7.8.9', series_dicom_id='4.5.6', study_dicom_id='1.2.3')
        self.assertIsNotNone(self.oa.instances.lookup('7.8.9'))
        self.oa.delete_all_content()

        #request A to get it from B
        self.oa.modalities.retrieve_study(from_modality='orthanc-b', dicom_id='1.2.3', retrieve_method=RetrieveMethod.GET)
        self.assertIsNotNone(1, self.oa.studies.lookup('1.2.3'))
        self.oa.delete_all_content()


    def test_peers_send(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()

        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids = self.oa.upload(dicom)
        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids.extend(self.oa.upload(dicom))

        study_id = self.oa.studies.lookup('1.2.3')

        self.oa.peers.send('orthanc-b', study_id)

        study_id = self.ob.studies.lookup('1.2.3')
        self.assertIsNotNone(study_id)

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

        job = self.oa.transfers.send_async('orthanc-b', resources_ids=study_id, resource_type=ResourceType.STUDY, compress=False)

        self.assertEqual(JobType.PUSH_TRANSFER, job.info.type)
        wait_until(job.is_complete, 5)

        study_id = self.ob.studies.lookup('1.2.3')
        self.assertIsNotNone(study_id)

    def test_transfers_send_instances(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()

        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids = self.oa.upload(dicom)

        job = self.oa.transfers.send_async('orthanc-b', resources_ids=instances_ids, resource_type=ResourceType.INSTANCE, compress=True)

        self.assertEqual(JobType.PUSH_TRANSFER, job.info.type)
        job.wait_completed(timeout=5)

        study_id = self.ob.studies.lookup('1.2.3')
        self.assertIsNotNone(study_id)


    def test_transfers_send_study_pull(self):
        self.oa.delete_all_content()
        self.oc.delete_all_content()

        dicom = generate_test_dicom_file(width=33, height=33, tags={'StudyInstanceUID': '1.2.3'})
        instances_ids = self.oa.upload(dicom)
        study_id = self.oa.studies.lookup('1.2.3')

        remote_job = self.oa.transfers.send_async('orthanc-c', resources_ids=study_id, resource_type=ResourceType.STUDY, compress=True)
        self.assertTrue(isinstance(remote_job, RemoteJob))

        job = self.oc.jobs.get(orthanc_id=remote_job.remote_job_id)

        self.assertEqual(JobType.PULL_TRANSFER, job.info.type)
        wait_until(job.is_complete, 5)

        study_id = self.oc.studies.lookup('1.2.3')
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
        value = self.oa.instances.get_string_metadata(
            instances_ids[0],
            metadata_name='1024',
            default_value=None
        )
        self.assertEqual(None, value)

        content = b'123456789'
        revision = self.oa.instances.set_binary_metadata(
            orthanc_id=instances_ids[0],
            metadata_name='1025',
            content=content
            )

        # get current revision
        content_readback, revision = self.oa.instances.get_string_metadata_with_revision(
            orthanc_id=instances_ids[0],
            metadata_name='1025'
        )

        self.assertEqual(content, content_readback.encode('utf-8'))

        # update if match current revision
        self.oa.instances.set_string_metadata(
            orthanc_id=instances_ids[0],
            metadata_name='1025',
            content='abcdefg2',
            match_revision=revision
            )

        # try to update if match another revision -> fails
        with self.assertRaises(api_exceptions.Conflict):
            self.oa.instances.set_string_metadata(
                orthanc_id=instances_ids[0],
                metadata_name=1025,
                content='abd4',
                match_revision='"1-bad-checksum"'
                )

        # get current revision
        content_readback, revision = self.oa.instances.get_string_metadata_with_revision(
            orthanc_id=instances_ids[0],
            metadata_name=1025
        )

        self.assertEqual('abcdefg2', content_readback)

    def test_metadata_default_value(self):
        self.oa.delete_all_content()
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")

        # try to read a metadata that does not exist
        value = self.oa.instances.get_string_metadata(
            instances_ids[0],
            metadata_name='1024',
            default_value=None
        )
        self.assertEqual(None, value)

        value = self.oa.instances.get_string_metadata(
            instances_ids[0],
            metadata_name='1024',
            default_value=''
        )
        self.assertEqual('', value)

        value, revision = self.oa.instances.get_string_metadata_with_revision(
            instances_ids[0],
            metadata_name='1024',
            default_value=''
        )
        self.assertEqual('', value)


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
        self.assertEqual('ANON', self.oa.studies.get_tags(anon_study_id)['PatientID'])

    def test_anonymize_patient(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        patient_id = self.oa.instances.get_parent_patient_id(instances_ids[0])

        # default anonymize
        anon_patient_id = self.oa.patients.anonymize(
            orthanc_id=patient_id,
            keep_tags=['PatientName'],
            force=True,
            delete_original=False
        )

        self.assertEqual(self.oa.patients.get_tags(patient_id)['PatientName'], self.oa.patients.get_tags(anon_patient_id)['PatientName'])
        self.assertNotEqual('1CT1', self.oa.patients.get_tags(anon_patient_id)['PatientID'])


    def test_modify_bulk_series(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        series_id = self.oa.instances.get_parent_series_id(instances_ids[0])

        original_tags = self.oa.series.get_tags(series_id)

        _, modified_series_ids, __, ___ = self.oa.series.modify_bulk(
            orthanc_ids=[series_id],
            remove_tags=['InstitutionName'],
            replace_tags={
                'PatientID': 'modified-id',
                'PatientName': 'modified-name',
                'StudyInstanceUID': original_tags['StudyInstanceUID'],
                'SeriesInstanceUID': original_tags['SeriesInstanceUID'],
            },
            force=True,
            delete_original=True
        )

        modified_tags = self.oa.series.get_tags(modified_series_ids[0])

        self.assertEqual(original_tags['StudyInstanceUID'], modified_tags['StudyInstanceUID'])
        self.assertEqual(original_tags['SeriesInstanceUID'], modified_tags['SeriesInstanceUID'])
        self.assertEqual('modified-id', modified_tags['PatientID'])

    def test_modify_bulk_study(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        original_tags = self.oa.studies.get_tags(study_id)

        # default anonymize
        _, _, modified_studies_ids, _ = self.oa.studies.modify_bulk(
            orthanc_ids=[study_id],
            remove_tags=['InstitutionName'],
            replace_tags={
                'PatientID': 'modified-id',
                'PatientName': 'modified-name',
                'StudyInstanceUID': original_tags['StudyInstanceUID'],
                'SeriesInstanceUID': original_tags['SeriesInstanceUID'],
            },
            force=True,
            delete_original=True
        )

        modified_tags = self.oa.studies.get_tags(modified_studies_ids[0])

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


    def test_modify_patient(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        patient_id = self.oa.instances.get_parent_patient_id(instances_ids[0])

        modified_patient_id = self.oa.patients.modify(
            orthanc_id=patient_id,
            remove_tags=['PatientWeight'],
            replace_tags={
                'PatientID': 'modified-id',
            },
            delete_original=False,
            force=True
        )

        modified_tags = self.oa.patients.get_tags(modified_patient_id)

        self.assertFalse('PatientWeight' in modified_tags)
        self.assertEqual('modified-id', modified_tags['PatientID'])


    def test_modify_study_keep_tags(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        original_instance_tags = self.oa.instances.get_tags(instances_ids[0])

        modified_study_id = self.oa.studies.modify(
            orthanc_id=study_id,
            replace_tags={
                'PatientID': '1234',
                'OtherPatientIDs': '5678'
            },
            keep_tags=['StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID'],
            delete_original=False,
            force=True
        )

        modified_instance_tags = self.oa.instances.get_tags(self.oa.studies.get_instances_ids(modified_study_id)[0])

        self.assertEqual(original_instance_tags['StudyInstanceUID'], modified_instance_tags['StudyInstanceUID'])
        self.assertEqual(original_instance_tags['SeriesInstanceUID'], modified_instance_tags['SeriesInstanceUID'])
        self.assertEqual(original_instance_tags['SOPInstanceUID'], modified_instance_tags['SOPInstanceUID'])
        self.assertEqual('1234', modified_instance_tags['PatientID'])
        self.assertEqual('5678', modified_instance_tags['OtherPatientIDs'])

    def test_modify_instances(self):
        self.oa.delete_all_content()

        instance_id = self.oa.upload_file(here / "stimuli/CT_small.dcm")[0]

        original_tags = self.oa.instances.get_tags(instance_id)

        modified = self.oa.instances.modify(
            orthanc_id=instance_id,
            remove_tags=['InstitutionName'],
            replace_tags={
                'SeriesDate': '20220208'
            },
            keep_tags=['StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID'],
            force=True
        )
        modified_id = self.oa.upload(buffer=modified)[0]
        self.assertEqual(instance_id, modified_id)

        modified_tags = self.oa.instances.get_tags(modified_id)

        self.assertFalse('InstitutionName' in modified_tags)
        self.assertEqual('20220208', modified_tags['SeriesDate'])
        self.assertEqual(original_tags.get('StudyInstanceUID'), modified_tags.get('StudyInstanceUID'))
        self.assertEqual(original_tags.get('SeriesInstanceUID'), modified_tags.get('SeriesInstanceUID'))
        self.assertEqual(original_tags.get('SOPInstanceUID'), modified_tags.get('SOPInstanceUID'))

    def test_modify_bulk_instances_async(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_folder(here / "stimuli/MR/Brain")

        job = self.oa.instances.modify_bulk_async(
            orthanc_ids=instances_ids,
            remove_tags=['InstitutionName'],
            keep_tags=['SeriesInstanceUID', 'SOPInstanceUID'],
            replace_tags={
                'StudyInstanceUID': "1.2.3.4"
            },
            transcode="1.2.840.10008.1.2.4.70",
            force=True
        )
        job.wait_completed()
        self.assertEqual(JobStatus.SUCCESS, job.info.status)

    def test_modify_bulk_instances(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_folder(here / "stimuli/MR/Brain")

        modified_instances_ids, modified_series_ids, modified_studies_ids, modified_patients_ids = self.oa.instances.modify_bulk(
            orthanc_ids=instances_ids,
            remove_tags=['InstitutionName'],
            keep_tags=['SeriesInstanceUID', 'SOPInstanceUID'],
            replace_tags={
                'StudyInstanceUID': "1.2.3.4"
            },
            transcode="1.2.840.10008.1.2.4.70",
            delete_original=True,
            force=True
        )
        self.assertEqual(3, len(modified_instances_ids))
        self.assertEqual(2, len(modified_series_ids))
        self.assertEqual(1, len(modified_studies_ids))
        self.assertEqual(1, len(modified_patients_ids))
        self.assertNotIn(instances_ids[0], modified_instances_ids)  # make sure the new ids are different from the original ones


    def test_anonymize_bulk_series(self):
        self.oa.delete_all_content()

        self.oa.upload_folder(here / "stimuli/MR/Brain")
        series_ids = self.oa.series.get_all_ids()

        self.assertEqual(1, len(self.oa.studies.get_all_ids()))

        _, modified_series_ids, __, ___ = self.oa.series.anonymize_bulk(
            orthanc_ids=series_ids,
            delete_original=False,
            keep_tags=["SeriesDescription", "StudyDescription"]
        )

        self.assertEqual(2, len(modified_series_ids))
        tags1 = self.oa.series.get_tags(modified_series_ids[0])
        tags2 = self.oa.series.get_tags(modified_series_ids[1])
        self.assertEqual(tags1.get("PatientName"), tags2.get("PatientName"))
        self.assertEqual(tags1.get("StudyDescription"), tags2.get("StudyDescription"))
        self.assertEqual(tags1.get("StudyInstanceUID"), tags2.get("StudyInstanceUID"))
        self.assertIn(tags1.get("SeriesDescription"), ["sT2W/FLAIR", "T1/3D/FFE/C"])
        # make sure both series are in the same anonymized study (the original study is still in Orthanc)
        self.assertEqual(2, len(self.oa.studies.get_all_ids()))


    def test_anonymize_bulk_study(self):
        self.oa.delete_all_content()

        self.oa.upload_folder(here / "stimuli/MR/Brain")
        self.oa.upload_file(here / "stimuli/CT_small.dcm")

        self.assertEqual(2, len(self.oa.studies.get_all_ids()))

        _, __, modified_studies_ids, ___ = self.oa.series.anonymize_bulk(
            orthanc_ids=self.oa.studies.get_all_ids(),
            delete_original=False,
            keep_tags=["SeriesDescription", "StudyDescription"],
            replace_tags={
                "PatientID": str(uuid.uuid4()),                    # orthanc does not put all studies in the same patient -> you must do it manually
                "PatientName": f"Anonymized " + str(uuid.uuid4())
            },
            force=True
        )

        self.assertEqual(2, len(modified_studies_ids))
        tags1 = self.oa.studies.get_tags(modified_studies_ids[0])
        tags2 = self.oa.studies.get_tags(modified_studies_ids[1])
        self.assertEqual(tags1.get("PatientName"), tags2.get("PatientName"))
        self.assertNotEqual(tags1.get("StudyDescription"), tags2.get("StudyDescription"))
        self.assertNotEqual(tags1.get("StudyInstanceUID"), tags2.get("StudyInstanceUID"))
        # make sure both studies are in the same anonymized patient (the original patients are still in Orthanc)
        self.assertEqual(3, len(self.oa.patients.get_all_ids()))

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

    def test_find_patient(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        patient_id = self.oa.instances.get_parent_patient_id(instances_ids[0])

        patients = self.oa.patients.find(
            query={
                'PatientID': '1C*'
            }
        )

        self.assertEqual(1, len(patients))
        self.assertEqual('1CT1', patients[0].dicom_id)


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
        self.assertIsNotNone(job.content)
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

    def test_get_pdf_instances(self):
        self.oa.delete_all_content()

        # upload an instance with a PDF file
        instances_ids = self.oa.upload_file(here / "stimuli/encapsulated_pdf_instance.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        self.assertEqual(instances_ids, self.oa.studies.get_pdf_instances(study_id))

    def test_is_pdf_instance(self):
        self.oa.delete_all_content()
        # upload an instance with a PDF file
        instances_ids = self.oa.upload_file(here / "stimuli/encapsulated_pdf_instance.dcm")
        self.assertTrue(self.oa.instances.is_pdf(instances_ids[0]))

        # test it return false with a non PDF file
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        self.assertFalse(self.oa.instances.is_pdf(instances_ids[0]))

    def test_download_pdf(self):
        self.oa.delete_all_content()

        # upload an instance with a PDF file
        instances_ids = self.oa.upload_file(here / "stimuli/encapsulated_pdf_instance.dcm")

        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.tmp'))
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path)
        file_path = os.path.join(path, '%s.pdf' % instances_ids[0])
        pdf_path = self.oa.instances.download_pdf(instances_ids[0], file_path)
        self.assertTrue(os.path.exists(pdf_path))
        shutil.rmtree(path)
        self.assertFalse(os.path.exists(pdf_path))

    def test_create_pdf(self):
        self.oa.delete_all_content()

        # create a pdf
        instance_id = self.oa.create_pdf(here / "stimuli/sample.pdf", {'PatientID' : '1234', 'PatientName' : 'TOTO'})

        self.assertIsNotNone(instance_id)

        study_id = self.oa.instances.get_parent_study_id(instance_id)
        tags = self.oa.studies.get_tags(study_id)

        self.assertEqual('1234', tags['PatientID'])
        self.assertEqual('TOTO', tags['PatientName'])
        self.assertTrue(self.oa.instances.is_pdf(instance_id))
        self.assertEqual([instance_id], self.oa.studies.get_pdf_instances(study_id))

    def test_attach_pdf(self):
        self.oa.delete_all_content()
        #upload a study
        original_pdf_path = here / "stimuli/sample.pdf"
        instances_id = self.oa.upload_folder(here / 'stimuli/MR/Brain/1')
        original_study_id = self.oa.instances.get_parent_study_id(instances_id[0])

        original_study = self.oa.studies.get(original_study_id)

        # attach a pdf to the study
        pdf_instance_id = self.oa.studies.attach_pdf(
            pdf_path = original_pdf_path,
            study_id = original_study_id,
            series_description = 'Protocole PDF',
            datetime = datetime.datetime(year=2023, month=1, day=20, hour=12, minute=32, second=43)
        )

        self.assertIsNotNone(pdf_instance_id)
        self.assertEqual(original_study_id, self.oa.instances.get_parent_study_id(pdf_instance_id)) # make sure the pdf is part of the study
        pdf_tags = self.oa.instances.get_tags(pdf_instance_id)

        self.assertEqual(original_study.patient_main_dicom_tags.get('PatientID'), pdf_tags['PatientID'])
        self.assertEqual(original_study.patient_main_dicom_tags.get('PatientName'), pdf_tags['PatientName'])
        self.assertEqual(original_study.main_dicom_tags.get('StudyInstanceUID'), pdf_tags['StudyInstanceUID'])
        self.assertEqual('Protocole PDF', pdf_tags['SeriesDescription'])
        self.assertEqual('20230120', pdf_tags['SeriesDate'])
        self.assertEqual('123243', pdf_tags['SeriesTime'])
        self.assertEqual([pdf_instance_id], self.oa.studies.get_pdf_instances(original_study_id))

        # download the pdf and compare with the original file
        with tempfile.NamedTemporaryFile(delete = False) as f:
            self.oa.instances.download_pdf(pdf_instance_id, f.name)

            pdf_content_after_download = open(f.name, 'rb').read()
            pdf_content_original = open(original_pdf_path, 'rb').read()
        self.assertEqual(pdf_content_original, pdf_content_after_download)

        f.delete = True
        f.close()

    def test_create_png(self):
        self.oa.delete_all_content()

        # create an instance from a png
        instance_id = self.oa.create_instance_from_png(here / "stimuli/orthanc-logo.png", {'PatientID' : '1234', 'PatientName' : 'ORTHANC-TEAM'})
        instance_tags = self.oa.instances.get_tags(instance_id)

        self.assertIsNotNone(instance_id)
        study = self.oa.studies.get(self.oa.instances.get_parent_study_id(instance_id))

        self.assertEqual('1234', study.patient_main_dicom_tags.get('PatientID'))
        self.assertEqual('ORTHANC-TEAM', study.patient_main_dicom_tags.get('PatientName'))
        self.assertEqual('146', instance_tags['Columns'])
        self.assertEqual('135', instance_tags['Rows'])
        self.assertEqual(to_dicom_date(datetime.date.today()), instance_tags['StudyDate'])

    def test_download_instance(self):
        self.oa.delete_all_content()

        # upload an instance
        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")

        with tempfile.NamedTemporaryFile() as f:
            self.oa.instances.download_instance(instance_id=instances_ids[0], path=f.name)
            instance_content_after_download = open(f.name, 'rb').read()
            instance_content_original = open(here / "stimuli/CT_small.dcm", 'rb').read()
            self.assertEqual(instance_content_after_download, instance_content_original)

    def test_download_series_studies(self):
        self.oa.delete_all_content()

        # upload all images from a study
        instances_id = self.oa.upload_folder(here / 'stimuli/MR/Brain/1')

        # download all files of the series
        series_id = self.oa.instances.get_parent_series_id(instances_id[0])
        with tempfile.TemporaryDirectory() as tempDir:
            downloaded_instances = self.oa.series.download_instances(series_id=series_id, path=tempDir)
        self.assertEqual(len(instances_id), len(downloaded_instances))

        # download all files of the study
        study_id = self.oa.series.get_parent_study_id(series_id)
        with tempfile.TemporaryDirectory() as tempDir:
            downloaded_instances = self.oa.studies.download_instances(study_id, tempDir)
        self.assertEqual(len(instances_id), len(downloaded_instances))


    def test_instances_set(self):
        self.oa.delete_all_content()

        # upload a partial study
        instances_id = self.oa.upload_folder(here / 'stimuli/MR/Brain/1')
        study_id = self.oa.instances.get_parent_study_id(instances_id[0])

        instances_set = InstancesSet.from_study(api_client=self.oa, study_id=study_id)

        self.assertEqual(1, len(instances_set.series_ids))
        self.assertEqual(2, len(instances_set.instances_ids))
        self.assertEqual(2, len(instances_set.get_instances_ids(series_id=instances_set.series_ids[0])))

        with tempfile.NamedTemporaryFile() as file:
            self.assertTrue(os.path.getsize(file.name) == 0)
            instances_set.download_archive(file.name)
            self.assertTrue(os.path.exists(file.name))
            self.assertTrue(os.path.getsize(file.name) > 0)

        with tempfile.NamedTemporaryFile() as file:
            self.assertTrue(os.path.getsize(file.name) == 0)
            instances_set.download_media(file.name)
            self.assertTrue(os.path.exists(file.name))
            self.assertTrue(os.path.getsize(file.name) > 0)

        # upload the second part of the study
        instances_id = self.oa.upload_folder(here / 'stimuli/MR/Brain/2')
        self.assertEqual(3, len(self.oa.studies.get_instances_ids(orthanc_id=study_id)))

        # modify the instance set only
        modified_set = instances_set.modify(
            replace_tags={
                'InstitutionName' : 'MY',
                'PatientName': 'TOTO',
                'PatientID': 'TEST',
                'OtherPatientIDs': 'TEST2'
            },
            keep_tags=['SOPInstanceUID', 'SeriesInstanceUID', 'StudyInstanceUID'],
            force=True,
            keep_source=False  # we are changing the PatientID -> Orthanc IDs will change
        )

        # this should not modify the total number of instances in Orthanc
        self.assertEqual(3, len(self.oa.instances.get_all_ids()))

        # the modified set shall have the same structure as the source
        self.assertEqual(1, len(modified_set.series_ids))
        self.assertEqual(2, len(modified_set.instances_ids))
        self.assertEqual(2, len(modified_set.get_instances_ids(series_id=modified_set.series_ids[0])))

        # check that changes have been applied
        self.assertEqual("TEST2", self.oa.studies.get(modified_set.study_id).patient_main_dicom_tags.get('OtherPatientIDs'))

        # delete only the modified set
        modified_set.delete()

        self.assertEqual(1, len(self.oa.instances.get_all_ids()))

    def test_instances_set_filter_apply(self):
        self.oa.delete_all_content()

        # upload a 2 series study (2 instances in T1/3D/FFE/C and 1 instance in sT2W/FLAIR)
        instances_id = self.oa.upload_folder(here / 'stimuli/MR/Brain')
        study_id = self.oa.instances.get_parent_study_id(instances_id[0])

        instances_set = InstancesSet.from_study(api_client=self.oa, study_id=study_id)

        self.assertEqual(3, len(instances_set.instances_ids))
        # filter and keep only 'sT2W/FLAIR'
        filtered_out_set = instances_set.filter_instances(filter=lambda api, i: 'sT2W/FLAIR' == api.instances.get(i).series.main_dicom_tags.get('SeriesDescription'))

        self.assertEqual(1, len(instances_set.instances_ids))
        self.assertEqual(1, len(instances_set.series_ids))
        self.assertEqual(2, len(filtered_out_set.instances_ids))
        self.assertEqual(1, len(filtered_out_set.series_ids))

        # apply a metadata to the filtered list of instances
        instances_set.process_instances(processor=lambda api, i: api.instances.set_string_metadata(i, '1024', 'filtered'))

        # now filter based on metadata
        instances_set2 = InstancesSet.from_study(api_client=self.oa, study_id=study_id)
        instances_set2.filter_instances(filter=lambda api, i: 'filtered' == api.instances.get_string_metadata(i, '1024', None))
        self.assertEqual(1, len(instances_set2.instances_ids))
        self.assertEqual(1, len(instances_set2.series_ids))
        self.assertEqual(instances_set.instances_ids, instances_set2.instances_ids)

    def test_add_get_label(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        # no labels at beginning
        labels = self.oa.studies.get_labels(study_id)
        self.assertEqual(len(labels), 0)

        # the label has been applied
        my_label = "MYLABEL"
        self.oa.studies.add_label(study_id, my_label)
        read_labels = self.oa.studies.get_labels(study_id)
        self.assertEqual(len(read_labels), 1)
        self.assertEqual(read_labels[0], my_label)

    def test_delete_label(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        # no labels at beginning
        labels = self.oa.studies.get_labels(study_id)
        self.assertEqual(len(labels), 0)

        # the labels have been applied
        my_label_1 = "MYLABEL1"
        my_label_2 = "MYLABEL2"
        self.oa.studies.add_labels(study_id, [my_label_1, my_label_2])
        read_labels = self.oa.studies.get_labels(study_id)
        self.assertEqual(len(read_labels), 2)

        # only label 1 is deleted
        self.oa.studies.delete_label(study_id, my_label_1)
        read_labels = self.oa.studies.get_labels(study_id)
        self.assertEqual(len(read_labels), 1)
        self.assertEqual(read_labels[0], my_label_2)

        # labels list has been deleted
        self.oa.studies.delete_labels(study_id, [my_label_2])
        read_labels = self.oa.studies.get_labels(study_id)
        self.assertEqual(len(read_labels), 0)

    def test_find_study_with_label(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_file(here / "stimuli/CT_small.dcm")
        study_id = self.oa.instances.get_parent_study_id(instances_ids[0])

        my_label = "MYLABEL"
        self.oa.studies.add_label(study_id, my_label)

        # study with the label is found
        studies = self.oa.studies.find(
            query={},
            labels=[my_label]
        )
        self.assertEqual(1, len(studies))

        # study with another label is not found
        studies = self.oa.studies.find(
            query={},
            labels=["NOTMYLABEL"]
        )
        self.assertEqual(0, len(studies))

        # study with another label is found if constraint to 'None'
        studies = self.oa.studies.find(
            query={},
            labels=["NOTMYLABEL"],
            labels_constraint=LabelsConstraint.NONE
        )
        self.assertEqual(1, len(studies))

        # study with 2 labels is found
        my_label2 = "MYLABEL2"
        self.oa.studies.add_label(study_id, my_label2)
        studies = self.oa.studies.find(
            query={},
            labels=[my_label, my_label2],
            labels_constraint=LabelsConstraint.ALL
        )
        self.assertEqual(1, len(studies))

        # study with 1 label is found (constraint = 'Any')
        self.oa.studies.delete_label(study_id, my_label2)
        studies = self.oa.studies.find(
            query={},
            labels=[my_label, my_label2],
            labels_constraint=LabelsConstraint.ANY
        )
        self.assertEqual(1, len(studies))

    def test_get_labels(self):
        self.oa.delete_all_content()

        instances_ids = self.oa.upload_folder(here / 'stimuli/MR/Brain/1')

        my_label1 = "MYLABEL1"
        my_label2 = "MYLABEL2"
        self.oa.instances.add_label(instances_ids[0], my_label1)
        self.oa.instances.add_label(instances_ids[1], my_label2)

        # 2 labels are retrieved
        read_labels = self.oa.get_all_labels()

        self.assertEqual(2, len(read_labels))
        self.assertIn(my_label1, read_labels)
        self.assertIn(my_label2, read_labels)

        # only one label is still there
        self.oa.instances.delete_label(instances_ids[0], my_label1)

        read_labels = self.oa.get_all_labels()

        self.assertEqual(1, len(read_labels))
        self.assertIn(my_label2, read_labels)

    def test_execute_lua_script(self):
        script = b"print(42)"
        r = self.oa.execute_lua_script(script)

        self.assertEqual(r, b"42\n")


    def test_get_log_level(self):
        r = self.oa.set_log_level(level=LogLevel.VERBOSE)
        r = self.oa.get_log_level()

        self.assertEqual(r, LogLevel.VERBOSE)


    def test_set_log_level(self):
        r = self.oa.set_log_level(level=LogLevel.DEFAULT)

        self.assertEqual(r, LogLevel.DEFAULT)

    def test_date_helpers(self):
        self.assertEqual(datetime.date(2024, 8, 15), from_dicom_date("20240815"))
        self.assertEqual(datetime.time(9, 12, 35), from_dicom_time("091235"))
        self.assertEqual(datetime.time(9, 12, 35, 100000), from_dicom_time("091235.1"))
        self.assertEqual(datetime.time(9, 12, 35, 120000), from_dicom_time("091235.12"))
        self.assertEqual(datetime.time(9, 12, 35, 123000), from_dicom_time("091235.123"))
        self.assertEqual(datetime.time(9, 12, 35, 123450), from_dicom_time("091235.12345"))
        self.assertEqual(datetime.time(9, 12, 35, 123456), from_dicom_time("091235.123456"))
        self.assertEqual(datetime.datetime(2024, 8, 15, 9, 12, 35), from_dicom_date_and_time("20240815", "091235"))
        self.assertEqual(datetime.datetime(2024, 8, 15, 0, 0, 0), from_dicom_date_and_time("20240815", ""))
        self.assertEqual(datetime.datetime(2024, 8, 15, 0, 0, 0), from_dicom_date_and_time("20240815", None))
        #self.assertEqual(datetime.datetime(2024, 8, 15, 9, 12, 35), from_dicom_datetime("20240815T091235"))  # TODO
        #self.assertEqual(datetime.datetime(2024, 8, 15, 9, 12, 35), from_dicom_datetime("20240815T091235+0205"))  # TODO

    def test_version(self):
        self.assertTrue(is_version_at_least("0.0.0", 0, 0, 0))
        self.assertTrue(is_version_at_least("0.0.1", 0, 0, 1))
        self.assertTrue(is_version_at_least("0.1.0", 0, 1, 0))
        self.assertTrue(is_version_at_least("1.2.3", 1, 2, 3))
        self.assertTrue(is_version_at_least("1.2.4", 1, 2, 3))
        self.assertFalse(is_version_at_least("1.2.2", 1, 2, 3))
        self.assertFalse(is_version_at_least("1.1.4", 1, 2, 3))
        self.assertFalse(is_version_at_least("0.2.3", 1, 2, 3))
        self.assertTrue(is_version_at_least("1.2", 1, 2, 3))
        self.assertFalse(is_version_at_least("1.1", 1, 2, 3))

        self.assertTrue(is_version_at_least("mainline", 1, 2, 3))  # mainline is always bigger than any version number !!!
        self.assertTrue(is_version_at_least("mainline-548748", 1, 2, 3))  # mainline is always bigger than any version number !!!

        self.assertTrue(self.oa.is_orthanc_version_at_least(1, 9, 0))
        self.assertTrue(self.oa.is_plugin_version_at_least("dicom-web", 1, 5))
        self.assertTrue(self.oa.has_loaded_plugin("dicom-web"))
        self.assertFalse(self.oa.has_loaded_plugin("wsi"))

    def test_capabilities(self):
        self.assertTrue(self.oa.capabilities.has_label_support)         # since we are using SQLite
        self.assertTrue(self.oa.capabilities.has_revision_support)      # since we are using SQLite
        self.assertTrue(self.oa.capabilities.has_extended_changes)      # since we are using SQLite
        self.assertTrue(self.oa.capabilities.has_extended_find)         # since we are using SQLite

    def test_path(self):
        # test issue #4
        self.assertEqual(self.oa.get_json('statistics'), self.oa.get_json('/statistics'))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    unittest.main()

