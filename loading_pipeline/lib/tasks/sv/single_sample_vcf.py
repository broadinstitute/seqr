import luigi

from loading_pipeline.lib.misc.sv import run_command
from loading_pipeline.lib.tasks.files import LocalizableFileTask


class SingleSampleVCFTask(luigi.Task):
    path_template = luigi.Parameter()
    sample_id = luigi.Parameter()
    vcf_sample_id = luigi.Parameter(default=None)

    def requires(self) -> list[luigi.Task]:
        pathname = self.path_template.replace('*', self.vcf_sample_id or self.sample_id)
        return [
            LocalizableFileTask(pathname),
            LocalizableFileTask(f'{pathname}.tbi'),
        ]

    def output(self) -> list[luigi.LocalTarget]:
        output_paths = [target.path for target in self.input()]
        if self.vcf_sample_id is not None:
            output_paths = [path.replace(self.vcf_sample_id, self.sample_id) for path in output_paths]
        return [luigi.LocalTarget(path) for path in output_paths]

    def run(self) -> None:
        for target in self.input():
            target.localize()

        if self.vcf_sample_id:
            run_command([
                'bcftools',
                'reheader',
                '-n',
                self.sample_id,
                '-o',
                self.output()[0].path,
                self.input()[0].path,
            ])
