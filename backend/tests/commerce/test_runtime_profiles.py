"""No database or provider calls: fail-closed configuration boundary tests."""

import unittest
from app.commerce_runtime import CommerceRuntime


class RuntimeProfiles(unittest.TestCase):
    def test_isolated_references_remain_compatible(self):
        p = CommerceRuntime.from_environment(
            {
                "DATABASE_URL": "postgresql+psycopg://u:password@batchivo-db/batchivo_commerce_test",
                "COMMERCE_ISOLATED": "true",
            }
        )
        self.assertTrue(p.isolated)
        self.assertEqual(p.job_reference(468, 23), "WOO-TEST-468:23")
        self.assertEqual(p.square_base, "https://connect.squareupsandbox.com/v2")
        self.assertEqual(p.token_environment_key, "SQUARE_SANDBOX_ACCESS_TOKEN")

    def test_isolation_is_exact_not_substring(self):
        for url in [
            "postgresql://u:batchivo_commerce_test@postgres/batchivo",
            "postgresql://db/batchivo_commerce_test_other",
            "postgresql://db/batchivo_commerce_test/other",
            "sqlite:///batchivo_commerce_test",
        ]:
            with self.subTest(url=url), self.assertRaises(RuntimeError):
                CommerceRuntime.from_environment({"DATABASE_URL": url, "COMMERCE_ISOLATED": "true"})

    def test_effective_rls_target_cannot_bypass_isolation(self):
        env = {
            "DATABASE_URL": "postgresql://db/batchivo_commerce_test",
            "COMMERCE_ISOLATED": "true",
            "RLS_ENABLED": "true",
            "RLS_DATABASE_URL": "postgresql://postgres.batchivo.svc/batchivo",
        }
        with self.assertRaises(RuntimeError):
            CommerceRuntime.from_environment(env)

    def production(self):
        return {
            "COMMERCE_MODE": "production",
            "COMMERCE_ISOLATED": "false",
            "COMMERCE_PRODUCTION_ENABLED": "true",
            "COMMERCE_RELEASE_ID": "a" * 40,
            "DATABASE_URL": "postgresql+psycopg://u:secret@postgres.batchivo.svc.cluster.local/batchivo",
            "SQUARE_PRODUCTION_ACCESS_TOKEN": "fixture",
            "SQUARE_PRODUCTION_LOCATION_ID": "fixture-location",
        }

    def test_production_requires_each_activation_field(self):
        for key in self.production():
            env = self.production()
            env.pop(key)
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                CommerceRuntime.from_environment(env)

    def test_production_rejects_test_and_ambiguous_targets(self):
        for key, value in [
            ("COMMERCE_ISOLATED", "true"),
            ("COMMERCE_MODE", "staging"),
            ("COMMERCE_RELEASE_ID", "latest"),
            ("DATABASE_URL", "postgresql://db/batchivo_commerce_test"),
            ("DATABASE_URL", "postgresql://postgres/batchivo"),
            ("DATABASE_URL", "postgresql://postgres.batchivo.svc/another"),
        ]:
            env = self.production()
            env[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(RuntimeError):
                CommerceRuntime.from_environment(env)

    def test_activated_production_has_distinct_credentials_and_references(self):
        p = CommerceRuntime.from_environment(self.production())
        self.assertFalse(p.isolated)
        self.assertEqual(p.order_reference(468), "WOO-468")
        self.assertEqual(p.job_reference(468, 23), "WOO-468:23")
        self.assertEqual(p.square_base, "https://connect.squareup.com/v2")
        self.assertEqual(p.token_environment_key, "SQUARE_PRODUCTION_ACCESS_TOKEN")
        self.assertEqual(p.source, "woocommerce")

    def test_configuration_error_does_not_echo_credentials(self):
        env = self.production()
        env["DATABASE_URL"] = "postgresql://u:secret@unreviewed/batchivo"
        with self.assertRaises(RuntimeError) as ctx:
            CommerceRuntime.from_environment(env)
        self.assertNotIn("secret", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
