from enum import Enum
import time
import concurrent.futures
import threading
import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


class State(Enum):
    THINKING = 0
    HUNGRY = 1
    EATING = 2


NUMBER_OF_PHILOSOPHERS = 15
EAT_MAX = 25
PROGRESS_REPORT_INTERVAL = 3

EAT_TIME_MIN = 0.3
EAT_TIME_MAX = 1.6

THINK_TIME_MIN = 0.3
THINK_TIME_MAX = 1.6

FINISHED_EVENT = threading.Event()
states_lock = threading.Lock()
states = [State.THINKING for _ in range(NUMBER_OF_PHILOSOPHERS)]
times_eaten_lock = threading.Lock()
times_eaten = [0 for _ in range(NUMBER_OF_PHILOSOPHERS)]
# Semaphores start at 0, which means that acquire() calls will block initially
# Calling release() on the semaphore allows the philosopher to start eating
# Philosophers who are done eating will attempt to call release() on neighboring semaphores
has_forks = [threading.Semaphore(0) for _ in range(NUMBER_OF_PHILOSOPHERS)]


def inc_and_get_times_eaten(i: int):
    with times_eaten_lock:
        times_eaten[i] += 1
        return times_eaten[i]


def print_times_eaten():
    with times_eaten_lock:
        logger.info(f"Progress: {[x for x in times_eaten]}")


def left(i: int):
    return i - 1


def right(i: int):
    return (1 + i) % NUMBER_OF_PHILOSOPHERS


# Critical region
def test(i: int):
    if (
        states[i] == State.HUNGRY
        and states[left(i)] != State.EATING
        and states[right(i)] != State.EATING
    ):
        states[i] = State.EATING
        # One of two cases:
        # 1. philosopher releases it's own semaphore and the subsequent call to acquire() will return immediately
        # 2. philosopher releases a neighboring philosopher's semaphore, allowing previously called acquire() to return
        has_forks[i].release()


def think(i: int):
    logger.debug(f"PHIL[{i}]: THINKING")
    time.sleep(random.uniform(THINK_TIME_MIN, THINK_TIME_MAX))


def eat(i: int):
    times = inc_and_get_times_eaten(i)
    logger.debug(f"PHIL[{i}]: EATING (Time eaten={times})")
    time.sleep(random.uniform(EAT_TIME_MIN, EAT_TIME_MAX))


def acquire_forks(i: int):
    logger.debug(f"PHIL[{i}]: Trying to acquire forks")
    with states_lock:
        states[i] = State.HUNGRY
        test(i)
    # If the semaphore has been released previously in the test() method, this will immediately return
    # Otherwise, this will block until another thread releases the semaphore from the release_forks() method
    has_forks[i].acquire()
    logger.debug(f"PHIL[{i}]: has acquired forks")


def release_forks(i: int):
    logger.debug(f"PHIL[{i}]: Releasing forks")
    with states_lock:
        states[i] = State.THINKING
        test(left(i))
        test(right(i))


def philosopher(i: int, eat_max: int):
    for _ in range(eat_max):
        think(i)
        acquire_forks(i)
        eat(i)
        release_forks(i)


def print_progress():
    while not FINISHED_EVENT.is_set():
        print_times_eaten()
        time.sleep(PROGRESS_REPORT_INTERVAL)


def main():
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=NUMBER_OF_PHILOSOPHERS + 1
    ) as executor:
        futures = [
            executor.submit(philosopher, i, EAT_MAX)
            for i in range(NUMBER_OF_PHILOSOPHERS)
        ]
        executor.submit(print_progress)
        concurrent.futures.wait(futures)
        FINISHED_EVENT.set()
        print_times_eaten()


if __name__ == "__main__":
    main()
    print("Finished program")
