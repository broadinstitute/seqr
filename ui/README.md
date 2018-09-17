This directory contains seqr pages that are built with React.js, Redux, and Semantic UI.


**Dependencies**

1. install `node` and `npm`
2. install javascript dependencies, run:
```
npm install
```

**Build**

Commands for dev. and production builds:

*Development:*

If you have seqr deployed locally on minikube (recommended):

```
# open 2 terminals - one for running the node development server directly on your laptop, and one for proxying webpage API requests to the seqr server that's running inside minikube

# in terminal A

cd $SEQR_ROOT/ui/
npm run test    # (optional) run client-side tests
npm run start   # starts a node development server on localhost:3000

# in terminal B

cd $SEQR_ROOT
./servctl connect-to seqr minikube   # proxy localhost:8000 to the gunicorn server inside kubernetes seqr pod
```

You should now be able to access seqr at [http://localhost:3000/dashboard](http://localhost:3000/dashboard)


(Legacy) If you have seqr components running directly on your machine (instead of using kuberenetes and minikube), do:
```
cd $SEQR_PROJECT_ROOT
python manage.py runserver   # start the Django development server so that the APIs are online

cd ui/
npm run start   # start a node UI development server on port 3000, then go to localhost:3000/dashboard.html
```


*Production:*

```
npm run build  # create a new production build in the ui/dist directory
```


**Deployment**

The production build can be committed to github and deployed to the production server.

On the production server, run:

```
python manage.py collectstatic
```
to copy the compiled html, js and other files to the Django static web directory so that Django will serve them as static files.


---

NOTE: The build configuration was initially created with `create-react-app` and then "ejected".
Although the configuration has been customized, it's similar enough to the original to allow
comparison and copying of changes from the latest `create-react-app` releases.
