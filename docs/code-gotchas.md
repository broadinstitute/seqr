### Understanding The Code

You should be able to quickly download and run the xBrowse scripts without any knowledge of how the software works.
If you are so inclined, we also encourage you to look inside the code and improve/extend it.
I hope to write an overview of the code structure at some point;
for now, here are a few random notes about how the package works:

- Throughout the package, genomic coordinates are reduced to a 1-D field known as "xpos".
This is a long integer that is equal to `chromosome * 1e9 + position`.
See genomeloc.py.

- Ensembl Gene IDs are used throughout xBrowse - "gene_id" always refers to an *unversioned* ensembl ID
(so `ENSG00000155657` instead of `ENSG00000155657.18`)

- Data structures are a bit awkward. There is a [doc page](docs/data-structures.md) describing the main data structures.


