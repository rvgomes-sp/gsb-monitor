import unittest
from mic.evidence import sha256_bytes,verify_and_parse
from mic.contracts import TransportEvidence,ReasonCode

class EvidenceTests(unittest.TestCase):
    def test_t14_identical_bytes_identical_sha(self): self.assertEqual(sha256_bytes(b"abc"),sha256_bytes(b"abc"))
    def test_t15_one_byte_changes_sha(self): self.assertNotEqual(sha256_bytes(b"abc"),sha256_bytes(b"abd"))
    def test_hash_before_parse(self):
        e=TransportEvidence("fixture://",200,b'{}',"0"*64,{},"a","b")
        self.assertEqual(verify_and_parse(e)[1],ReasonCode.HASH_DIVERGENTE)
