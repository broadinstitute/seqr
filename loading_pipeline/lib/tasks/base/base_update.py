import hail as hl

from loading_pipeline.lib.misc.io import write
from loading_pipeline.lib.tasks.base.base_hail_table import BaseHailTableTask


class BaseUpdateTask(BaseHailTableTask):
    def run(self) -> None:
        self.init_hail()
        if not self.output().exists():
            ht = self.initialize_table()
        else:
            read_fn = (
                hl.read_matrix_table
                if self.output().path.endswith('mt')
                else hl.read_table
            )
            ht = read_fn(self.output().path)
        ht = self.update_table(ht)
        write(ht, self.output().path)

    def initialize_table(self) -> hl.Table:
        raise NotImplementedError

    def update_table(self, ht: hl.Table) -> hl.Table:
        raise NotImplementedError
