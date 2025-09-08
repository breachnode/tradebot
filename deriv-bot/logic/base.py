from abc import ABC, abstractmethod


class Strategy(ABC):
    @abstractmethod
    def decide_entry(self, row) -> dict | None:
        ...

    @abstractmethod
    def decide_exit(self, position, row) -> dict | None:
        ...

    def update(self, row):
        return None

