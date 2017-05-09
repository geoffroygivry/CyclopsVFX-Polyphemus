from pymongo import MongoClient
from cyc_config import cyc_config as cfg

server = MongoClient(cfg.MONGODB)
