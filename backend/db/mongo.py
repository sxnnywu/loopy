"""MongoDB Atlas (pymongo). Owner: C. Collections: users, tests, variants, scores."""
import os
from pymongo import MongoClient

_client = None
def db():
    global _client
    if _client is None:
        _client = MongoClient(os.environ["MONGODB_URI"])
    return _client[os.environ.get("MONGODB_DB", "reeled_in")]
