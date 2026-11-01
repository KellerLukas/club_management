from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock

from O365.drive import Folder

from club_management.sharepoint import upload_file


class TestSharepoint(TestCase):
    def setUp(self) -> None:
        self.tmp_path = Path(self.enterContext(TemporaryDirectory()))

    def test_upload_applies_conflict_policy_to_small_files(self) -> None:
        path = self.tmp_path / "report.txt"
        path.write_text("Report")
        folder = Mock(spec=Folder)
        self.assertIs(upload_file(folder, path), folder.upload_file.return_value)
        folder.upload_file.assert_called_once_with(
            path, item_name=None, upload_in_chunks=True, conflict_handling="fail"
        )
