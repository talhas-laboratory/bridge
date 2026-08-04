from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.bridge_index import INDEX_JSON, INDEX_MD, build_index, main, write_index


class BridgeIndexTestCase(unittest.TestCase):
    def test_build_index_categorizes_core_and_packet_extension(self) -> None:
        index = build_index()
        module_ids = {module.module_id for module in index.modules}
        self.assertIn("reasoning_bridge.runtime", module_ids)
        self.assertIn("reasoning_bridge.extensions", module_ids)
        self.assertIn("reasoning_bridge.extensions.packet", module_ids)
        self.assertEqual(index.extensions, ["packet"])

        runtime = next(module for module in index.modules if module.module_id == "reasoning_bridge.runtime")
        self.assertEqual(runtime.category, "core")
        packet = next(
            module for module in index.modules if module.module_id == "reasoning_bridge.extensions.packet"
        )
        self.assertEqual(packet.category, "extension")
        self.assertEqual(packet.layer, "extension:packet")

        asset_ids = {asset.asset_id for asset in index.assets}
        self.assertIn("schema:context-packet.schema", asset_ids)
        self.assertIn("tool:bridge_index", asset_ids)
        self.assertIn("docs:AGENTS", asset_ids)

    def test_write_and_check_roundtrip(self) -> None:
        index = build_index()
        write_index(index)
        self.assertTrue(INDEX_JSON.exists())
        self.assertTrue(INDEX_MD.exists())
        payload = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
        self.assertEqual(payload["package"], "reasoning-bridge")
        self.assertIn("packet", payload["extensions"])
        self.assertEqual(main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
