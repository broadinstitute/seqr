This directory contains the new seqr user interface (UI) that's based on React.js+JSX, Redux, and Semantic UI.
The build configuration was initially generated using `create-react-up`, and then "ejected" to allow some relatively minor customization. 

**Dependencies**

Building this UI requires node and npm to be installed. 

To install dependencies, run:
```
npm install 
```

**Build**

These are the main commands for dev. and production builds:

*Development:*

```
python manage.py runserver   # start the Django development server so that the APIs are online
npm run start   # start a node UI development server on port 3000, then go to localhost:3000/dashboard.html
npm run test    # run client-side tests
```

*Production:*

```
npm run build  # create a new production build in the ui/dist directory
```

**Deployment**

New production builds of the UI are simply committed to github and then pushed to the production server.
Then on the production server, the Django collectstatic command will copy these files into the static web directory.

```
python manage.py collectstatic
```

