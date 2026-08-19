from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from modules.storage.supplementary_db import load_dataframe, upsert_dataframe


class SupplementaryDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["POSTKALK_DB_PATH"] = str(Path(self.tempdir.name) / "test.db")

    def tearDown(self):
        os.environ.pop("POSTKALK_DB_PATH", None)
        self.tempdir.cleanup()

    def test_inserts_skips_duplicates_and_updates_changed_rows(self):
        initial = pd.DataFrame([
            {"Numer-Linia": "ABC-1", "Format": "A4"},
            {"Numer-Linia": "DEF-2", "Format": "A3"},
        ])
        stored, stats = upsert_dataframe("orders", initial, ("Numer-Linia",))
        self.assertEqual(stats, {"inserted": 2, "updated": 0, "unchanged": 0})
        self.assertEqual(len(stored), 2)

        _, stats = upsert_dataframe("orders", initial, ("Numer-Linia",))
        self.assertEqual(stats, {"inserted": 0, "updated": 0, "unchanged": 2})

        changed = pd.DataFrame([
            {"Numer-Linia": " abc-1 ", "Format": "A5"},
            {"Numer-Linia": "NEW-3", "Format": "A2"},
        ])
        stored, stats = upsert_dataframe("orders", changed, ("Numer-Linia",))
        self.assertEqual(stats, {"inserted": 1, "updated": 1, "unchanged": 0})
        self.assertEqual(len(stored), 3)
        formats = dict(zip(stored["Numer-Linia"].str.strip().str.casefold(), stored["Format"]))
        self.assertEqual(formats["abc-1"], "A5")

    def test_loads_existing_data_when_no_file_is_uploaded(self):
        upsert_dataframe("tektura", pd.DataFrame([{"job_name": "ZP1", "mindex": "M1"}]), ("job_name",))
        stored, stats = upsert_dataframe("tektura", None, ("job_name",))
        self.assertEqual(stats, {"inserted": 0, "updated": 0, "unchanged": 0})
        self.assertEqual(stored.to_dict("records"), [{"job_name": "ZP1", "mindex": "M1"}])
        self.assertEqual(len(load_dataframe("tektura")), 1)


if __name__ == "__main__":
    unittest.main()
