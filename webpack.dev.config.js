/*eslint no-undef: "error"*/

var path = require("path")
var webpack = require('webpack')
var BundleTracker = require('webpack-bundle-tracker')

var config = require('./webpack.base.config.js')

// Use webpack dev server
config.entry = {
    dashboard:   ['./assets/pages/dashboard/Dashboard.jsx',    'webpack/hot/only-dev-server'],
    //dashboard: ['./assets/pages/families/families.jsx', 'webpack/hot/only-dev-server'],
    search:      ['./assets/pages/search/Search.jsx',          'webpack/hot/only-dev-server'],
    case_review: ['./assets/pages/case-review/CaseReview.jsx', 'webpack/hot/only-dev-server']
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