import base64
import os
import logging
import typing
import datetime
import zipfile
import tempfile
from typing import List, Optional, Dict
from urllib.parse import urlunsplit, urlencode

from .http_client import HttpClient
from .resources import Instances, SeriesList, Studies, Jobs, Patients

from .helpers import wait_until, encode_multipart_related, is_version_at_least
from .exceptions import *
from .dicomweb_servers import DicomWebServers
from .modalities import DicomModalities
from .change import Change, ChangeType, ResourceType
from .transfers import Transfers
from .peers import Peers
from .logging import LogLevel
from .capabilities import Capabilities

logger = logging.getLogger(__name__)

class SystemStatistics:

    def __init__(self, json_stats):
        self.instances_count = json_stats['CountInstances']
        self.patients_count = json_stats['CountPatients']
        self.series_count = json_stats['CountSeries']
        self.studies_count = json_stats['CountStudies']
        self.total_disk_size = int(json_stats['TotalDiskSize'])
        self.total_disk_size_mb = json_stats['TotalDiskSizeMB']
        self.total_uncompressed_size = int(json_stats['TotalUncompressedSize'])
        self.total_uncompressed_size_mb = json_stats['TotalUncompressedSizeMB']


class OrthancApiClient(HttpClient):

    def __init__(self, orthanc_root_url: str, user: Optional[str] = None, pwd: Optional[str] = None, api_token: Optional[str] = None, headers: Optional[Dict[str, str]] = None ) -> None:
        """Creates an HttpClient

        Parameters
        ----------
        orthanc_root_url: base orthanc url: ex= 'http://localhost:8042'
        user: an orthanc user name (for basic Auth)
        pwd: the password for the orthanc user (for basic Auth)
        api_token: a token obtained from inside an Orthanc python plugin through orthanc.GenerateRestApiAuthorizationToken
                   format: 'Bearer 3d03892c-fe...' or '3d03892c-fe...'
        headers: HTTP headers that will be included in each requests
        """
        if api_token:
            if headers is None:
                headers = {}
            if api_token.startswith('Bearer '):
                header_value = api_token
            else:
                header_value = f'Bearer {api_token}'
            headers['authorization'] = header_value

        super().__init__(root_url=orthanc_root_url, user=user, pwd=pwd, headers=headers)

        self.patients = Patients(api_client=self)
        self.studies = Studies(api_client=self)
        self.series = SeriesList(api_client=self)
        self.instances = Instances(api_client=self)
        self.dicomweb_servers = DicomWebServers(api_client=self)
        self.modalities = DicomModalities(api_client=self)
        self.jobs = Jobs(api_client=self)
        self.transfers = Transfers(api_client=self)
        self.peers = Peers(api_client=self)
        self.capabilities = Capabilities(api_client=self)

    def __repr__(self) -> str:
        return f"{self._root_url}"

    def wait_started(self, timeout: float = None) -> bool:
        return wait_until(self.is_alive, timeout)

    def is_alive(self, timeout = 1) -> bool:
        """Checks if the orthanc server can be reached.
        
        Returns
        -------
            True if orthanc can be reached, False otherwise
        """
        try:
            # if we get an answer to a basic request, it means the server is alive
            self.get('system', timeout=timeout)
            return True
        except Exception as e:
            return False

    def is_orthanc_version_at_least(self, expected_major: int, expected_minor: int, expected_patch: Optional[int] = None) -> bool:
        s = self.get_system()
        return is_version_at_least(s.get("Version"), expected_major, expected_minor, expected_patch)

    def is_plugin_version_at_least(self, plugin_name: str, expected_major: int, expected_minor: int, expected_patch: Optional[int] = None) -> bool:
        if self.has_loaded_plugin(plugin_name):
            plugin = self.get_json(f"plugins/{plugin_name}")
            return is_version_at_least(plugin.get("Version"), expected_major, expected_minor, expected_patch)
        return False

    def has_loaded_plugin(self, plugin_name: str) -> bool:
        plugins = self.get_json('plugins')
        return plugin_name in plugins

    def get_system(self) -> object:
        return self.get_json('system')

    def get_statistics(self) -> SystemStatistics:
        return SystemStatistics(json_stats=self.get_json('statistics'))

    def delete_all_content(self):
        """Deletes all content from Orthanc"""
        self.patients.delete_all()

    def upload(self, buffer: bytes, ignore_errors: bool = False) -> List[str]:
        """Uploads the content of a binary buffer to Orthanc (can be a DICOM file or a zip file)

        Parameters
        ----------
        ignore_errors: if True: does not raise exceptions
        
        Returns
        -------
        the instance id of the uploaded file or None when uploading a zip file
        """
        try:
            response = self.post('instances', data=buffer)
            if isinstance(response.json(), list):
                return [x['ID'] for x in response.json()]
            else:
                return [response.json()['ID']]
        except HttpError as ex:
            if ex.http_status_code == 409 and ignore_errors:  # same instance being uploaded twice at the same time
                return []
            if ex.http_status_code == 400 and ex.request_response.json()['OrthancStatus'] == 15:
                if ignore_errors:
                    return []
                else:
                    raise BadFileFormat(ex)
            else:
                raise ex        


    def upload_file(self, path, ignore_errors: bool = False) -> List[str]:
        """Uploads a file to Orthanc (can be a DICOM file or a zip file)
        
        Parameters
        ----------
        ignore_errors: if True: does not raise exceptions

        Returns
        -------
        the list of instances ids (one if a single file, can be multiple if the uploaded file is a zip)
        """
        logger.info(f"uploading {path}")
        with open(path, 'rb') as f:
            return self.upload(f.read(), ignore_errors)


    def upload_folder(self, 
                      folder_path: str, 
                      skip_extensions: List[str] = None,
                      ignore_dots: bool = True,
                      ignore_errors: bool = False
                      ) -> List[str]:
        """Uploads all files from a folder.

        Parameters
        ----------
        folder_path: the folder to upload
        skip_extensions: a list of extensions to skip e.g: ['.ini', '.bmp']
        ignore_dots: to ignore files/folders starting with a dot
        ignore_errors: if True: does not raise exceptions

        Returns
        -------
        A list of instances id (one for each uploaded file)
        """

        instances_ids = []
        
        for path in os.listdir(folder_path):
            if ignore_dots and path.startswith('.'):
                continue

            full_path = os.path.join(folder_path, path)
            if os.path.isfile(full_path):
                if not skip_extensions or not any([full_path.endswith(ext) for ext in skip_extensions]):
                    instances_ids.extend(self.upload_file(full_path, ignore_errors=ignore_errors))
            elif os.path.isdir(full_path):
                instances_ids.extend(self.upload_folder(full_path, ignore_errors=ignore_errors, skip_extensions=skip_extensions))
        
        return instances_ids
    
    def upload_folder_return_details(self, folder_path: str, unzip_before_upload: bool = False) -> (typing.Set, typing.Set, typing.List):
        '''
        Uploads all the files contained in the folder, including the ones in the sub-folders.
        Returns some details
        Parameters
        ----------
        folder_path: the folder to upload
        unzip_before_upload: if True, a zip file will be unzipped and all resulting files will be uploaded
                             (if False, the zip file will be uploaded as it is)

        Returns
        -------
        - A Set with all the StudyInstanceUID uploaded
        - A Set with all the Study orthanc Ids uploaded
        - A List with all the files names which were not correctly uploaded + corresponding error
        '''
        dicom_ids_set = set()
        orthanc_ids_set = set()
        rejected_files_list = []

        for path in os.listdir(folder_path):
            full_path = os.path.join(folder_path, path)
            if os.path.isfile(full_path):

                if unzip_before_upload and zipfile.is_zipfile(full_path):
                    with tempfile.TemporaryDirectory() as tempDir:
                        with zipfile.ZipFile(full_path, 'r') as z:
                            z.extractall(tempDir)
                        zip_dicom_ids_set, zip_orthanc_ids_set, zip_rejected_files_list = self.upload_folder_return_details(folder_path=tempDir)
                        dicom_ids_set.update(zip_dicom_ids_set)
                        orthanc_ids_set.update(zip_orthanc_ids_set)
                        rejected_files_list.extend(zip_rejected_files_list)
                else:
                    try:
                        instance_orthanc_ids = self.upload_file(full_path, ignore_errors=False)
                        for id in instance_orthanc_ids:
                            dicom_ids_set.add(self.instances.get_tags(id)["StudyInstanceUID"])
                            orthanc_ids_set.add(self.instances.get_parent_study_id(id))
                    except Exception as e:
                        rejected_files_list.append([str(full_path), str(e)])
            elif os.path.isdir(full_path):
                sub_dicom_ids_set, sub_orthanc_ids_set, sub_rejected_files_list = self.upload_folder_return_details(full_path)
                dicom_ids_set.update(sub_dicom_ids_set)
                orthanc_ids_set.update(sub_orthanc_ids_set)
                rejected_files_list.extend(sub_rejected_files_list)

        return dicom_ids_set, orthanc_ids_set, rejected_files_list
    
    def upload_files_dicom_web(self, paths: List[str], ignore_errors: bool = False) -> any:
        """Uploads a file to Orthanc through its DicomWeb API (only DICOM files, no zip files)

        Parameters
        ----------
        ignore_errors: if True: does not raise exceptions
        """
        logger.info(f"uploading {len(paths)} files through DicomWeb STOW-RS")

        files = {}
        counter = 1
        for path in paths:
            with open(path, 'rb') as f:
                raw_file = f.read()
                files[f'file{counter}'] = (str(path), raw_file, 'application/dicom')
                counter += 1

        body, content_type = encode_multipart_related(fields=files)
        r = self.post(endpoint="dicom-web/studies",
                      data=body,
                      headers = {
                          'Accept':'application/json',
                          'Content-Type': content_type
                      })
        return r.json()

    def lookup(self, needle: str, filter: str = None) -> List[str]:
        """searches the Orthanc DB for the 'needle'
        
        Parameters:
        ----------
        needle: the value to look for (may be a StudyInstanceUid, a PatientID, ...)
        filter: the only type returned, 'None' will return all types (Study, Patient, Series, Instance)

        Returns:
        -------
        the list of resources ids
        """
        response = self.post(
            endpoint="tools/lookup",
            data=needle
        )

        resources = []
        json_response = response.json()
        
        for r in json_response:
            if r['Type'] == 'Study' and (filter is None or filter == 'Study'):
                resources.append(r['ID'])
            elif r['Type'] == 'Patient' and (filter is None or filter == 'Patient'):
                resources.append(r['ID'])
            elif r['Type'] == 'Series' and (filter is None or filter == 'Series'):
                resources.append(r['ID'])
            elif r['Type'] == 'Instance' and (filter is None or filter == 'Instance'):
                resources.append(r['ID'])

        return resources

    def get_changes(self, since: int = None, limit: int = None) -> typing.Tuple[List[Change], int, bool]:
        """ get the changes

        Parameters:
        ----------
        since: request changes from this sequence_id
        limit: limit the number of changes in the response

        Returns:
        -------
        - the list of changes
        - the last sequence id returned
        - a boolean indicating if there are more changes to load
        """

        args = {}
        
        if since:
            args['since'] = since
        if limit:
            args['limit'] = limit

        response = self.get_json(
            endpoint="changes?" + urlencode(args)
        )

        changes = []
        for c in response['Changes']:
            changes.append(Change(
                change_type=c.get('ChangeType'),
                timestamp=datetime.datetime.strptime(c.get('Date'), "%Y%m%dT%H%M%S"),
                sequence_id=c.get('Seq'),
                resource_type=c.get('ResourceType'),
                resource_id=c.get('ID')
            ))
        done = response['Done']
        last_sequence_id = response['Last']

        return changes, last_sequence_id, done


    def create_pdf(self, pdf_path: str, dicom_tags: object, parent_id: str = None):
        """
        Creates an instance with an embedded pdf file.  If not parent_id is specified, this instance is part of a new study.

        dicom_tags = {
            'PatientID': '1234',
            'PatientName': 'Toto',
            'AccessionNumber': '1234',
            'PatientSex' : 'M',
            'PatientBirthDate' : '20000101',
            'StudyDescription': 'test'
            }
        )
        If you do not provide any value for 'SOPClassUID', the 'Encapsulated PDF Storage' will be used ('1.2.840.10008.5.1.4.1.1.104.1')

        Returns:
            the instance_orthanc_id of the created instance
        """
        if 'SOPClassUID' not in dicom_tags:
            dicom_tags['SOPClassUID'] = '1.2.840.10008.5.1.4.1.1.104.1'

        return self._create_instance_from_data_path(data_path = pdf_path,
                                                    content_type = 'application/pdf',
                                                    dicom_tags = dicom_tags,
                                                    parent_id = parent_id)

    def _create_instance_from_data_path(self, data_path: str, content_type: str, dicom_tags: object, parent_id: str = None):
        """
        Creates an instance with embedded data.  If not parent_id is specified, this instance is part of a new study.

        Returns:
            the instance_orthanc_id of the created instance
        """
        with open(data_path, 'rb') as f:
            content = f.read()

        return self._create_instance_from_data(content, content_type, dicom_tags, parent_id)

    def _create_instance_from_data(self, content: bytes, content_type: str, dicom_tags: object, parent_id: str = None):

        request_data = {
            'Tags': dicom_tags,
            'Content': "data:{content_type};base64,{data}".format(content_type = content_type, data = base64.b64encode(content).decode('utf-8'))
        }

        if parent_id is not None:
            request_data['Parent'] = parent_id

        response = self.post(
            endpoint = 'tools/create-dicom',
            json = request_data
        )
        return response.json()['ID']


    def create_instance_from_png(self, image_path: str, dicom_tags: object, parent_id: str = None):
        """
        Creates an instance with an embedded image.  If not parent_id is specified, this instance is part of a new study.

        Note: it is recommended to provide at least all these tags:
        dicom_tags = {
            'PatientID': '1234',
            'PatientName': 'Toto',
            'AccessionNumber': '1234',
            'PatientSex' : 'M',
            'PatientBirthDate' : '20000101',
            'StudyDescription': 'test',
            'Modality': 'MR'}
        )
        If you do not provide any value for 'SOPClassUID', the 'CR Image Storage' will be used ('1.2.840.10008.5.1.4.1.1.1')

        Returns:
            the instance_orthanc_id of the created instance
        """
        if 'SOPClassUID' not in dicom_tags:
            dicom_tags['SOPClassUID'] = '1.2.840.10008.5.1.4.1.1.1'

        return self._create_instance_from_data_path(data_path = image_path,
                                                    content_type = 'image/png',
                                                    dicom_tags = dicom_tags,
                                                    parent_id = parent_id)

    def create_instance_from_jpeg(self, image_path: str, dicom_tags: object, parent_id: str = None):
        """
        Creates an instance with an embedded image.  If not parent_id is specified, this instance is part of a new study.

        Note: it is recommended to provide at least all these tags:
        dicom_tags = {
            'PatientID': '1234',
            'PatientName': 'Toto',
            'AccessionNumber': '1234',
            'PatientSex' : 'M',
            'PatientBirthDate' : '20000101',
            'StudyDescription': 'test',
            'Modality': 'MR'}
        )
        If you do not provide any value for 'SOPClassUID', the 'CR Image Storage' will be used ('1.2.840.10008.5.1.4.1.1.1')

        Returns:
            the instance_orthanc_id of the created instance
        """

        if 'SOPClassUID' not in dicom_tags:
            dicom_tags['SOPClassUID'] = '1.2.840.10008.5.1.4.1.1.1'

        return self._create_instance_from_data_path(data_path = image_path,
                                                    content_type = 'image/jpeg',
                                                    dicom_tags = dicom_tags,
                                                    parent_id = parent_id)

    def get_all_labels(self):
        """
        List all the labels that are associated with any resource of the Orthanc database
        """
        return self.get_json(endpoint="tools/labels")

    def execute_lua_script(self, buffer: bytes):
        """
        Uploads the content of a binary buffer to be executed as a lua script

        Parameters:
            buffer: lua script content in a binary format

        Returns:
            The content of the response.
        """
        try:
            response = self.post('tools/execute-script', data=buffer)
            return response.content
        except HttpError as ex:
            if ex.http_status_code == 403:
                raise Forbidden(ex)
            else:
                raise ex

    def get_log_level(self):
        return LogLevel(self.get_binary(endpoint="tools/log-level").decode('utf-8'))

    def set_log_level(self, level: LogLevel):
        self.put(endpoint="tools/log-level", data=level)
        return LogLevel(self.get_binary(endpoint="tools/log-level").decode('utf-8'))
