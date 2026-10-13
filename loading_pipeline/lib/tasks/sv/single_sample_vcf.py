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
        paths = [target.path for target in self.input()]
        if self.vcf_sample_id is not None:
            paths = [
                f'{self.vcf_sample_id}__{self.sample_id}'.join(
                    path.rsplit(self.vcf_sample_id, 1),
                )
                for path in paths
            ]
        return [luigi.LocalTarget(pathname) for pathname in paths]

    def run(self) -> None:
        for target in self.input():
            target.localize()

        if self.vcf_sample_id:
            out_path = self.output()[0].path
            samples_target = luigi.LocalTarget(is_tmp=True)
            with samples_target.open('w') as f:
                f.write(f'{self.sample_id}\n')
            run_command(
                [
                    'bcftools',
                    'reheader',
                    '-s',
                    samples_target.path,
                    '-o',
                    out_path,
                    self.input()[0].path,
                ],
            )
            run_command(['tabix', '-p', 'vcf', out_path])
