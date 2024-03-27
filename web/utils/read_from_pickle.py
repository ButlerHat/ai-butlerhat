import pickle
import json
from ButlerRobot.src.data_types import Task


class TaskReader:
    def __init__(self, file_path):
        self.file_path = file_path

    def read(self) -> Task:
        raise NotImplementedError


class TaskFromPickle(TaskReader):
    
        def __init__(self, file_path):
            super().__init__(file_path)
    
        def read(self):
            with open(self.file_path, 'rb') as f:
                return pickle.load(f)


class TaskFromJson(TaskReader):
    
        def __init__(self, file_path):
            super().__init__(file_path)
    
        def read(self):
            with open(self.file_path, 'r') as f:
                return json.load(f)

