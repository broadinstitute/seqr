const autoprefixer = require('autoprefixer')
const fs = require('fs')
const path = require('path')
const Purify = require('purifycss-webpack-plugin')
const validate = require('webpack-validator')
const webpack = require('webpack')

const CaseSensitivePathsPlugin = require('case-sensitive-paths-webpack-plugin')
const WebpackCleanupPlugin = require('webpack-cleanup-plugin')
const HtmlWebpackPlugin = require('html-webpack-plugin')


//how to optimize webpack builds:
//   https://hashnode.com/post/how-can-i-properly-use-webpack-to-build-the-production-version-of-my-app-cipoc4dzq029vnq53bglp5atk
//
//summary of webpack2 changes: https://gist.github.com/sokra/27b24881210b56bbaff7
//using react-line: https://www.npmjs.com/package/react-lite


// Make sure any symlinks in the project folder are resolved:
// https://github.com/facebookincubator/create-react-app/issues/637
const appDirectory = fs.realpathSync(process.cwd())
function resolveApp(relativePath) {
  return path.resolve(appDirectory, relativePath)
}

const nodePaths = (process.env.NODE_PATH || '')
  .split(':').filter(Boolean).filter(folder => !path.isAbsolute(folder)).map(resolveApp)

const config = {

  context: __dirname,

  /**
   * To define a new single-page app:
   * 1) add entry to webpack.dev.config.js and webpack.prod.config.js (this will be compiled into [name]-[hash].js)
   * 2) add HtmlWebpackPlugin to generate html based on template.ejs
   */

  devtool: 'cheap-module-source-map',

  entry: {
    //dashboard: ['./assets/pages/dashboard/dashboard.jsx'],
    case_review: [
      'react-dev-utils/webpackHotDevClient',
      './assets/pages/case-review/CaseReviewPage',
    ],
  },

  output: {
    path: path.resolve('./assets/bundles/'), // override django's STATIC_URL for webpack bundles
    filename: '[name]-[hash].js',
    publicPath: '/assets/bundles/',   // Tell django to use this URL to load packages and not use STATIC_URL + bundle_name
  },

  resolve: {
    // This allows you to set a fallback for where Webpack should look for modules.
    // We read `NODE_PATH` environment variable in `paths.js` and pass paths here.
    // We use `fallback` instead of `root` because we want `node_modules` to "win"
    // if there any conflicts. This matches Node resolution mechanism.
    // https://github.com/facebookincubator/create-react-app/issues/253
    fallback: nodePaths,
    // These are the reasonable defaults supported by the Node ecosystem.
    // We also include JSX as a common component filename extension to support
    // some tools, although we do not recommend using it, see:
    // https://github.com/facebookincubator/create-react-app/issues/290
    extensions: ['.js', '.json', '.jsx', '.css', ''],
  },

  plugins: [

    new webpack.NoErrorsPlugin(),

    new webpack.DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify('development'),
    }),

    new WebpackCleanupPlugin(),

    new webpack.NoErrorsPlugin(),

    new Purify({
      basePath: __dirname,
      paths: ['/assets/*template*.html'],
    }),

    // Generates an `index.html` file with the <script> injected.
    new HtmlWebpackPlugin({
      initial_url: '/api/project/1/case_review_data',
      filename: 'case_review.html',
      inject: true,
      chunks: ['case_review', 'devServerClient'],
      template: path.resolve('./assets/react-template.html'),
    }),

    // This is necessary to emit hot updates (currently CSS only):
    new webpack.HotModuleReplacementPlugin(),
    // Watcher doesn't work well if you mistype casing in a path so we use
    // a plugin that prints an error when you attempt to do this.
    // See https://github.com/facebookincubator/create-react-app/issues/240
    new CaseSensitivePathsPlugin(),
    //new ExtractTextPlugin('style.css'), //described here: http://survivejs.com/webpack/building-with-webpack/separating-css/
  ],

  /*
   dashboard: [
   'webpack/hot/only-dev-server', 'webpack-dev-server/client?http://0.0.0.0:3000',
   './assets/pages/dashboard/Dashboard.jsx',
   ],
   */


  module: {
    // First, run the linter.
    // It's important to do this before Babel processes the JS.
    preLoaders: [
      {
        test: /\.(js|jsx)$/,
        loader: 'eslint',
        exclude: /node_modules/,
      },
    ],
    loaders: [
      {
        test: /\.(png|eot|woff2|woff|ttf)$/,
        loader: 'url-loader',
      },

      // Process JS with Babel.
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        loader: 'babel',
        query: {

          // This is a feature of `babel-loader` for webpack (not Babel itself).
          // It enables caching results in ./node_modules/.cache/babel-loader/
          // directory for faster rebuilds.
          cacheDirectory: true,
        },
      },
      // "postcss" loader applies autoprefixer to our CSS.
      // "css" loader resolves paths in CSS and adds assets as dependencies.
      // "style" loader turns CSS into JS modules that inject <style> tags.
      // In production, we use a plugin to extract that CSS to a file, but
      // in development "style" loader enables hot editing of CSS.
      {
        test: /\.css$/,
        loader: 'style!css-loader?importLoaders=1!postcss-loader',
      },
      // JSON is not enabled by default in Webpack but both Node and Browserify
      // allow it implicitly so we also enable it.
      {
        test: /\.json$/,
        loader: 'json',
      },
      // "file" loader for svg
      {
        test: /\.svg$/,
        loader: 'file',
        query: {
          name: 'static/media/[name].[hash:8].[ext]',
        },
      },
    ],
  },

  // We use PostCSS for autoprefixing only.
  postcss: () => {
    return [
      autoprefixer({
        browsers: [
          '>1%',
          'last 4 versions',
          'Firefox ESR',
          'not ie < 9', // React doesn't support IE8 anyway
        ],
      }),
    ]
  },
}

module.exports = validate(config)
