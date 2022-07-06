v 0.5.5
=======

- fix relative url

v 0.5.4
=======

- fix relative url

v 0.5.3
=======

- added `timeout` argument to `is_alive()`

v 0.5.2
=======

- fixed relative url in `studies.merge`

v 0.5.1
=======

- added `studies.merge`

v 0.5.0
=======

- BREAKING_CHANGE: renamed `relative_url` arg into `endpoint` for `get, put, post, get_json, ...`
- added `retry, cancel, pause, ...` to `jobs`

v 0.4.1
=======

- added `ignore_errors` to `delete` methods

v 0.4.0
=======

- BREAKING_CHANGE: renamed `dicom_servers.send` into `dicom_servers.send_asynchronous`
- added Job, JobType, JobStatus, JobInfo classes
- new resource `jobs` in api_client: `orthanc.jobs.get(orthanc_id=...)`