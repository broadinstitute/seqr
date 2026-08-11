import luigi


class MockCompleteTask(luigi.Task):
    def complete(self):
        return True
