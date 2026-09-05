import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend import image_storage


class ImageStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.upload_directory = Path(self.temporary_directory.name)
        self.directory_patch = patch.object(
            image_storage,
            "UPLOAD_DIRECTORY",
            self.upload_directory,
        )
        self.directory_patch.start()

    def tearDown(self):
        self.directory_patch.stop()
        self.temporary_directory.cleanup()

    def test_delete_rejects_external_and_unsafe_paths(self):
        self.assertFalse(
            image_storage.delete_uploaded_property_image(
                "https://images.example.com/home.jpg"
            )
        )
        self.assertFalse(
            image_storage.delete_uploaded_property_image(
                "/uploads/property-images/../outside.jpg"
            )
        )

    def test_delete_removes_local_upload_and_handles_missing_file(self):
        image_path = self.upload_directory / "owner_image.png"
        image_path.write_bytes(b"image")

        self.assertTrue(
            image_storage.delete_uploaded_property_image(
                "/uploads/property-images/owner_image.png"
            )
        )
        self.assertFalse(image_path.exists())
        self.assertFalse(
            image_storage.delete_uploaded_property_image(
                "/uploads/property-images/owner_image.png"
            )
        )

    def test_disk_error_is_logged_without_escaping_after_database_commit(self):
        image_path = self.upload_directory / "locked_image.png"
        image_path.write_bytes(b"image")

        with patch.object(Path, "unlink", side_effect=PermissionError("locked")):
            with self.assertLogs("backend.image_storage", level="WARNING") as logs:
                deleted = image_storage.delete_uploaded_property_image(
                    "/uploads/property-images/locked_image.png"
                )

        self.assertFalse(deleted)
        self.assertIn("locked_image.png", logs.output[0])
        self.assertIn("locked", logs.output[0])


    def test_s3_upload_and_delete_use_the_same_object_key(self):
        client = Mock()
        settings = {
            "PROPERTY_IMAGE_STORAGE": "s3",
            "OBJECT_STORAGE_BUCKET": "habitard-images",
            "OBJECT_STORAGE_ACCESS_KEY_ID": "access",
            "OBJECT_STORAGE_SECRET_ACCESS_KEY": "secret",
            "OBJECT_STORAGE_PUBLIC_BASE_URL": "https://images.habitard.test",
        }
        image_url = image_storage.store_property_image(
            "7_home.png", b"image", "image/png", settings=settings, client=client
        )
        self.assertEqual(image_url, "https://images.habitard.test/property-images/7_home.png")
        self.assertTrue(image_storage.delete_uploaded_property_image(
            image_url, settings=settings, client=client
        ))
        self.assertEqual(client.put_object.call_args.kwargs["Key"], "property-images/7_home.png")
        client.delete_object.assert_called_once_with(
            Bucket="habitard-images", Key="property-images/7_home.png"
        )

    def test_s3_configuration_rejects_missing_or_insecure_values(self):
        with self.assertRaises(RuntimeError):
            image_storage.validate_object_storage_settings({"PROPERTY_IMAGE_STORAGE": "s3"})
        with self.assertRaises(RuntimeError):
            image_storage.validate_object_storage_settings({
                "PROPERTY_IMAGE_STORAGE": "s3",
                "OBJECT_STORAGE_BUCKET": "bucket",
                "OBJECT_STORAGE_ACCESS_KEY_ID": "access",
                "OBJECT_STORAGE_SECRET_ACCESS_KEY": "secret",
                "OBJECT_STORAGE_PUBLIC_BASE_URL": "http://images.example.test",
            })


if __name__ == "__main__":
    unittest.main()
