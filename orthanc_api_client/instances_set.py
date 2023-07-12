from typing import Optional, List, Any
from .study import Study
from .series import Series
from .instance import Instance
from .job import Job
import hashlib
import base64

# This class contains a set of Instances that represents the status of a study at a given time.
# Its main use is to avoid this kind of situation:
# - you wish to modify a study, forward it and delete it
# - if new instances are received while you are processing the study and you simply "delete"
#   the whole study at the end, you might delete instances that have not been processed.
# The InstancesSet makes a snapshot of the current state of a study to make sure you'll
# process, forward and delete only the instances from the snapshot


class InstancesSet:

    def __init__(self, api_client: 'OrthancApiClient', id: str = None):
        self.api_client = api_client
        self._id = id
        self._computed_id = None
        self._all_instances_ids = []
        self._by_series = {}
        self.study_id = None

    def __str__(self):
        return f"{self.id} - {len(self.series_ids)} series / {len(self.instances_ids)} instances"

    def add_series(self, series_id: str):
        self._add_series(
            series_id=series_id,
            instances_ids=self.api_client.series.get_instances_ids(orthanc_id=series_id)
        )

    def _add_series(self, series_id: str, instances_ids: List[str]):
        self._by_series[series_id] = instances_ids
        self._all_instances_ids.extend(instances_ids)
        self._computed_id = None  # invalidate the computed id

    @property
    def id(self) -> str:
        if not self._computed_id:
            self._computed_id = base64.b16encode(hashlib.sha1(",".join(self._all_instances_ids).encode('utf-8')).digest())[:10].decode('utf-8')
        return self._computed_id

    @property
    def instances_ids(self) -> List[str]:
        return self._all_instances_ids

    @property
    def series_ids(self) -> List[str]:
        return list(self._by_series.keys())

    def get_instances_ids(self, series_id: str) -> List[str]:
        if series_id in self._by_series:
            return self._by_series[series_id]
        else:
            return []

    @staticmethod
    def from_study(api_client, study_id: Optional[str] = None, study: Optional[Study] = None) -> 'InstancesSet':
        instances_set = InstancesSet(api_client=api_client)
        if not study:
            study = api_client.studies.get(study_id)
        instances_set.study_id = study.orthanc_id

        for series_id in study.info.series_ids:
            instances_set.add_series(series_id)

        return instances_set

    @staticmethod
    def from_series(api_client, series_id: Optional[str] = None, series: Optional[Series] = None) -> 'InstancesSet':
        instances_set = InstancesSet(api_client=api_client)
        if not series:
            series = api_client.series.get(series_id)

        instances_set.study_id = series.study.orthanc_id
        instances_set.add_series(series_id=series.orthanc_id)

        return instances_set

    @staticmethod
    def from_instance(api_client, instance_id: Optional[str] = None, instance: Optional[Instance] = None) -> 'InstancesSet':
        instances_set = InstancesSet(api_client=api_client)
        if not instance:
            instance = api_client.instances.get(instance_id)

        instances_set.study_id = instance.series.study.orthanc_id
        instances_set._by_series[instance.series.orthanc_id] = [instance.orthanc_id]
        instances_set._all_instances_ids.append(instance.orthanc_id)

        return instances_set

    def delete(self):
        self.api_client.post(
            endpoint=f"tools/bulk-delete",
            json= {
                "Resources": self.instances_ids
            })

    # returns a new InstancesSet with the modified resources
    def modify(self, replace_tags: Any = {}, remove_tags: List[str] = [], keep_tags: List[str] = [], keep_source=True, force=False) -> Optional['InstancesSet']:

        query = {
            "Force": force,
            "Resources": self.instances_ids,
            "KeepSource": keep_source,
            "Level": "Instance"
        }

        if replace_tags is not None and len(replace_tags) > 0:
            query['Replace'] = replace_tags
        if remove_tags is not None and len(remove_tags) > 0:
            query['Remove'] = remove_tags
        if keep_tags is not None and len(keep_tags) > 0:
            query['Keep'] = keep_tags

        r = self.api_client.post(
            endpoint=f"tools/bulk-modify",
            json=query)

        if r.status_code == 200:
            rjson = r.json()

            # create the modified set from the response
            modified_set = InstancesSet(api_client=self.api_client)
            modified_instances_ids = []
            modified_series_ids = []
            modified_studies_ids = []
            for r in rjson['Resources']:
                if r['Type'] == 'Study':
                    modified_studies_ids.append(r['ID'])
                if r['Type'] == 'Series':
                    modified_series_ids.append(r['ID'])
                if r['Type'] == 'Instance':
                    modified_instances_ids.append(r['ID'])

            if len(modified_studies_ids) != 1:
                return None  # we had a problem since there should be only one study !!!
            if len(modified_series_ids) != len(self._by_series.keys()):
                return None  # we had a problem since the number of series has changed !!!
            if len(modified_instances_ids) != len(self._all_instances_ids):
                return None  # we had a problem since the number of instances has changed !!!

            for s in modified_series_ids:
                series_all_instances_ids = set(self.api_client.series.get_instances_ids(orthanc_id=s))

                # the series might contain some instances that do not come from our modification, ignore them !
                series_instances_ids = list(series_all_instances_ids.intersection(set(modified_instances_ids)))
                modified_set._by_series[s] = series_instances_ids
                modified_set._all_instances_ids.extend(series_instances_ids)

            modified_set.study_id = modified_studies_ids[0]

            return modified_set

        return None  # TODO: raise exception ???

    # keep only the instances that satisfy the filter
    # prototype: filter(api_client, instance_id)
    # this method returns an InstanceSet containing the removed instances and series
    # example: filter_out_sets = s.filter_instances(filter=lambda api, id: api.instances.get(id).tags.get('SeriesDescription') == "keep this description")
    def filter_instances(self, filter) -> 'InstancesSet':
        series_to_delete = []
        removed_set = InstancesSet(self.api_client)
        removed_set.study_id = self.study_id

        for series_id, instances_ids in self._by_series.items():
            instances_to_delete = []
            for instance_id in instances_ids:
                if not filter(self.api_client, instance_id):
                    instances_to_delete.append(instance_id)

            for i in instances_to_delete:
                self._by_series[series_id].remove(i)
                self._all_instances_ids.remove(i)

            if len(self._by_series[series_id]) == 0:
                series_to_delete.append(series_id)

            if len(instances_to_delete) > 0:
                removed_set._add_series(series_id, instances_to_delete)

        for s in series_to_delete:
            del self._by_series[s]

        return removed_set

    # apply a method on all instances
    # prototype: processor(api_client, instance_id)
    def process_instances(self, processor):
        for instance_id in self._all_instances_ids:
            processor(self.api_client, instance_id)

    def download_archive(self, path: str):
        response = self.api_client.post(
            endpoint="tools/create-archive",
            json={
                "Synchronous": True,
                "Resources": self.instances_ids
            }
        )
        with open(path, 'wb') as f:
            f.write(response.content)

    def download_media(self, path: str):
        response = self.api_client.post(
            endpoint="tools/create-media",
            json={
                "Synchronous": True,
                "Resources": self.instances_ids
            }
        )
        with open(path, 'wb') as f:
            f.write(response.content)
