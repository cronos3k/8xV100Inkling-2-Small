import sys
sys.path.insert(0, '.')

import re
from sol import PATTERN
for s in ["0.0.0.0", "255.255.255.255", "192.168.1.1", "1.2.3.4", "10.0.0.255", "249.250.199.100", "9.99.100.200"]:
    assert re.fullmatch(PATTERN, s), "rejects " + s
for s in ["256.1.1.1", "1.1.1", "1.1.1.1.1", "01.1.1.1", "1.1.1.1 ", "a.b.c.d", "1..1.1", "300.1.1.1", "1.1.1.-1", "", "00.0.0.0", "1.1.1.1\n", "1.1.1.260", "1,1,1,1", "1.1.1.1.", "999.1.1.1", "1.1.1.025"]:
    assert not re.fullmatch(PATTERN, s), "accepts %r" % s

print('ALL-OK')
