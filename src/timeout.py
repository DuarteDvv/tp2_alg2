"""interrupção por tempo de parede no processo principal (Linux/macOS)."""

from contextlib import contextmanager
import argparse
import signal


def time_limit_arg(value):
    seconds = float(value)
    if not 0 < seconds <= 1800:

        raise argparse.ArgumentTypeError("Use um tempo maior que 0 e até 1800 segundos.")

    return seconds


def interrupt_execution(signal_number, frame):
    raise TimeoutError("Tempo de execução esgotado.")


@contextmanager
def execution_timeout(seconds):
    if seconds is None:

        yield
        return

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, interrupt_execution)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
