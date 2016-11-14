/*eslint no-undef: "error"*/

var webpack = require('webpack')
var BundleTracker = require('webpack-bundle-tracker')

var config = require('./webpack.base.config.js')

config.output.path = require('path').resolve('./assets/dist')


// Use webpack dev server
config.entry = {
    dashboard: ['./assets/pages/dashboard/dashboard.jsx' ],
    //dashboard: ['./assets/pages/families/families.jsx'],
    search: ['./assets/pages/search/search.jsx' ],
},


config.plugins = config.plugins.concat([
    new BundleTracker({filename: './webpack-stats-prod.json'}),

    // removes a lot of debugging code in React
    new webpack.DefinePlugin({
        'process.env.NODE_ENV': JSON.stringify('production')
    }),

    // keeps hashes consistent between compilations
    new webpack.optimize.OccurenceOrderPlugin(),

    // minifies the code
    new webpack.optimize.UglifyJsPlugin({
        compressor: {
            warnings: false
        }
    })
])

config.module.loaders.push(
    {test: /\.jsx?$/, exclude: /node_modules/, loaders: [ 'babel', 'eslint-loader']}
)

module.exports = config