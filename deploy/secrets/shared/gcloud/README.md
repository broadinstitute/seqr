###### google service account key

This is used to authenticate gcloud and gsutils command-line tools within the seqr and pipeline-runner pods,
so that gcloud and gsutil can be used to access public google storage buckets, etc. without having to first prompt for authentication.

For example, this is used within the pipeline-runner component when loading data into elasticsearch to allow the spark/hail loading pipeline to directly
access reference data files in gs://seqr-reference-data via the Cloud Storage connector.

The key provided below is generated using a temporary google account created just for generating this key.
To create your own key file, see instructions @ https://cloud.google.com/dataproc/docs/concepts/connectors/install-storage-connector

It can be created by:
 1) Go to https://console.developers.google.com/apis/credentials
 2) In the "Create credentials" drop-down, select "Service account key"
 3) Select "Compute Engine default service account" and Key type "JSON"
