from collections import deque
class Queue:
    def __init__(self):
        self.queue = deque()
        self.playing = False

    def add(self, source, meta):
        self.queue.append((source, meta))

    def get_next(self):
        return self.queue.popleft() if self.queue else None

    def is_empty(self):
        return len(self.queue) == 0
    