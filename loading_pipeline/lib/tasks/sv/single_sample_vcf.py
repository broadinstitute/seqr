import luigi

from loading_pipeline.lib.tasks.files import LocalizableFileTask


class SingleSampleVCFTask(luigi.Task):
    path_template = luigi.Parameter()
    sample_id = luigi.Parameter()

    def requires(self) -> list[luigi.Task]:
        pathname = self.path_template.replace('*', self.sample_id)
        return [
            LocalizableFileTask(pathname),
            LocalizableFileTask(f'{pathname}.tbi'),
        ]

    def output(self) -> list[luigi.LocalTarget]:
        return [luigi.LocalTarget(target.path) for target in self.input()]

    def run(self) -> None:
        for target in self.input():
            target.localize()
