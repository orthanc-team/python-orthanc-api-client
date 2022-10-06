import os
import logging
import typing
import datetime
from typing import List
from urllib.parse import urlunsplit, urlencode

from .http_client import HttpClient
from .resources import Resources, Instances, Series, Studies, Jobs

from .helpers import wait_until, encode_multipart_related
from .exceptions import *
from .dicomweb_servers import DicomWebServers
from .modalities import DicomModalities
from .change import Change, ChangeType, ResourceType
from .transfers import Transfers
from .peers import Peers


logger = logging.getLogger('api-client')

    


class OrthancApiClient(HttpClient):

    def __init__(self, orthanc_root_url: str, user: str = None, pwd: str = None, api_token: str = None) -> None:
        """Creates an HttpClient

        Parameters
        ----------
        orthanc_root_url: base orthanc url: ex= 'http://localhost:8042'
        user: an orthanc user name (for basic Auth)
        pwd: the password for the orthanc user (for basic Auth)
        api_token: a token obtained from inside an Orthanc python plugin through OrthancPluginGenerateRestApiAuthorizationToken
                   format: 'Bearer 3d03892c-fe...' or '3d03892c-fe...'
        """
        headers = None
        if api_token:
            if api_token.startswith('Bearer '):
                header_value = api_token
            else:
                header_value = f'Bearer {api_token}'
            headers = {
                'authorization': header_value
            }
        super().__init__(root_url=orthanc_root_url, user=user, pwd=pwd, headers=headers)

        self.patients = Resources(api_client=self, url_segment='patients')
        self.studies = Studies(api_client=self)
        self.series = Series(api_client=self)
        self.instances = Instances(api_client=self)
        self.dicomweb_servers = DicomWebServers(api_client=self)
        self.modalities = DicomModalities(api_client=self)
        self.jobs = Jobs(api_client=self)
        self.transfers = Transfers(api_client=self)
        self.peers = Peers(api_client=self)

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

    def get_system(self) -> object:
        return self.get_json('system')

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
            endpoint = "/changes?" + urlencode(args)
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
