
v 0.8.0
=======

- **BREAKING CHANGE:** removed the `stow_rs` method from the `DicomWebServers` class

v 0.7.1
=======

- fixed absolute url in `upload` methods.

v 0.7.0
=======

- **BREAKING CHANGE:** renamed the `modality` argument of `client.modalities.send()` and 
  `client.modalities.store()` into `target_modality` to be more consistent with `send()` methods.


v 0.6.1
=======

- added `job.wait_completed()'

v 0.6.0
=======

- added `client.peers.send()'

v 0.5.8
=======

- **BREAKING CHANGE:** renamed `client.upload_file_dicom_web` into `client.upload_files_dicom_web`
  and added support for multiple files
- any HTTP status between 200 and 300 is now considered as a success and won't
  raise exceptions anymore

v 0.5.7
=======

- added `client.upload_file_dicom_web`

v 0.5.6
=======

- added `client.transfers.send`

v 0.5.5
=======

- fix relative url of various methods

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