# app/tasks/broker.py
from taskiq_nats import PullBasedJetStreamBroker
from config.config import load_config

config = load_config()

broker = PullBasedJetStreamBroker(
    servers=[f"{config.nats.servers}"],
    queue="taskiq_broadcasts",
)