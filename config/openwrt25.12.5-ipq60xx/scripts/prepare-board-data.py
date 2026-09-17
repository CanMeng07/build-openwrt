import base64
import gzip
import hashlib
import os
from pathlib import Path

root = Path(__file__).resolve().parent.parent
encoded = os.environ.pop('ZN_M2_BOARD_DATA_GZ_B64', '')
if not encoded:
    raise SystemExit('Missing current-device board data input ZN_M2_BOARD_DATA_GZ_B64')
data = gzip.decompress(base64.b64decode(encoded, validate=True))
expected = '52f1094dd3279bab95bf3845be273854fa4f2daa8595ca0b26e1be0e19fa6948'
if hashlib.sha256(data).hexdigest() != expected:
    raise SystemExit('Current-device board data SHA-256 mismatch')
(root / 'packages/ipq-wifi-zn-m2/board-2.bin').write_bytes(data)
print('Verified current-device board data: 65620 bytes; chip ID 0, board ID 255')
