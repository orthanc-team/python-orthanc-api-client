import re


class SimplifiedTags:

    def __init__(self, json_tags):
        self._tags_by_name = {}
        self._fill(json_tags)

    def _fill(self, json_tags: object):
        for name, value in json_tags.items():
            self._tags_by_name[name] = value

    def __getitem__(self, item):
        return self.get(item)

    def __contains__(self, name):
        return name in self._tags_by_name

    def get(self, name):
        return self._tags_by_name.get(name)


class Tags:

    def __init__(self, json_tags):
        self._raw_tags = json_tags
        self._tags_by_group_and_id = {}
        self._tags_by_name = {}
        self._fill(json_tags)

    def _fill(self, json_tags: object):
        for group_and_id, json_value in json_tags.items():
            name = json_value["Name"]
            type_ = json_value["Type"]
            value = json_value["Value"]
            if type_ == 'String':
                self._tags_by_group_and_id[group_and_id] = value
                self._tags_by_name[name] = value
            elif type_ == 'Sequence':
                sequence = TagsSequence(value)
                self._tags_by_group_and_id[group_and_id] = sequence
                self._tags_by_name[name] = sequence
            elif type_ == 'Null':
                self._tags_by_group_and_id[group_and_id] = None
                self._tags_by_name[name] = None

    def __getitem__(self, item):
        return self.get(item)

    def __contains__(self, accessor):
        return accessor in self._tags_by_name or accessor in self._tags_by_group_and_id

    def get(self, accessor):
        match_group_and_id = re.search('([0-9A-Fa-f]{4})[,-]([0-9A-Fa-f]{4})', accessor)
        if match_group_and_id:
            key = '{group},{id}'.format(group=match_group_and_id.group(1), id=match_group_and_id.group(2))
            return self._tags_by_group_and_id.get(key)
        else:
            return self._tags_by_name.get(accessor)

    def append(self, other: 'Tags'):
        self._fill(other._raw_tags)


class TagsSequence:
    def __init__(self, json_tags):
        self._raw_tags = json_tags
        self._sequence = []

        for json_item in json_tags:
            tags = Tags(json_item)
            self._sequence.append(tags)

    def __getitem__(self, item):
        return self.get(item)

    def get(self, index):
        return self._sequence[index]

