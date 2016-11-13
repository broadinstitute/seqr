/*eslint no-undef: "error"*/

var path = require("path")
var webpack = require('webpack')
var BundleTracker = require('webpack-bundle-tracker')

var config = require('./webpack.base.config.js')

// Use webpack dev server
config.entry = {
    dashboard:   [
        'webpack/hot/only-dev-server', 'webpack-dev-server/client?http://0.0.0.0:3000',
        './assets/pages/dashboard/Dashboard.jsx'
    ],
    //dashboard: ['webpack/hot/only-dev-server', './assets/pages/families/families.jsx'],
    search:      [
        'webpack/hot/only-dev-server', 'webpack-dev-server/client?http://0.0.0.0:3000',
        './assets/pages/search/Search.jsx'
    ],
    case_review: [
        'webpack/hot/only-dev-server', 'webpack-dev-server/client?http://0.0.0.0:3000',
        './assets/pages/case-review/CaseReview.jsx'
    ],
}

// override django's STATIC_URL for webpack bundles
config.output.publicPath = '/assets/bundles/'

// Add HotModuleReplacementPlugin and BundleTracker plugins
config.plugins = [
    new webpack.HotModuleReplacementPlugin(),
    new webpack.NoErrorsPlugin(),
    ...config.plugins,
    new BundleTracker({filename: './webpack-stats.json'}),
]


// Add a loader for JSX files with react-hot enabled
config.module.loaders = [
    {test: /\.jsx?$/, exclude: /node_modules/, loaders: [ 'react-hot', 'babel', 'eslint-loader'] },
    ...config.module.loaders
]

module.exports = config