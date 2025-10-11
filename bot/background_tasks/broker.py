# bot/background_tasks/broker.py
from taskiq_nats import PullBasedJetStreamBroker
from taskiq_nats.schedule_source import NATSKeyValueScheduleSource
from config.config import load_config
from taskiq import TaskiqScheduler

config = load_config()

broker = PullBasedJetStreamBroker(
    servers=config.nats.servers,
    queue="taskiq_broadcasts",
)


schedule_source = NATSKeyValueScheduleSource(
    servers=config.nats.servers,
    bucket_name="taskiq_scheduled_tasks"
)

import bot.background_tasks.dunning
import bot.background_tasks.test

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[schedule_source]
)