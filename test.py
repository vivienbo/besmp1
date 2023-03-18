import logging

logging.getLogger().setLevel(logging.INFO)

l = logging.Logger
logging.info("type: %s", type(l))