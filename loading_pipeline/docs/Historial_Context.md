Notes on Loading Pipeline Orchestration

## Decision to move off of Airflow (late 2024):
	- Manual mapping of luigi tasks to Airflow tasks (w/ strings!)
	- Cost ($400 a month)
		- Small instance (2 cpu/2 gb ram) for schedular and actual compute
		- Unbelieveable scaling issues?
			- DAG built dynamically, OOMs.
			- Parallelism in task execution.
	- Maintainability issues
		- Lack of shared code with open source repo.
		- Airflow system complexity w/ helm.
		- Composer "management" + versions.
		- Manual environment variables and secrets, lack of cohesion with kubernetes.
		- Composer was its own Kubernetes ecosystem!
		- GCP integration.
		- Hooks for replacing python API calls... (why????)
		- Nasty bugs
			https://github.com/broadinstitute/seqr/pull/3995/changes
			https://github.com/broadinstitute/seqr/pull/4539/changes
			https://github.com/broadinstitute/seqr/pull/4646/changes
	- Testing difficulties
		- Able to test DAG "compile", but not actual execution.
		- System complexity (templating, XCom, retries, 'Context') in the way of lean unit and integration tests.

## Evaluation of other DAG frameworks:
	- Prefect/Dagster/Argo Workflows
	- Seem to have similar issues as Airflow; complexity does not align with the straightforward needs of the pipeline execution.

## Current Implementation
- API listens for requests from `seqr` application for asynchronous work.
- Worker with concurrency=1 polls for work.
	- One task at a time; coarse-grained lock:
		Hail cannot update variants in parallel. 
		Clickhouse cannot rebuild entire gt_stats in parallel.
	- Retries managed within the worker and persisted on disk.
	- Failures moved to deadletter queue after 5 retries.
- Loading pipeline runs "Luigi" via --local-scheduler locally or via Dataproc.
	- Luigi manages task flow and nothing else.
- Output looks like (as of 05/26):
```
gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/20260421-125644-303855/_CLICKHOUSE_LOAD_SUCCESS
gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/20260421-125644-303855/_SUCCESS
gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/20260421-125644-303855/metadata.json
gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/20260421-125644-303855/new_entries.parquet/
gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/20260421-125644-303855/new_variant_details.parquet/
gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/20260421-125644-303855/new_variants.ht/
gs://seqr-hail-search-data/v3.1/GRCh38/SNV_INDEL/runs/20260421-125644-303855/new_variants.parquet/
```

### Residues from previous iterations.
- `complete()` methods are likely overcomplicated.
	- Each task verifies completeness by running this method and if it returns `True`, skips execution.
	- Necessary for performance, but as the pipeline has started doing less it is less necessary.
	- Historically been the source of many bugs.  
		- For example, re-running pipeline with a different pedigree... we'd cached the subsetted callset, failed to generate a new one etc.
- Globalizing and Deglobalizing Ids.
	- We optimized the hail table structure to move sample ids into globals, this complicates the current logic and is likely unnecessary.  

## Thoughts for future:
	- Remove Hail for non SNV_INDEL dataset types and callsets < 500 samples.
	- Resolve the "Fatal Flaw", two separate representations of production variants, one in Hail and one in Clickhouse.
		- If pipeline fails immediately after "UpdateVariantAnnotationsTableWithNewVariantsTask", next run will have 
		incorrect "new_variants.parquet".
	- Lightweight replacement for Luigi "run()/complete()/output()/requires()" framework.
	- Eliminate scheduler in favor or "tasks" table in seqr postgres.
	- Running arbitrary docker images:
		- Airflow was useful for this, w/ Kubernetes elasticity.
		- Need to support external computational biology tools.
			- Can we just re-write with agentic coding?
	- Remove as much business logic from core pipeline as we can.
		- For example, the Terra Data Repository sample fetching.

## VEP (🗑️) Addendum:
	- VEP runs only on new variants via a custom wrapper around Hail's command.
		- Internally, HAIL exports a table to VCF and shell execs parallelized docker-VEP processes and then re-imports into a VEP schema.
	- On Dataproc, one initialization action syncs VEP reference data to HDFS.
		- For open source users, sync to local disk.
	- VEP itself is a custom docker build, pushed as a one time operation to seqr's gcr repo.
	- GRCh38 and GRCh37 use different schemas, though are both using VEP 110.
