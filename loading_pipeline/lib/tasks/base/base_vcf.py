import luigi
import luigi.format

from loading_pipeline.lib.tasks.files import LocalizableTarget

class BaseVCFTask(luigi.Task):
    def output(self) -> list[LocalizableTarget]:
        vcf_name = self.vcf_name()
        return [
            LocalizableTarget(
                vcf_name,
                format=luigi.format.UTF8 >> luigi.format.Gzip,
            ),
            LocalizableTarget(f'{vcf_name}.tbi'),
        ]

    def run(self) -> None:
        self.write_vcf()

        for target in self.output():
            target.persist()

    def vcf_name(self) -> str:
        raise NotImplementedError

    def write_vcf(self) -> None:
        raise NotImplementedError
