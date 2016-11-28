/*eslint no-undef: "error"*/

const config = require('./webpack.base.config.js')
const webpack = require('webpack')
const BundleTracker = require('webpack-bundle-tracker')

// Use webpack dev server
config.entry = {
  //dashboard: ['./assets/pages/dashboard/dashboard.jsx'],
  //dashboard: ['./assets/pages/families/families.jsx'],
  //search: ['./assets/pages/search/search.jsx'],
  case_review: ['./assets/pages/case-review/CaseReview.jsx'],
}

config.output.path = './assets/dist'


config.plugins = [
  new webpack.DefinePlugin({
    // removes a lot of debugging code in React
    'process.env.NODE_ENV': JSON.stringify('production'),
  }),


  new webpack.optimize.OccurenceOrderPlugin(), // keeps hashes consistent between builds

  ...config.plugins,

  new BundleTracker({ filename: './webpack-stats-prod.json' }),

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
  { test: /\.jsx$/, exclude: /node_modules/, loaders: ['babel', 'eslint-loader'] },
  ...config.module.loaders,
]

module.exports = config
