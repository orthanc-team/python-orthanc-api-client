
v 0.4.0
=======

- BREAKING_CHANGE: renamed `dicom_servers.send` into `dicom_servers.send_asynchronous`
- added Job, JobType, JobStatus, JobInfo classes
- new resource `jobs` in api_client: `orthanc.jobs.get(orthanc_id=...)`