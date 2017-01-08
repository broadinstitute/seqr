/*eslint no-undef: "error"*/

const autoprefixer = require('autoprefixer')
const fs = require('fs')
const path = require('path')
//const Purify = require('purifycss-webpack-plugin')
const validate = require('webpack-validator')
const webpack = require('webpack')

const CaseSensitivePathsPlugin = require('case-sensitive-paths-webpack-plugin')
const WebpackCleanupPlugin = require('webpack-cleanup-plugin')
const ExtractTextPlugin = require('extract-text-webpack-plugin')
const HtmlWebpackPlugin = require('html-webpack-plugin')
const PostCSSFontMagician = require('postcss-font-magician')
const PostCSSNext = require('postcss-cssnext')
const PostCSSNested = require('postcss-nested')

// Make sure any symlinks in the project folder are resolved:
// https://github.com/facebookincubator/create-react-app/issues/637
const appDirectory = fs.realpathSync(process.cwd())
function resolveApp(relativePath) {
  return path.resolve(appDirectory, relativePath)
}

const nodePaths = (process.env.NODE_PATH || '')
  .split(':').filter(Boolean).filter(folder => !path.isAbsolute(folder)).map(resolveApp)


const htmlPluginOptions = {
  inject: true,
  template: path.resolve('./pages/react-template.html'), // Load a custom template
  minify: {
    removeComments: true,
    collapseWhitespace: true,
    removeRedundantAttributes: true,
    useShortDoctype: true,
    removeEmptyAttributes: true,
    removeStyleLinkTypeAttributes: true,
    keepClosingSlash: true,
    minifyJS: true,
    minifyCSS: true,
    minifyURLs: true,
  },
}

const config = {

  context: __dirname,

  /**
   * To define a new single-page app:
   * 1) add entry to webpack.dev.config.js and webpack.prod.config.js (this will be compiled into [name]-[hash].js)
   * 2) add HtmlWebpackPlugin to generate html based on template.ejs
   */

  devtool: 'source-map',

  entry: {
    dashboard: [
      '../pages/Dashboard/DashboardPage',
    ],
    case_review: [
      '../pages/CaseReview/CaseReviewPage',
    ],
  },

  output: {
    path: path.resolve('./dist/'),
    filename: '[name]-[hash:8].js',
    publicPath: '/static/',
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
      // removes a lot of debugging code in React
      'process.env.NODE_ENV': JSON.stringify('production'),
    }),

    new WebpackCleanupPlugin(),

    new webpack.NoErrorsPlugin(),

    new HtmlWebpackPlugin(Object.assign({}, {
      filename: 'case_review.html',
      chunks: ['case_review'],
    }, htmlPluginOptions)),

    new HtmlWebpackPlugin(Object.assign({}, {
      filename: 'dashboard.html',
      chunks: ['dashboard'],
    }, htmlPluginOptions)),

    // This helps ensure the builds are consistent if source hasn't changed:
    new webpack.optimize.OccurrenceOrderPlugin(),
    // Try to dedupe duplicated modules, if any:
    new webpack.optimize.DedupePlugin(),
    // Minify the code.
    new webpack.optimize.UglifyJsPlugin({
      compress: {
        screw_ie8: true, // React doesn't support IE8
        warnings: false,
      },
      mangle: {
        screw_ie8: true,
      },
      output: {
        comments: false,
        screw_ie8: true,
      },
    }),
    // Note: this won't work without ExtractTextPlugin.extract(..) in `loaders`.
    new ExtractTextPlugin('[name].[contenthash:8].css'),
    new CaseSensitivePathsPlugin(),
  ],

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
      },
      // The notation here is somewhat confusing.
      // "postcss" loader applies autoprefixer to our CSS.
      // "css" loader resolves paths in CSS and adds assets as dependencies.
      // "style" loader normally turns CSS into JS modules injecting <style>,
      // but unlike in development configuration, we do something different.
      // `ExtractTextPlugin` first applies the "postcss" and "css" loaders
      // (second argument), then grabs the result CSS and puts it into a
      // separate file in our build process. This way we actually ship
      // a single CSS file in production instead of JS code injecting <style>
      // tags. If you use code splitting, however, any async bundles will still
      // use the "style" loader inside the async code so CSS from them won't be
      // in the main CSS file.
      {
        test: /\.css$/,
        loader: ExtractTextPlugin.extract('style', 'css-loader?modules&importLoaders=1&localIdentName=[name]__[local]___[hash:base64:5]!postcss-loader'),
        // Note: this won't work without `new ExtractTextPlugin()` in `plugins`.
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
      PostCSSFontMagician,
      PostCSSNext,
      PostCSSNested,
    ]
  },
}

module.exports = validate(config)
