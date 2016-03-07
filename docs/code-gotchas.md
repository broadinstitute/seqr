### Understanding The Code

- Throughout the package, genomic coordinates are reduced to a 1-D field known as "xpos".
This is a long integer that is equal to `chromosome * 1e9 + position`.
See genomeloc.py.

- Ensembl Gene IDs are used throughout xBrowse - "gene_id" always refers to an *unversioned* ensembl ID
(so `ENSG00000155657` instead of `ENSG00000155657.18`)


