# python-orthanc-api-client

A python client to ease using the Orthanc Rest API.

Functionalities are very limited now !  Backward compat will break a lot in the near future !

Installation:

```shell
pip3 install orthanc-api-client
```


Examples:

```python
from orthanc_api_client import OrthancApiClient, ResourceType
import datetime

orthanc_a = OrthancApiClient('http://localhost:8042', user='orthanc', pwd='orthanc')
orthanc_b = OrthancApiClient('http://localhost:8043', user='orthanc', pwd='orthanc')

if not orthanc_a.wait_started(timeout=20):
    print("Orthanc has not started after 20 sec")

if not orthanc_a.is_alive():
    print("Could not connect to Orthanc, check it is running")

# upload files/folders
orthanc_a.upload_folder('/home/o/files', ignore_errors=True)
instances_ids = orthanc_a.upload_file('/home/o/files/a.dcm')
instances_ids = orthanc_a.upload_file('/home/o/files/a.zip')
with open('/home/o/files/a.dcm', 'rb') as f:
    instances_ids = orthanc_a.upload(f.read())
orthanc_a.upload_files_dicom_web(['/home/o/files/a.dcm'])
    
# list all resources ids
all_patients_ids = orthanc_a.patients.get_all_ids()
all_studies_ids = orthanc_a.studies.get_all_ids()
all_series_ids = orthanc_a.series.get_all_ids()
all_instances_ids = orthanc_a.instances.get_all_ids()

# show some daily stats
orthanc_a.studies.print_daily_stats(from_date=datetime.date(2022, 2, 4), to_date=datetime.date(2022, 2, 8))
orthanc_a.series.print_daily_stats() # show last 8 days per default
orthanc_a.instances.print_daily_stats()

# instances methods
dicom_file = orthanc_a.instances.get_file(orthanc_id=all_instances_ids[0])
instances_ids = orthanc_b.upload(buffer=dicom_file)
study_id = orthanc_b.instances.get_parent_study_id(instances_ids[0])

# access study info & simplified tags
study = orthanc_b.studies.get(study_id)
patient_id = study.patient_main_dicom_tags.get('PatientID')
study_description = study.main_dicom_tags.get('StudyDescription')
dicom_id = study.dicom_id

# access metadata
orthanc_a.instances.set_metadata(orthanc_id=all_instances_ids[0], 
                                 metadata_name=1024, 
                                 content='my-value')

# access tags
tags = orthanc_a.instances.get_tags(orhtanc_id=all_instances_ids[0])
patient_name = tags['PatientName']
patient_id = tags['0010,0020']
patient_sex = tags['0010-0040']

# anonymize
anon_study_id = orthanc_b.studies.anonymize(
    orthanc_id=study_id,
    keep_tags=['PatientName'],
    replace_tags={
        'PatientID': 'ANON'
    },
    force=True,
    delete_original=False
)

# find locally in Orthanc
study_id = orthanc_a.studies.lookup(dicom_id='1.2.3.4')
study_id = orthanc_a.studies.lookup(dicom_id='1.2.3.4', filter="Study")

studies = orthanc_a.studies.find(query={
    'PatientName': 'A*', 
    'StudyDate': '20220101-20220109'
})

# find in a remote modality
remote_studies = orthanc_a.modalities.query_studies(
    from_modality='pacs',
    query={'PatientName': 'A*', 'StudyDate': '20220101-20220109'}
)
orthanc_a.modalities.retrieve_study(
    from_modality=remote_studies[0].remote_modality_id,
    dicom_id=remote_studies[0].dicom_id
)

# send to a remote modality
orthanc_a.modalities.send(
    modality='orthanc-b',
    resources_ids=[study_id],
    synchronous=True
)

# send to a remote peer (synchronous)
orthanc_a.peers.send(
    target_peer='orthanc-b',
    resources_ids=[study_id]
)

# send using transfer plugin
orthanc_a.transfers.send(
    target_peer='orthanc-b',
    resources_ids=[study_id],
    resource_type=ResourceType.STUDY,
    compress=True
)

```

## helpers methods

```python
import datetime
from orthanc_api_client import helpers, OrthancApiClient

dicom_date = helpers.to_dicom_date(datetime.date.today())
standard_date = helpers.from_dicom_date(dicom_date)

# for tests:
o = OrthancApiClient('http://localhost:8042', user='orthanc', pwd='orthanc')
helpers.wait_until(lambda: len(o.instances.get_all_ids() > 50), timeout=30)

dicom_date = helpers.get_random_dicom_date(date_from=datetime.date(2000, 1, 1),
                                           date_to=datetime.date.today())
dicom_file = helpers.generate_test_dicom_file(width=128,
                                              height=128,
                                              tags={
                                                  "PatientName": "Toto",
                                                  "StudyInstanceUID": "123"
                                              })

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