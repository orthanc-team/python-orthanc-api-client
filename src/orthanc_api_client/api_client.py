from http_client import HttpClient
from resources import Resources
from instances import Instances

class OrthancApiClient:

    def __init__(self, orthanc_url: str, user: str = None, pwd: str = None) -> None:

        self.http_client = HttpClient(root_url=orthanc_url, user=user, pwd=pwd)
        
        self.patients = Resources(http_client=self.http_client, url_segment='patients')
        self.studies = Resources(http_client=self.http_client, url_segment='studies')
        self.series = Resources(http_client=self.http_client, url_segment='series')
        self.instances = Instances(http_client=self.http_client)


    def upload_dicom(self, dicom) -> str:
        response = self.http_client.post('/instances', data=dicom).json()