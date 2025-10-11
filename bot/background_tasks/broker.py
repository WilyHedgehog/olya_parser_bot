# bot/background_tasks/broker.py
from taskiq_nats import PullBasedJetStreamBroker
from config.config import load_config
import taskiq_worker

config = load_config()

broker = PullBasedJetStreamBroker(
    servers=config.nats.servers,
    queue="taskiq_broadcasts",
)