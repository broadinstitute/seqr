# Developer startup

Install dependencies:
- Postgres
- Node + npm
- Python and Conda


1. Clone repository:

   ```shell
   git clone git@github.com:populationgenomics/seqr.git
   git checkout dev
   ```

1. Build UI

   ```shell
   cd ui/
   npm install
   npm run build
   cp dist/* ../static/
   cd ..
   ```

1. Build seqr python environment

   ```shell
   conda create -n seqr python=3.7
   conda activate seqr
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
   
1. Run migrations to set-up Postgres database

   ```shell
   psql --host localhost -U postgres -c 'CREATE DATABASE reference_data_db';
   psql --host localhost -U postgres -c 'CREATE DATABASE seqrdb';
   python -u manage.py makemigrations
   python -u manage.py migrate
   python -u manage.py migrate --database=reference_data
   python -u manage.py check
   python -u manage.py collectstatic --no-input
   python -u manage.py loaddata variant_tag_types
   python -u manage.py loaddata variant_searches
   python -u manage.py update_all_reference_data --use-cached-omim
   ```

1. Create seqr superuser

   ```bash
   python manage.py createsuperuser
   ```

1. Run seqr in debug mode:

   ```shell
   python3 manage.py runserver
   ```

   OR debug in VSCode with the following launch json:

   ```json
   {
       "name": "Python: Current File",
       "type": "python",
       "request": "launch",
       "program": "manage.py",
       "args": ["runserver"],
       "console": "integratedTerminal"
   }
   ```

    By default, this serves the seqr UI.


## Debug seqr UI

You can run the seqr UI separately with:

> This will automatically proxy seqr requests to localhost:8000, so make sure you have the python server running.

```shell
cd ui
npm run start
open http://localhost:3000
```

