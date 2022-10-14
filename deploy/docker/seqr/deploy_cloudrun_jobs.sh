# Add updater scripts

ENV_NAME="prod"

SEQR_URL="https://seqr.populationgenomics.org.au/"
SERVICE_ACCOUNT="seqr-prod@seqr-308602.iam.gserviceaccount.com"
IMAGE="australia-southeast1-docker.pkg.dev/seqr-308602/seqr-project/seqr:gcloud-prod"

POSTGRES_USERNAME="postgres"
POSTGRES_DATABASE="seqrdb"
POSTGRES_REFERENCE_DATABASE="reference_data_db"
POSTGRES_PASSWORD_SECRET_NAME="postgres-password"

GSA_SECRET_NAME="gsa-key-prod"
DJANGO_SECRET_NAME="django-key-prod"

gcloud beta run jobs create \
   ${ENV_NAME}-schema-migrator \
   --image=${IMAGE} \
   --task-timeout 3600 \
   --command=python --args="-u,manage.py,migrate" \
   --region=australia-southeast1 \
   --service-account=${SERVICE_ACCOUNT} \
   --vpc-connector=projects/seqr-308602/locations/australia-southeast1/connectors/seqr-cloud-run-to-sql \
   --vpc-egress=private-ranges-only \
   --set-env-vars="DEPLOYMENT_TYPE=dev,BASE_URL=${SEQR_URL},POSTGRES_SERVICE_HOSTNAME=10.94.145.3,POSTGRES_SERVICE_PORT=5432,POSTGRES_DATABASE=${POSTGRES_DATABASE},POSTGRES_REFERENCE_DATABASE=${POSTGRES_REFERENCE_DATABASE},POSTGRES_USERNAME=${POSTGRES_USERNAME},PYTHONPATH=/seqr,PYTHONUNBUFFERED=True" \
   --set-secrets="DJANGO_KEY=${DJANGO_SECRET_NAME}:latest,GSA_KEY=${GSA_SECRET_NAME}:latest,POSTGRES_PASSWORD=${POSTGRES_PASSWORD_SECRET_NAME}:latest" \
   --execute-now

gcloud beta run jobs create \
   ${ENV_NAME}-reference-schema-migrator \
   --image=${IMAGE} \
   --task-timeout 3600 \
   --command=python --args="-u,manage.py,migrate,--database=reference_data" \
   --region=australia-southeast1 \
   --service-account=${SERVICE_ACCOUNT} \
   --vpc-connector=projects/seqr-308602/locations/australia-southeast1/connectors/seqr-cloud-run-to-sql \
   --vpc-egress=private-ranges-only \
   --set-env-vars="DEPLOYMENT_TYPE=dev,BASE_URL=${SEQR_URL},POSTGRES_SERVICE_HOSTNAME=10.94.145.3,POSTGRES_SERVICE_PORT=5432,POSTGRES_DATABASE=${POSTGRES_DATABASE},POSTGRES_REFERENCE_DATABASE=${POSTGRES_REFERENCE_DATABASE},POSTGRES_USERNAME=${POSTGRES_USERNAME},PYTHONPATH=/seqr,PYTHONUNBUFFERED=True" \
   --set-secrets="DJANGO_KEY=${DJANGO_SECRET_NAME}:latest,GSA_KEY=${GSA_SECRET_NAME}:latest,POSTGRES_PASSWORD=${POSTGRES_PASSWORD_SECRET_NAME}:latest" \
   --execute-now

gcloud beta run jobs create \
   ${ENV_NAME}-reference-updater \
   --image=${IMAGE} \
   --task-timeout 3600 --memory 2048Mi \
   --command=python --args="-u,manage.py,update_all_reference_data,--use-cached-omim" \
   --region=australia-southeast1 \
   --service-account=${SERVICE_ACCOUNT} \
   --vpc-connector=projects/seqr-308602/locations/australia-southeast1/connectors/seqr-cloud-run-to-sql \
   --vpc-egress=private-ranges-only \
   --set-env-vars="DEPLOYMENT_TYPE=dev,BASE_URL=${SEQR_URL},POSTGRES_SERVICE_HOSTNAME=10.94.145.3,POSTGRES_SERVICE_PORT=5432,POSTGRES_DATABASE=${POSTGRES_DATABASE},POSTGRES_REFERENCE_DATABASE=${POSTGRES_REFERENCE_DATABASE},POSTGRES_USERNAME=${POSTGRES_USERNAME},PYTHONPATH=/seqr,PYTHONUNBUFFERED=True" \
   --set-secrets="DJANGO_KEY=${DJANGO_SECRET_NAME}:latest,GSA_KEY=${GSA_SECRET_NAME}:latest,POSTGRES_PASSWORD=${POSTGRES_PASSWORD_SECRET_NAME}:latest" \
   --execute-now

gcloud beta run jobs create \
   ${ENV_NAME}-reference-update-hpo-terms \
   --image=${IMAGE} \
   --task-timeout 3600 \
   --command=python --args="-u,manage.py,update_human_phenotype_ontology" \
   --region=australia-southeast1 \
   --service-account=${SERVICE_ACCOUNT} \
   --vpc-connector=projects/seqr-308602/locations/australia-southeast1/connectors/seqr-cloud-run-to-sql \
   --vpc-egress=private-ranges-only \
   --set-env-vars="DEPLOYMENT_TYPE=dev,BASE_URL=${SEQR_URL},POSTGRES_SERVICE_HOSTNAME=10.94.145.3,POSTGRES_SERVICE_PORT=5432,POSTGRES_DATABASE=${POSTGRES_DATABASE},POSTGRES_REFERENCE_DATABASE=${POSTGRES_REFERENCE_DATABASE},POSTGRES_USERNAME=${POSTGRES_USERNAME},PYTHONPATH=/seqr,PYTHONUNBUFFERED=True" \
   --set-secrets="DJANGO_KEY=${DJANGO_SECRET_NAME}:latest,GSA_KEY=${GSA_SECRET_NAME}:latest,POSTGRES_PASSWORD=${POSTGRES_PASSWORD_SECRET_NAME}:latest" \
   --execute-now

gcloud beta run jobs create \
   ${ENV_NAME}-reference-import-panels \
   --image=${IMAGE} \
   --task-timeout 3600 \
   --command=python --args="-u,manage.py,import_all_panels,https://panelapp.agha.umccr.org/api/v1,--label=AU" \
   --region=australia-southeast1 \
   --service-account=${SERVICE_ACCOUNT} \
   --vpc-connector=projects/seqr-308602/locations/australia-southeast1/connectors/seqr-cloud-run-to-sql \
   --vpc-egress=private-ranges-only \
   --set-env-vars="DEPLOYMENT_TYPE=dev,BASE_URL=${SEQR_URL},POSTGRES_SERVICE_HOSTNAME=10.94.145.3,POSTGRES_SERVICE_PORT=5432,POSTGRES_DATABASE=${POSTGRES_DATABASE},POSTGRES_REFERENCE_DATABASE=${POSTGRES_REFERENCE_DATABASE},POSTGRES_USERNAME=${POSTGRES_USERNAME},PYTHONPATH=/seqr,PYTHONUNBUFFERED=True" \
   --set-secrets="DJANGO_KEY=${DJANGO_SECRET_NAME}:latest,GSA_KEY=${GSA_SECRET_NAME}:latest,POSTGRES_PASSWORD=${POSTGRES_PASSWORD_SECRET_NAME}:latest" \
   --execute-now


# Add triggers
# space these out time-wise so they don't update at the same time
gcloud scheduler jobs create http --location australia-southeast1 \
   ${ENV_NAME}-reference-update-hpo-terms \
   --uri "https://australia-southeast1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/seqr-308602/jobs/${ENV_NAME}-reference-update-hpo-terms:run" \
   --description "${ENV_NAME}: Update HPO Terms" \
   --schedule "0 0 * * 0" \
   --time-zone "Australia/Melbourne" \
   --oauth-service-account-email ${SERVICE_ACCOUNT}

gcloud scheduler jobs create http --location australia-southeast1 \
   ${ENV_NAME}-reference-import-panels \
   --uri "https://australia-southeast1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/seqr-308602/jobs/${ENV_NAME}-reference-import-panels:run" \
   --description "${ENV_NAME}: Import Panels" \
   --schedule "5 0 * * 0" \
   --time-zone "Australia/Melbourne" \
   --oauth-service-account-email ${SERVICE_ACCOUNT}

gcloud scheduler jobs create http --location australia-southeast1 \
   ${ENV_NAME}-reference-updater \
   --uri "https://australia-southeast1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/seqr-308602/jobs/${ENV_NAME}-reference-updater:run" \
   --description "${ENV_NAME}: Update references" \
   --schedule "10 0 * * 0" \
   --time-zone "Australia/Melbourne" \
   --oauth-service-account-email ${SERVICE_ACCOUNT}
