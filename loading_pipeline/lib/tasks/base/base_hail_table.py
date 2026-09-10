import hail as hl
import luigi

from loading_pipeline.lib.annotations.liftover import remove_liftover
from loading_pipeline.lib.core import Env
from loading_pipeline.lib.logger import get_logger
from loading_pipeline.lib.tasks.base.base_loading_pipeline_params import (
    BaseLoadingPipelineParams,
)
from loading_pipeline.lib.tasks.files import GCSorLocalFolderTarget

logger = get_logger(__name__)


@luigi.util.inherits(BaseLoadingPipelineParams)
class BaseHailTableTask(luigi.Task):
    def output(self) -> luigi.Target:
        raise NotImplementedError

    def complete(self) -> bool:
        logger.info(f'BaseHailTableTask: checking if {self.output().path} exists')
        return GCSorLocalFolderTarget(self.output().path).exists()

    def init_hail(self):
        # Need to use the GCP bucket as temp storage for very large callset joins
        hl.init(tmp_dir=Env.HAIL_TMP_DIR, idempotent=True)
        logger.info(f'Initialized hail w/ tmp_dir {Env.HAIL_TMP_DIR}')

        # Interval ref data join causes shuffle death, this prevents it
        hl._set_flags(use_new_shuffle='1', no_whole_stage_codegen='1')  # noqa: SLF001

        # Ensure any cached liftover files within Hail are cleared
        # to provide a clean context free of hidden state.
        # This runs "before" a task to account for situations where
        # the Hail write fails and we do not have the chance to
        # run this method in the "after".
        remove_liftover()


# NB: these are defined over luigi.Task instead of the BaseHailTableTask so that
# they work on file dependencies.


@luigi.Task.event_handler(luigi.Event.DEPENDENCY_DISCOVERED)
def dependency_discovered(task, dependency):
    logger.info(f'{task} dependency_discovered {dependency} at {task.output()}')


@luigi.Task.event_handler(luigi.Event.DEPENDENCY_MISSING)
def dependency_missing(task):
    logger.info(f'{task} dependency_missing at {task.output()}')


@luigi.Task.event_handler(luigi.Event.DEPENDENCY_PRESENT)
def dependency_present(task):
    logger.info(f'{task} dependency_present at {task.output()}')


@luigi.Task.event_handler(luigi.Event.START)
def start(task):
    logger.info(f'{task} start')


@luigi.Task.event_handler(luigi.Event.FAILURE)
def failure(task, _):
    logger.exception(f'{task} failure')


@luigi.Task.event_handler(luigi.Event.SUCCESS)
def success(task):
    logger.info(f'{task} success')
