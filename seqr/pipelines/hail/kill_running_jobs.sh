gcloud dataproc jobs kill `gcloud dataproc jobs list --state-filter=active |& cut -f 1 |& grep -v Listed`
