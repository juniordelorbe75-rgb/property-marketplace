import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from backend.image_maintenance import cleanup_orphaned_uploads


class ImageMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.now = datetime(2026, 8, 29, tzinfo=timezone.utc)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def make_old_file(self, name: str):
        path = self.directory / name
        path.write_bytes(b"test")
        old_timestamp = (self.now - timedelta(hours=48)).timestamp()
        os.utime(path, (old_timestamp, old_timestamp))
        return path

    def make_session(self, image_urls):
        scalar_result = Mock()
        scalar_result.all.return_value = [SimpleNamespace(image_urls=image_urls)]
        session = Mock()
        session.scalars.return_value = scalar_result
        return session

    def test_dry_run_reports_old_orphans_without_deleting(self):
        referenced = self.make_old_file("1_referenced.png")
        orphan = self.make_old_file("1_orphan.png")
        stale_temporary = self.make_old_file(".upload-crashed.tmp")
        recent = self.directory / "1_recent.png"
        recent.write_bytes(b"recent")
        unrelated = self.make_old_file("notes.txt")
        session = self.make_session(
            ["/uploads/property-images/1_referenced.png"]
        )

        result = cleanup_orphaned_uploads(
            session,
            directory=self.directory,
            now=self.now,
        )

        self.assertEqual(
            result["candidates"],
            [".upload-crashed.tmp", "1_orphan.png"],
        )
        self.assertEqual(result["deleted"], [])
        for path in (referenced, orphan, stale_temporary, recent, unrelated):
            self.assertTrue(path.exists())

    def test_delete_mode_removes_only_safe_candidates(self):
        referenced = self.make_old_file("2_referenced.webp")
        orphan = self.make_old_file("2_orphan.jpg")
        session = self.make_session(
            ["/uploads/property-images/2_referenced.webp"]
        )

        result = cleanup_orphaned_uploads(
            session,
            directory=self.directory,
            now=self.now,
            delete=True,
        )

        self.assertEqual(result["deleted"], ["2_orphan.jpg"])
        self.assertTrue(referenced.exists())
        self.assertFalse(orphan.exists())


if __name__ == "__main__":
    unittest.main()
