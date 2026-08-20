from __future__ import annotations

import unittest

from shared.merkle import canonicalize_json_text, hash_node


class MerkleTests(unittest.TestCase):
    def test_length_prefix_prevents_ambiguous_concatenation(self) -> None:
        self.assertNotEqual(hash_node("test", "ab", "c"), hash_node("test", "a", "bc"))

    def test_domain_separation_changes_digest(self) -> None:
        self.assertNotEqual(hash_node("scene-content", "x"), hash_node("scene-structure", "x"))

    def test_none_is_distinct_from_empty_string(self) -> None:
        self.assertNotEqual(hash_node("test", None), hash_node("test", ""))

    def test_numeric_types_have_canonical_distinct_encodings(self) -> None:
        self.assertNotEqual(hash_node("test", 1), hash_node("test", 1.0))
        self.assertNotEqual(hash_node("test", True), hash_node("test", 1))
        self.assertEqual(hash_node("test", 0.5), hash_node("test", float.fromhex("0x1p-1")))

    def test_json_key_order_is_canonicalized(self) -> None:
        first = canonicalize_json_text('{"nome":"Ana","idade":20}')
        second = canonicalize_json_text('{ "idade": 20, "nome": "Ana" }')
        self.assertEqual(first, second)
        self.assertEqual(hash_node("json", first), hash_node("json", second))


if __name__ == "__main__":
    unittest.main()
