
* for now, instead of only using django 'views' as json api endpoints, and putting all UI logic strictly on the client side, continue
  to embed the react UI instead a generic django template.
  Benefits:
    - minimize initial page loading ajax calls (eg. to check login, populate initial data, page view log, etc.)

* use django webpack-loader (https://github.com/owais/django-webpack-loader) to embed the webpack-compiled js bundle into the html template

* avoid creating a separate django template for every page - use the same template for all pages
  Benefits:
    - keeps as much as possible of the UI code and logic on the client side
    - allows react hot-reloading with a node.js server
  Approach 1:
    - django template context:
        - webpack loader bundle name
        - initial json
    - django is optional - should be able to use ejs template instead
        - initial json should be optional - if null, page should load data from

* api design
   - based on http://www.vinaysahni.com/best-practices-for-a-pragmatic-restful-api
   - after the first api update, add versioning

* use Semantic-UI?
   - bootstrap doesn't make sense:
        - pile of random functionality and components
        - are you really supposed to hard-code different screen sizes into every element of your page?

* use JSX (https://facebook.github.io/react/docs/jsx-in-depth.html)

Useful links:
   https://www.codementor.io/reactjs/tutorial/redux-server-rendering-react-router-universal-web-app
   http://nerds.airbnb.com/isomorphic-javascript-future-web-apps/  (might revisit this later once it's more mature)
   https://www.terlici.com/2015/03/18/fast-react-loading-server-rendering.html