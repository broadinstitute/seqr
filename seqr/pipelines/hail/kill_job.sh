gcloud dataproc jobs kill --project=seqr-project $1
#`gcloud dataproc jobs list --state-filter=active |& cut -f 1 |& grep -v Listed`
