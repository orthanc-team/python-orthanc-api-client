# python-orthanc-api-client

A python client to ease using the Orthanc Rest API.

Functionalities are very limited now !  Backward compat will break a lot in the near future !

Installation:

```
pip3 install orthanc-api-client
```


Examples:

```
from orthanc_api_client import OrthancApiClient

orthanc_a = OrthancApiClient('http://localhost:8042', user='orthanc', pwd='orthanc')
orthanc_b = OrthancApiClient('http://localhost:8043', user='orthanc', pwd='orthanc')

all_patients_ids = orthanc_a.patients.get_all_ids()
all_studies_ids = orthanc_a.studies.get_all_ids()
all_series_ids = orthanc_a.series.get_all_ids()
all_instances_ids = orthanc_a.instances.get_all_ids()

dicom_file = orthanc_a.instances.get_file(instance_id=all_instances_ids[0])

instances_ids = orthanc_b.upload(buffer=dicom_file)


```

## upload a folder to Orthanc
```
from orthanc_api_client import OrthancApiClient

o = OrthancApiClient('http://localhost:8042', user='orthanc', pwd='orthanc')
o.upload_folder('/home/o/files', ignore_errors=True)

```
