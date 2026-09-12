import unittest
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "database" / "quota_schema.sql"


class QuotaSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = SCHEMA_PATH.read_text(encoding="utf-8").lower()

    def test_schema_defines_read_and_reservation_functions(self):
        self.assertIn("function public.read_public_analysis_quota", self.schema)
        self.assertIn("function public.reserve_public_analysis", self.schema)

    def test_reservation_uses_row_locks_for_atomic_limits(self):
        self.assertGreaterEqual(self.schema.count("for update"), 3)
        self.assertIn("analysis_user_usage", self.schema)
        self.assertIn("analysis_daily_usage", self.schema)
        self.assertIn("analysis_global_usage", self.schema)

    def test_reservation_avoids_output_column_name_ambiguity(self):
        self.assertIn(
            "update public.analysis_daily_usage as d",
            self.schema,
        )
        self.assertIn("where d.usage_date = v_usage_date", self.schema)
        self.assertNotIn("on conflict (usage_date)", self.schema)

    def test_tables_are_not_accessible_to_public_users(self):
        self.assertGreaterEqual(
            self.schema.count("enable row level security"),
            3,
        )
        self.assertIn("from public, anon, authenticated", self.schema)
        self.assertIn("to service_role", self.schema)


if __name__ == "__main__":
    unittest.main()
