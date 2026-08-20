# Pipeline flow, as of 05/06/2026

```
                      WriteImportedCallsetTask
                      (VCF → Hail Matrix Table)
                                |
                                v
                   WritePostprocessedCallsetTask
                   (split multi, deduplicate)
                                |
                 _______________|_______________
                |                               |
                v                               v
   WriteSexCheckTableTask          ValidateCallsetTask
                |                  (validation checks)
                |                               |
                |                               v
                |               WriteRelatednessCheckTableTask
                |                               |
                |                               v
                |               WriteRelatednessCheckTsvTask
                |                               |
                |_______________________________|
                                |
                                v
           _____________________|_____________________
          |                                           |
          v                                           v
  WriteRemappedAndSubsettedCallsetTask  WriteRemappedAndSubsettedCallsetTask
    (Project 1)                            (Project N)
          |                                           |
          |___________________________________________|
                                |
                                v
                   WriteMetadataForRunTask
                                |
                                v
                    WriteNewVariantsTableTask
                                |
                                v
            UpdateVariantAnnotationsTableWithNewVariantsTask
                      (Variants with annotations)
                                |
          ______________________+_______________________
          |                     |                      |
          v                     v                      v
  WriteNewEntries...     WriteNewVariants...    WriteNewVariantDetails...
  ParquetTask            ParquetTask            ParquetTask
  |                           |                  (optional)
  |___________________________|_______________________|
          |
          v
     RunPipelineTask
     (all parquets ready)
          |
          v
    WriteSuccessFileTask
          |
          v
  WriteClickhouseLoadSuccessFileTask
  (load parquets → ClickHouse)
```

ClickHouse LSM-Tree

```
┌────────────────────────────────────────────────────────────┐
│        ClickHouse LSM: MemTable → Parts → Merge            │
└────────────────────────────────────────────────────────────┘

  WRITE PHASE:
  ─────────────

      INSERT statements
             │
             ▼
      ┌──────────────┐
      │  MemTable    │  (In-memory buffer)
      │  ~150 MB     │  ◄─── Growing as writes arrive
      └──────┬───────┘
             │
        (Threshold exceeded)
             │
             ▼
      ┌──────────────┐
      │    Flush     │
      │  to Disk     │
      └──────┬───────┘
             │
             ▼
      ┌──────────────┐
      │  Part (L0)   │  ◄─── New immutable part on disk
      └──────────────┘


  DISK STATE (Multiple Parts):
  ──────────────────────────────

      MemTable      Disk Parts (sorted by creation)
      ┌─────┐
      │     │       ┌──────────┐
      │     │       │ Part(L0) │ ◄─── Recently flushed (small)
      │     │       └──────────┘
      │     │       ┌──────────┐
      │     │       │ Part(L0) │
      │     │       └──────────┘
      │     │       ┌──────────┐
      │     │       │ Part(L0) │
      │     │       └──────────┘
      │     │       ┌──────────┐
      │     │       │ Part(L1) │ ◄─── Older (larger)
      │     │       └──────────┘
      │     │       ┌──────────┐
      │     │       │ Part(L2) │
      │     │       └──────────┘
      └─────┘


  BACKGROUND MERGE (Compaction):
  ───────────────────────────────

      When L0 has ~10 parts:

          ┌──────────┐
          │Part(L0)  │
          └────┬─────┘
               │
          ┌────┴─────┬──────────┐
          │           │          │
      ┌───▼──┐  ┌────▼───┐  ┌───▼──┐
      │L0 #1 │  │  L0 #2 │  │ L0#3 │ ──┐
      └──────┘  └────────┘  └──────┘   │
                                        │  Read + Sort
      ┌──────────────────────────────┐ │  + Compress
      │     Compaction Process       │◄┘
      │                              │
      │  1. Read all rows from L0s   │
      │  2. Merge by primary key     │
      │  3. Sort & compress          │
      │  4. Write to single Part(L1) │
      └───────────────┬──────────────┘
                      │
                      ▼
               ┌──────────────┐
               │  Part(L1)    │  ◄─── One larger part
               │  (merged)    │      (old L0 parts deleted)
               └──────────────┘ 

```