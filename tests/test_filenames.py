from unittest import TestCase

from club_management.filenames import sanitize_filename


class TestFilenames(TestCase):
    def test_filename_cleanup(self) -> None:
        self.assertEqual(
            sanitize_filename("Riegen/Übersicht: 2026.xlsx"),
            "Riegen_Übersicht_ 2026.xlsx",
        )
        self.assertEqual(sanitize_filename("CON.xlsx"), "_CON.xlsx")
