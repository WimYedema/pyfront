import logging
import sys
from pathlib import Path

from out.parser import parse

logging.basicConfig(level=logging.DEBUG)

text = Path(sys.argv[1]).read_text(encoding="utf-8")
print(parse(text))
