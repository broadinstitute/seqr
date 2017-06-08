Annotation In xBrowse
=====================

[In Progress]

This page describes how variants are given a functional annotation in xBrowse.
xBrowse uses Ensembl’s Variant Effect Predictor (VEP) to annotate variants -
you’ll see that much of the conversation here is framed around the behavior of VEP.

As part of the loading process, xBrowse runs VEP on all variants in a VCF file,
parses annotations into a more intuitive format,
and adds additional annotations.

We periodically re-run this annotation pipeline
all of the VCF files in xBrowse, to ensure that annotations are up to date.
(This is much of the delay whenever we are "rebuilding" the xBrowse database.)

Currently, xBrowse annotations are rebuilt sporadically.
We have no method for dating or versioning annotations, though we should definitely pursue this.

### VEP Usage

The exact command we use to annotate a VCF is:

    perl variant_effect_predictor.pl --offline --protein --hgnc --vcf --dir [cache directory] -i $INPUT_VCF_PATH -o $OUTPUT_VCF_PATH

Using this command, you should be able to replicate the annotation that is used in xBrowse.

### Classifying Annotations

xBrowse follows VEP and uses the **Sequence Ontology** terms to describe functional consequences.
A list of the annotations provided by VEP is information is available
<a target="_blank" href="http://useast.ensembl.org/info/docs/variation/predicted_data.html#consequences">here</a>.

However, it can often be easier to describe variants in higher order terms like *missense* and *nonsense*.
So, xBrowse also maps each of the sequence ontology terms into one of the following groups:

- Nonsense
- Essential splice site
- Extended splice site
- Missense
- Frameshift
- In Frame
- Synonymous
- Other

In the xBrowse analysis pages, you can zoom in on one of these groups and select the more granular sequence ontology terms.

### Collapsing Annotations

VEP annotations are *per-transcript*; a variant is given an annotation for each transcript that it impacts.
For each variant, xBrowse also determines the *most severe annotation*,
as well as the most severe annotation *for each gene* that the variant is annotated to.

When you search for variants in xBrowse, the most severe annotation per gene is always considered.