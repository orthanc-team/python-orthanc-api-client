import os
import logging
from typing import List

from .http_client import HttpClient
from .resources import Resources
from .instances import Instances
from .helpers import wait_until
from .exceptions import *


logger = logging.getLogger('api-client')


class OrthancApiClient:

    def __init__(self, orthanc_url: str, user: str = None, pwd: str = None) -> None:

        self.http_client = HttpClient(root_url=orthanc_url, user=user, pwd=pwd)
        
        self.patients = Resources(http_client=self.http_client, url_segment='patients')
        self.studies = Resources(http_client=self.http_client, url_segment='studies')
        self.series = Resources(http_client=self.http_client, url_segment='series')
        self.instances = Instances(http_client=self.http_client)

    def wait_started(self, timeout: float = None):
        wait_until(self.is_alive, timeout)

    def is_alive(self) -> bool:
        """Checks if the orthanc server can be reached.
        
        Returns
        -------
            True if orthanc can be reached, False otherwise
        """
        try:
            # if we get an answer to a basic request, it means the server is alive
            self.http_client.get('system', timeout = 0.1)
            return True
        except Exception as e:
            return False

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
            response = self.http_client.post('/instances', data=buffer)
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
        the list of instances ids (one if a single file, can be multiple )
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
                instances_ids.extend(self.upload_folder(full_path, ignore_errors=ignore_errors))
        
        return instances_ids