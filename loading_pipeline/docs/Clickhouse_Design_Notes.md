# ClickHouse Design Decisions

## Schema

### Entries Table
- Grouping by family was most efficient at query-time and was a wash on-disk.
- ORDER BY `project_guid, family_guid, sample_type, is_gnomad_gt_5_percent, is_annotated_in_any_gene, key`
	- Support searches on project or family
- PROJECTION on `is_gnomad_gt_5_percent`, `is_annotated_in_any_gene`, `xpos`
	- Static view over gnomad constructed at load time.
	- Note that an update to gnomad _requires_ rebuilding this!!!!
		- I would try to be clever about this, identifying the variants that change when gnomad updates
		- From experience, dropping or adding columns NOT in the sorting key is very easy... impossible if it is.
	- `is_annotated_in_gene` (lightweight boolean index to support gene search)
	- xpos ordering supports sorts on gene/position.
- `geneId_ids` Array(UInt32)
	- We _tried_ to make this a bitmap column.  However, they are really "partial aggregation state" columns 
	`AggregateFunction(groupBitmap, UInt64)` and are not cleanly supported in all the right ways downstream.  
	- We store an array of integers and convert to a bitmap at search time, for a slight performance hit.
	- hasAny(`list<str>`, `list<str>`) is trash slow and untenable.

### Variants Tables
- Searchable fields in `variants_memory`.
- `variants_details` is post-filter and slow (10k per second).  Mostly large blobs of strings.
- Live search queries run against `variants_memory` only.  At load time, we insert into both tables w/ "on-disk" first.  RocksDB inserts are idempotent so can handle retries re-writing the same key multiple times.

### Reference Data Tables
- One table each per reference data source: `all_variants`, `seqr_variants`, `search`. 
- Sourced from raw VCFs/TSVs if possible, `splice_ai` and `dbnsfp` are SLOW and big.
- Dictionaries are mostly [`HASHED_ARRAY`](https://kb.altinity.com/altinity-kb-dictionaries/altinity-kb-sparse_hashed-vs-hashed/)
- Tables with lots of seqr variants ("full rank" in key space) or too small to matter can be "FLAT" arrays.
- `RANGE_HASHED()` for ranges.
- dictGets and JOIN tables are super fast (10M/S) so even N joins is much faster than RocksDB table access.

### SeqrDB Dicts
- Postgres backed dictionaries.
- Postgres named collection set up in infrastructure.
- These are essential, providing fast access within ClickHouse to Postgres itself.
	- Loading references these.
		- populating the geneIds field
	- Search queries reference them too.
- Performantly refreshable!

### Incremental vs Refreshable Materialized Views
- Incremental MVs are pointers between two actual tables, when data is inserted into the first it is copied
to the second with a transformation.
- Refreshable MVs are more analagous to other DBs, full data is generated on a schedule or manually.
    - All Refreshable MVs in seqr are set to a refresh frequency of every 10 years.
- Incremental MVs cannot be "built".

### RocksDB
The dependency on RocksDB is the weak point of the ClickHouse backend.  The data structure is opaque, hard to reason about and improve, and challenging to query and update.  Schema migrations are not supported, backups are manual and failure-prone, and the Engine is not supported in the managed ClickHouse Inc product.  It solves a key problem for us, however, supporting fast key-value access over both small and large blobs of strings. 

Only Key/Value access is really supported for the RocksDB tables.  Queries such as `SELECT ... WHERE key > 0 and key < 100000` are very slow and should be avoided.

### Ingestion Architecture & Async Tasks
- Many operations in ClickHouse are asynchrnous and happen in the background.  Careful attention must be paid
to ensure things finish reliably and do not leave partial state!
- Load is structured around a `staging` database and [atomic partition movement](https://clickhouse.com/blog/table-cloning).
    - All `entries` tables and materialized views are schema-copied into `staging`.
    - All data is inserted into `staging`.
    - `staging` environment must be 'verified'.
    - Dictionaries are rebuilt only in `production` database!
- `entries`/`project_gt_stats`/`gt_stats` cascade was required for reasonable performance
of recomputing allele frequencies.  We did try loading without multiple descending views, but re-grouping the whole `entries` table OOMs.

### History of Nasty Bugs
- Incorrectly named the on-disk tables `/variants/details` instead of `/variants_details` which caused issues because of an existing `/variants` path.
- Missing `affected_status` in materialized view ORDER BY, leading to undefined behavior.
- Mis-typed a gnomad allele frequency, incorrectly rounding down AFs.
- Infinite issues with column ordering, missing fields, and types.

## Infrastructure

#### ClickHouse Settings
Essential:
- `max_partition_size_to_drop`/`max_table_size_to_drop` need to be high, we delete the `staging` database
and thus need these to be the size of the largest project.
- `max_bytes_ratio_before_external_group_by`/`max_bytes_ratio_before_external_sort`.  These are set to `0.1` and are essential.
During loading and various other operations, large `GROUP BY` can OOM.  We have set these to ensure JOINs spill to disk, preferring slowness to crashes!
- `stop_refreshable_materialized_views_on_startup`, prevents all views from starting all at once on server startup.

Optional:
- `max_query_size`, `max_ast_elements`, `max_expanded_ast_elements`,`max_parser_backtracks`: used internally for large projects with many samples.
- `max_server_memory_usage_to_ram_ratio` instructs ClickHouse to use less of the server's memory.  Since we mount `/in-memory-dir` we allocate resources away from ClickHouse without its knowledge.
- `background_pool_size`, `background_merges_mutations_concurrency_ratio`, `number_of_free_entries_in_pool_to_execute_mutation`, `number_of_free_entries_in_pool_to_lower_max_size_of_merge`, `number_of_free_entries_in_pool_to_execute_optimize_entire_partition` allow limiting the number of background threads for background tasks.  This has been helpful for protecting search performance at the cost of longer background operations.

#### Running a Single Host  
Clickhouse and the Helm installation support replication and scaling with either a Zookeeper or Clickhouse-Keeper managed cluster.  Given our prioritization of Consistency >> Availability, and the complexity of managing a cluster, we've opted for the simplicity of maintaining a single host, accepting the risk of limited downtime both in search and loading.

#### Backups
We have a cron in the [seqr codebase](https://github.com/broadinstitute/seqr/blob/master/deploy/docker/seqr/clickhouse_backup.py) that manages incremental backups of the the Broad `seqr`'s database.  The `rocksdb` tables are backed up with a cloud storage rsync cron.

#### Project Sub-Partitions
Select `GRCh38/SNV_INDEL` WGS projects are subpartitioned via a static mapping, set up as a one time operation w/ a rough goal of 500m rows per partition.  Our largest projects far exceed ClickHouse's recommended maximum partition, and operations on coalesced single partitions are single threaded (slowing down `OPTIMIZE TABLE FINAL` like no other).  Supporting sub-partitions lets us parallelize
any `OPTIMIZE TABLE` and in general leads to more manageable chunks of data.  

We did not, however, notice this prior to initial go-live.  Thus all non-`GRCh38/SNV_INDEL` tables and early open-source releases do
follow this pattern.  We have code and unit-tests to support both partitioning paradigms, and also have an operations script for the manual re-partitioning (`loading_pipeline/ops`).

## Miscellaneous

#### Learning About ClickHouse
- PostHog's [Clickhouse explainers](https://posthog.com/blog/clickhouse)
- Andy Pavlo's [DB Course](https://www.youtube.com/watch?v=nhlpwmOBEiE)
- The ClickHouse Documentation.

#### Debugging Advice
- Logging into the client:
```
kubectl port-forward services/seqr-clickhouse 9000:9000

# In another terminal
./clickhouse client --user seqr_clickhouse_writer --password PASSWORD
```

- Reading the query log, for example recent non-insert queries:
```
select * FROM system.query_log where query_start_time > '2026-05-01' and query not like '%INSERT%';
```
Statistics like query time and memory are available here.

- Manually timing queries.  I've generally had a much better experience running a query and inserting into a temp table.  For example:
```
create temporary table t as SELECT transcripts FROM (
    SELECT toUInt32(generate_series) AS key
    FROM generate_series(5_000_000, 5_010_000)
) k INNER JOIN `GRCh38/SNV_INDEL/transcripts` t on k.key = t.key;
```
The alternatives, either returning the full result set to the client or "SELECT COUNT(*)", return biased timings.  Either too slow due to networking buffering over the terminal or too fast due to not actually fetching the full result set off of disk.

- Viewing `Dictionary` usage:
```
SELECT
    name AS dictionary_name,
    sum(bytes_allocated) AS bytes_allocated_,
    formatReadableSize(sum(bytes_allocated)) AS readable_size
FROM system.dictionaries
GROUP BY dictionary_name
ORDER BY bytes_allocated_ DESC
```
Broad Seqr's production instance dictionaries consume ~30GB of memory.

NOTE: I (bpb) believe these numbers are underestimates and don't account for some of the full memory overhead of maintaining these in memory.

- Viewing `Join` table memory usage:
```
SELECT
    database,
    name,
    formatReadableSize(total_bytes)
FROM system.tables
WHERE engine IN ('Memory', 'Set', 'Join')
```
Broad Seqr's production 'Join' tables consume about ~1GB of memory.

- Viewing disk usage within ClickHouse:
```
SELECT
    disk_name,
    database,
    `table`,
    sum(bytes_on_disk) AS s,
    formatReadableSize(sum(bytes_on_disk)) AS size
FROM system.parts
WHERE active = 1
GROUP BY
    disk_name,
    database,
    `table`
ORDER BY s DESC
```

Broad Seqr's production disk usage:
```
   ┌─disk_name─┬─database─┬─table─────────────────────────────────────────────────────────────────────┬─────────────s─┬─size───────┐
1. │ default   │ seqr     │ GRCh38/SNV_INDEL/entries                                                  │ 2134397010569 │ 1.94 TiB   │
2. │ default   │ seqr     │ GRCh37/SNV_INDEL/reference_data/splice_ai/all_variants                    │   72085843803 │ 67.14 GiB  │
3. │ default   │ seqr     │ GRCh38/SNV_INDEL/reference_data/splice_ai/all_variants                    │   71927088053 │ 66.99 GiB  │
4. │ default   │ seqr     │ GRCh37/SNV_INDEL/entries                                                  │   39255880565 │ 36.56 GiB  │
5. │ default   │ seqr     │ GRCh38/SNV_INDEL/project_gt_stats                                         │   38191863243 │ 35.57 GiB  │
6. │ default   │ seqr     │ GRCh38/SNV_INDEL/reference_data/gnomad_genomes/all_variants               │   12827564551 │ 11.95 GiB  │


SELECT COUNT(*)
FROM `GRCh38/SNV_INDEL/entries`

Query id: 51d2a78e-de1a-4b75-9131-1e9e1e3a2ecb

   ┌─────COUNT()─┐
1. │ 68213850227 │ -- 68.21 billion
   └─────────────┘
```

- Viewing disk usage outside of ClickHouse:
```
kubectl exec seqr-clickhouse-shard0-0  -c clickhouse -it -- bash -c 'cd /in-memory-dir; du -h'
```

```
kubectl exec seqr-clickhouse-shard0-0  -c clickhouse -it -- bash -c 'cd /var/seqr/clickhouse-data; du -h'
```
