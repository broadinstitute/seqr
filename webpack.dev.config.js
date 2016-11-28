/*eslint no-undef: "error"*/

const config = require('./webpack.base.config.js')
const webpack = require('webpack')
const BundleTracker = require('webpack-bundle-tracker')
const WebpackCleanupPlugin = require('webpack-cleanup-plugin')


// Use webpack dev server
config.entry = {
  /*
  dashboard: [
    'webpack/hot/only-dev-server', 'webpack-dev-server/client?http://0.0.0.0:3000',
    './assets/pages/dashboard/Dashboard.jsx',
  ],
  //dashboard: ['webpack/hot/only-dev-server', './assets/pages/families/families.jsx'],
  search: [
    'webpack/hot/only-dev-server', 'webpack-dev-server/client?http://0.0.0.0:3000',
    './assets/pages/search/Search.jsx',
  ],
  */
  case_review: [
    'webpack/hot/only-dev-server',
    'webpack-dev-server/client?http://0.0.0.0:3000',
    './assets/pages/case-review/CaseReview.jsx',
  ],
}

// Add HotModuleReplacementPlugin and BundleTracker plugins
config.plugins = [
  new webpack.HotModuleReplacementPlugin(),

  new WebpackCleanupPlugin(),

  ...config.plugins,

  new BundleTracker({ filename: './webpack-stats.json' }),

  new webpack.optimize.UglifyJsPlugin({
    beautify: true,
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

// Add a loader for JSX files with react-hot enabled
config.module.loaders = [
  { test: /\.jsx$/, exclude: /node_modules/, loaders: ['react-hot', 'babel', 'eslint-loader'] },
  ...config.module.loaders,
]

module.exports = config
