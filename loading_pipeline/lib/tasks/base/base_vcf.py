import luigi
import luigi.format

from loading_pipeline.lib.tasks.files import LocalizableTarget


class BaseVCFTask(luigi.Task):
    def output(self) -> list[LocalizableTarget]:
        vcf_path = self.vcf_path()
        return [
            LocalizableTarget(
                vcf_path,
                format=luigi.format.UTF8 >> luigi.format.Gzip,
            ),
            LocalizableTarget(f'{vcf_path}.tbi'),
        ]

    def run(self) -> None:
        self.write_vcf()

        for target in self.output():
            target.persist()

    def vcf_path(self) -> str:
        raise NotImplementedError

    def write_vcf(self) -> None:
        raise NotImplementedError
