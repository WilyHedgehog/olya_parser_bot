# bot/background_tasks/worker.py
from bot.background_tasks.broker import broker
from taskiq_nats import run_worker # если версия Taskiq новая, run_worker встроен

if __name__ == "__main__":
    run_worker(broker)