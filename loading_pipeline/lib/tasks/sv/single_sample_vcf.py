import luigi

from loading_pipeline.lib.misc.sv import run_command
from loading_pipeline.lib.tasks.files import LocalizableFileTask


class SingleSampleVCFTask(luigi.Task):
    path_template = luigi.Parameter()
    sample_id = luigi.Parameter()
    vcf_sample_id = luigi.Parameter(default=None)

    def requires(self) -> list[luigi.Task]:
        return [
            LocalizableFileTask(pathname)
            for pathname in self._file_names(self.vcf_sample_id or self.sample_id)
        ]

    def output(self) -> list[luigi.LocalTarget]:
        file_id = self.sample_id
        if self.vcf_sample_id is not None:
            file_id = f'{self.vcf_sample_id}__{file_id}'
        return [luigi.LocalTarget(pathname) for pathname in self._file_names(file_id)]

    def _file_names(self, file_id: str) -> list[str]:
        pathname = self.path_template.replace('*', file_id)
        return [pathname, f'{pathname}.tbi']

    def run(self) -> None:
        for target in self.input():
            target.localize()

        if self.vcf_sample_id:
            out_path = self.output()[0].path
            run_command(
                [
                    'bcftools',
                    'reheader',
                    '-n',
                    self.sample_id,
                    '-o',
                    out_path,
                    self.input()[0].path,
                ],
            )
            run_command(['tabix', '-p', 'vcf', out_path])
