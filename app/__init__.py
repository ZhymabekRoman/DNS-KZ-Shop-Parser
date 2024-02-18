import sys
from loguru import logger

logger.configure(handlers=[{"sink": sys.stderr, "level": "DEBUG"}])
