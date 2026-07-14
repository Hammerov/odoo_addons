import pathlib
import unittest


class ModuleUpgradeTest(unittest.TestCase):
    def test_manifest_targets_odoo_19(self):
        module_dir = pathlib.Path(__file__).resolve().parents[1]
        manifest_path = module_dir / "__manifest__.py"
        self.assertTrue(manifest_path.exists(), "Manifest file should exist")

        manifest_content = manifest_path.read_text(encoding="utf-8")
        self.assertIn("19.", manifest_content, "Module should target Odoo 19")

    def test_required_views_exist(self):
        module_dir = pathlib.Path(__file__).resolve().parents[1]
        required_files = [
            module_dir / "views" / "inherited_invoice.xml",
            module_dir / "views" / "inherited_purchase_order.xml",
            module_dir / "views" / "inherited_sale_order.xml",
            module_dir / "views" / "inherited_invoice_payment.xml",
        ]
        for file_path in required_files:
            self.assertTrue(file_path.exists(), f"Required view file is missing: {file_path.name}")


if __name__ == "__main__":
    unittest.main()
