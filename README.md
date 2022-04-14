# python-orthanc-api-client

A python client to ease using the Orthanc Rest API.

Functionalities are very limited now !  Backward compat will break a lot in the near future !

Installation:

```shell
pip3 install orthanc-api-client
```


Examples:

```python
from orthanc_api_client import OrthancApiClient

orthanc_a = OrthancApiClient('http://localhost:8042', user='orthanc', pwd='orthanc')
orthanc_b = OrthancApiClient('http://localhost:8043', user='orthanc', pwd='orthanc')

all_patients_ids = orthanc_a.patients.get_all_ids()
all_studies_ids = orthanc_a.studies.get_all_ids()
all_series_ids = orthanc_a.series.get_all_ids()
all_instances_ids = orthanc_a.instances.get_all_ids()

dicom_file = orthanc_a.instances.get_file(orthanc_id=all_instances_ids[0])

instances_ids = orthanc_b.upload(buffer=dicom_file)
study_id = orthanc_b.instances.get_parent_study_id(instances_ids[0])

orthanc_a.instances.set_metadata(orthanc_id=all_instances_ids[0], 
                                 metadata_name=1024, 
                                 content='my-value')

tags = orthanc_a.instances.get_tags(orhtanc_id=all_instances_ids[0])

patient_name = tags['PatientName']
patient_id = tags['0010,0020']
patient_sex = tags['0010-0040']

anon_study_id = orthanc_b.studies.anonymize(
    orthanc_id=study_id,
    keep_tags=['PatientName'],
    replace_tags={
        'PatientID': 'ANON'
    },
    force=True,
    delete_original=False
)


```

## upload a folder to Orthanc

```python
from orthanc_api_client import OrthancApiClient

o = OrthancApiClient('http://localhost:8042', user='orthanc', pwd='orthanc')
o.upload_folder('/home/o/files', ignore_errors=True)

```

## running from inside an Orthanc python plugin

```python
from orthanc_api_client import OrthancApiClient
import orthanc
import json

orthanc_client = None



def OnChange(changeType, level, resource):
    global orthanc_client

    if changeType == orthanc.ChangeType.ORTHANC_STARTED:
        orthanc.LogWarning("Starting python plugin")

        # at startup, use the python SDK direct access to the Rest API to retrieve info to pass to the OrthancApiClient that is using 'requests'
        system = json.loads(orthanc.RestApiGet('/system'))
        api_token = orthanc.GenerateRestApiAuthorizationToken()

        orthanc_client = OrthancApiClient(
            orthanc_root_url=f"http://localhost:{system['HttpPort']}",
            api_token=api_token
        )
        ...

orthanc.RegisterOnChangeCallback(OnChange)
```