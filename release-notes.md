v 0.14.10
========

- added functions to check the Orthanc and plugin versions:
  `helpers.is_version_at_least`, `OrthancApiClient.is_orthanc_version_at_least`
  `OrthancApiClient.is_plugin_version_at_least`, `OrthancApiClient.has_loaded_plugin`.

v 0.14.8
========

- added `helpers.from_dicom_date_and_time` and `helpers.from_dicom_time`

v 0.14.6
========

- added a `RemoteJob` class that can be created when a `PULL_TRANSFER` is created

v 0.14.5
========

- added `get_statistics()` in `OrthancApiClient`

v 0.14.4
========

- `ignore_errors` in `upload` methods now ignoring 409 errors (conflict)

v 0.14.3
========

- added `get_log_level` and `set_log_level` in `OrthancApiClient`

v 0.14.2
========

- added `execute_lua_script` in `OrthancApiClient`


v 0.14.1
========

- introduced `patients`

v 0.14.0
========

- **BREAKING CHANGE:** `DicomModalities.send_async` was actually not asynchronous and 
  now returns a job.

v 0.13.8
========

- added `local_aet` arg for `DicomModalities.send` and `DicomModalities.send_async`

v 0.13.7
========

- added `Study.last_update`


v 0.13.6
========

- added `headers` arg to the `OrthancApiClient` constructor

v 0.13.5
========

- added `Resources.download_media()` and `Resources.download_archive()` 
- added `InstancesSet.download_media()` and `InstancesSet.download_archive()` 

v 0.13.4
========

- added `Modalities.get_all_ids()`
- added `Modalities.get_id_from_aet()`
- added `Study.info.patient_orthanc_id`
- added `Resources.exists()`

v 0.13.3
========

- added `Studies.get_modalities` and `Studies.get_first_instance_tags()`

v 0.13.2
========

- `Modalities.send` and `Modalities.store`:
  - `timeout` is now a float argument (more pythonic) 
- added `keep_tags` argument to `modify()`


v 0.13.1
========

- added `get_labels`, `add_label`, `add_labels`, `delete_label`, `delete_labels`
  at all resources levels
- added `OrthancApiClient.get_all_labels` to return all labels in Orthanc
- added `labels` and `label_constraint` arguments to `studies.find`

v 0.12.2
========

- `Modalities.send` and `Modalities.store`:
  - **BREAKING CHANGE:** removed `synchronous` argument: it is always synchronous
  - added an optional `timeout` argument

v 0.11.8
========

- `InstancesSet` ids are reproducible (based on a hash of their initial content)
- more detailed HttpError

v 0.11.7
========

- fix `Series.statistics` and `Study.statistics`
- uniformized logger names to `__name__`

v 0.11.5
========
- added `Modalities.configure`, `Modalities.delete` and `Modalities.get_configuration`

v 0.11.4
========
- fix `InstancesSet.filter_instances`

v 0.11.3
========
- fix metadata default value

v 0.11.2
========

- added `keep_tags` to `Instances.modify`

v 0.11.1
========

- added `InstancesSet.id`
- `InstancesSet.api_client` is now public

v 0.11.0
========

- **BREAKING CHANGE:** renamed `dicomweb_servers.send_asynchronous` into `dicomweb_servers.send_async`
- for every target (`peers, transfers, modalities, dicomweb_server`) we now have both:
  - `send()` that is synchronous
  - and `send_async()` that is asynchronous and returns the job that has been created

v 0.10.2
========

- added synchronous `dicomweb_servers.send()`

v 0.10.1
========

- InstancesSet.filter_instances() now returns and instance set with the excluded instances

v 0.10.0
========

- **BREAKING CHANGE:** renamed `set_metadata` into `set_string_metadata` & `set_binary_metadata`
- **BREAKING CHANGE:** renamed `get_metadata` into `get_string_metadata` & `get_binary_metadata`
- added `InstancesSet.filter_instances()` & `InstancesSet.process_instances()` 

v 0.9.1
=======

- introduced `InstancesSet` class

v 0.9.0
=======

- **BREAKING CHANGE:** renamed `download_study` and `download_series` into `download_instances`
- introduced `Series`, `SeriesInfo`, `Instance` and `InstanceInfo` classes

v 0.8.3
=======

- added download methods for instances, series, studies

v 0.8.2
=======

- added pdf (and png/jpg) import tools

v 0.8.1
=======

- made HttpClient available for lib users

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