/*eslint no-undef: "error"*/

//how to optimize webpack builds:
//   https://hashnode.com/post/how-can-i-properly-use-webpack-to-build-the-production-version-of-my-app-cipoc4dzq029vnq53bglp5atk
//
//summary of webpack2 changes: https://gist.github.com/sokra/27b24881210b56bbaff7
//using react-line: https://www.npmjs.com/package/react-lite


const path = require('path')
const webpack = require('webpack')
//const ExtractTextPlugin = require('extract-text-webpack-plugin')
const HtmlWebpackPlugin = require('html-webpack-plugin')

const config = {

  context: __dirname,

  /**
   * To define a new single-page app:
   * 1) add entry to webpack.dev.config.js and webpack.prod.config.js (this will be compiled into [name]-[hash].js)
   * 2) add HtmlWebpackPlugin to generate html based on template.ejs
   */


  devtool: 'source-map',

  output: {
    path: path.resolve('./assets/bundles/'), // override django's STATIC_URL for webpack bundles
    filename: '[name]-[hash].js',
    publicPath: '/assets/bundles/',   // Tell django to use this URL to load packages and not use STATIC_URL + bundle_name
    //hash: true,
  },

  plugins: [

    /*
    new HtmlWebpackPlugin({
      title: 'seqr',
      filename: 'dashboard.html',
      chunks: ['dashboard', 'devServerClient'],
      template: path.resolve('./assets/react-template.ejs'),
    }),


     new HtmlWebpackPlugin({
     title: 'seqr',
     filename: 'families.html',
     chunks: ['families', 'devServerClient'],
     template: path.resolve('./assets/react-template.ejs'),
     }),

    new HtmlWebpackPlugin({
      title: 'seqr: Search',
      filename: 'search.html',
      chunks: ['search', 'devServerClient'],
      template: path.resolve('./assets/react-template.ejs'), // Load a custom template
    }),
     */

    /*
    new webpack.ProvidePlugin({   //used by http://alex-d.github.io/Trumbowyg/
      $: 'jquery',
      jQuery: 'jquery',
    }),
    */

    new webpack.NoErrorsPlugin(),

    new HtmlWebpackPlugin({
      title: 'seqr: Case Review',
      initial_url: '/api/project/1/case_review_data',
      filename: 'case_review.html',
      chunks: ['case_review', 'devServerClient'],
      template: path.resolve('./assets/react-template.ejs'), // Load a custom template
    }),

    //new ExtractTextPlugin('style.css'), //described here: http://survivejs.com/webpack/building-with-webpack/separating-css/
  ],

  module: {
    loaders: [
      //{ test: /\.css$/, exclude: /node_modules/, loader: ExtractTextPlugin.extract('style-loader', 'css-loader') },
      //{ test: /\.scss$/, loader: 'style!css!sass!' },
      //{ test: /\.js$/, include: /node_modules/, loader: 'babel' },
      { test: /\.css$/, exclude: /node_modules/, loader: 'style!css!' },
      { test: /\.js$/, exclude: /node_modules/, loaders: ['babel-loader', 'eslint-loader'] },
    ],
  },

  resolve: {
    extensions: ['.js', '.jsx', '.css'],
  },
}

module.exports = config

