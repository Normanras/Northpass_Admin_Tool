import os


class Config(object):
    SECRET_KEY = os.environ.get("NORTHPASS") or "north-pass"
