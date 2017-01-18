/*eslint no-undef: "error"*/

const path = require('path')
const webpack = require('webpack')
const BundleTracker = require('webpack-bundle-tracker')
const validate = require('webpack-validator')

const config = require('./webpack.base.config')

// Use webpack dev server
config.entry = {
  //dashboard: ['./assets/pages/dashboard/dashboard.jsx'],
  //dashboard: ['./assets/pages/families/families.jsx'],
  //search: ['./assets/pages/search/search.jsx'],
  case_review: ['./assets/pages/case-review/CaseReviewPage.jsx'],
}

config.output.path = path.resolve('./assets/dist')
config.output.publicPath = '/static/dist/'


config.plugins = [
  new webpack.DefinePlugin({
    // removes a lot of debugging code in React
    'process.env.NODE_ENV': JSON.stringify('production'),
  }),


  new webpack.optimize.OccurrenceOrderPlugin(), // keeps hashes consistent between builds

  ...config.plugins,

  new BundleTracker({ filename: './webpack-stats-prod.json' }),

  new webpack.LoaderOptionsPlugin({
    minimize: true,
    debug: false,
  }),
  new webpack.optimize.UglifyJsPlugin({
    beautify: false,
    compressor: {
      dead_code: true,
      evaluate: true,
      booleans: true,
      drop_debugger: true,
      warnings: false,
      reduce_vars: true,
      collapse_vars: true,
    },
  }),
]

config.module.loaders = [
  { test: /\.jsx$/, exclude: /node_modules/, loaders: ['babel-loader', 'eslint-loader'] },
  ...config.module.loaders,
]

module.exports = validate(config)
