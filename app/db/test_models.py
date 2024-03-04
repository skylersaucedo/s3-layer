import datetime
import uuid

from app.db.models import DatasetObject


def test_dataset_object():
    dataset_object = DatasetObject(
        id=uuid.uuid4(),
        name=uuid.uuid4(),
        s3_object_name="test.jpg",
        content_type="image/jpeg",
        upload_date=datetime.datetime.now(),
        modified_date=datetime.datetime.now(),
        file_hash_sha1="test",
    )

    assert dataset_object.id
    assert dataset_object.name
    assert dataset_object.s3_object_name
    assert dataset_object.content_type
    assert dataset_object.upload_date
    assert dataset_object.modified_date
    assert dataset_object.file_hash_sha1
    assert dataset_object.__repr__()
    assert dataset_object.__str__()


def test_clean_polygons():
    assert DatasetObject.clean_polygons(
        [
            {"x": 1, "y": 2},
            {"left": 3, "top": 4},
        ]
    ) == [
        {"x": 1, "y": 2},
        {"x": 3, "y": 4},
    ]

    assert DatasetObject.clean_polygons(
        [
            {"x": 1, "y": 2},
            {"left": 3, "top": 4},
            {"x": 5, "y": 6},
        ]
    ) == [
        {"x": 1, "y": 2},
        {"x": 3, "y": 4},
        {"x": 5, "y": 6},
    ]

    assert DatasetObject.clean_polygons(
        [
            {"x": 1, "y": 2},
            {"left": 3, "top": 4},
            {"x": 5, "y": 6},
            {"left": 7, "top": 8},
        ]
    ) == [
        {"x": 1, "y": 2},
        {"x": 3, "y": 4},
        {"x": 5, "y": 6},
        {"x": 7, "y": 8},
    ]

    assert DatasetObject.clean_polygons([]) == []
    assert DatasetObject.clean_polygons(None) == []
    assert DatasetObject.clean_polygons("invalid") == []


def test_polygon_string_to_json():
    assert DatasetObject.polygon_string_to_json("[]") == []
    assert DatasetObject.polygon_string_to_json('[{"x": 1, "y": 2}]') == [
        {"x": 1, "y": 2}
    ]
    assert DatasetObject.polygon_string_to_json(
        '[{"x": 1, "y": 2}, {"x": 3, "y": 4}]'
    ) == [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
    assert DatasetObject.polygon_string_to_json("") == []
    assert DatasetObject.polygon_string_to_json(None) == []
    assert DatasetObject.polygon_string_to_json("invalid") == []
