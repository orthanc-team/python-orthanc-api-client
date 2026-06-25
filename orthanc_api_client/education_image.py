from typing import Any


class Image:
    def __init__(
        self,
        level: str,
        preview_url: str,
        projects: list[str],
        resource_id: str,
        series_instance_uid: str,
        sop_instance_uid: str,
        study_instance_uid: str,
        title: str,
    ) -> None:
        self.level: str = level
        self.preview_url: str = preview_url
        self.projects: list[str] = projects
        self.resource_id: str = resource_id
        self.series_instance_uid: str = series_instance_uid
        self.sop_instance_uid: str = sop_instance_uid
        self.study_instance_uid: str = study_instance_uid
        self.title: str = title

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Image":
        return cls(
            level=data["level"],
            preview_url=data["preview_url"],
            projects=data["projects"],
            resource_id=data["resource-id"],
            series_instance_uid=data["series-instance-uid"],
            sop_instance_uid=data["sop-instance-uid"],
            study_instance_uid=data["study-instance-uid"],
            title=data["title"],
        )

    # def __repr__(self) -> str:
    #     return (
    #         f"Series("
    #         f"title='{self.title}', "
    #         f"resource_id='{self.resource_id}'"
    #         f")"
    #     )