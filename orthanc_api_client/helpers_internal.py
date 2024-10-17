from io import BytesIO


def write_dataset_to_bytes(dataset) -> bytes:
    # create a buffer
    with BytesIO() as buffer:
        dataset.save_as(buffer)
        return buffer.getvalue()
