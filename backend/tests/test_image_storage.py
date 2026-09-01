import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
