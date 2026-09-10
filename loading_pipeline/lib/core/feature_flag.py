import os
from dataclasses import dataclass

# Feature Flags
CHECK_SEX_AND_RELATEDNESS = os.environ.get('CHECK_SEX_AND_RELATEDNESS') == '1'
EXPECT_TDR_METRICS = os.environ.get('EXPECT_TDR_METRICS') == '1'
RUN_PIPELINE_ON_DATAPROC = os.environ.get('RUN_PIPELINE_ON_DATAPROC') == '1'


@dataclass
class FeatureFlag:
    CHECK_SEX_AND_RELATEDNESS: bool = CHECK_SEX_AND_RELATEDNESS
    EXPECT_TDR_METRICS: bool = EXPECT_TDR_METRICS
    RUN_PIPELINE_ON_DATAPROC: bool = RUN_PIPELINE_ON_DATAPROC
