#from orthanc_api_client import OrthancApiClient


class Viewer:

    def __init__(
        self,
        id: str,
        description: str
    ):
        self.id = id
        self.description = description

    @classmethod
    def from_json(cls, data: dict) -> "Viewer":
        return cls(
            id=data["id"],
            description=data["description"]
        )


class Project:

    def __init__(
        self,
        api_client: 'OrthancApiClient',
        id: str,
        name: str,
        description: str,
        policy: str,
        primary_viewer: Viewer,
        secondary_viewers: list[Viewer],
        instructors: list[str],
        learners: list[str]):

        self._api_client = api_client
        self.id = id
        self.name = name
        self.description = description
        self.policy = policy
        self.primary_viewer = primary_viewer
        self.secondary_viewers = secondary_viewers
        self.instructors = instructors
        self.learners = learners

    @classmethod
    def from_json(cls, api_client: 'OrthancApiClient', data: dict) -> "Project":
        return cls(
            api_client=api_client,
            id=data["id"],
            name=data["name"],
            description=data["description"],
            policy=data["policy"],
            primary_viewer=Viewer(data["primary_viewer"], data["primary_viewer"]),
            secondary_viewers=[
                Viewer.from_json(v)
                for v in data.get("secondary_viewers", [])
            ],
            instructors=data.get("instructors", []),
            learners=data.get("learners", [])
        )