class DownloadedInstance:
    """
    A structure to store the info about a downloaded file:
    - its instance id
    - the path where it has been downloaded
    """

    def __init__(self, instance_id, path):
        self.instance_id = instance_id
        self.path = path

    def __str__(self):
        return self.instance_id