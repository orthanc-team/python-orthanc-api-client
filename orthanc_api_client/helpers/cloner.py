from orthanc_api_client import OrthancApiClient

class Cloner:

    def __init__(self, source: OrthancApiClient, destination: OrthancApiClient):
        self._source = source
        self._destination = destination



    def execute(self):
        all_patient_ids = self._source.patients.get_all_ids()
        instance_counter = 0

        for patient_id in all_patient_ids:
            studies_ids = self._source.studies.get_all_ids()

            for study_id in studies_ids:
                series_ids = self._source.series.get_all_ids()

                for series_id in series_ids:
                    instances_ids = self._source.instances.get_all_ids()

                    for instance_id in instances_ids:
                        dicom = self._source.instances.get_file(instance_id)

                        self._destination.upload_dicom(dicom)
                        instance_counter += 1
                        print(f"copied {instance_counter} {instance_id}")