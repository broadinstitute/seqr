/*eslint no-undef: "error"*/

var path = require('path')
var HtmlWebpackPlugin = require('html-webpack-plugin')
var WebpackCleanupPlugin = require('webpack-cleanup-plugin')
var BundleTracker = require('webpack-bundle-tracker')
var webpack = require('webpack')

const config = {
    context: __dirname,

    /**
     * To define a new single-page app:
     * 1) add entry point  (this will be compiled into [name]-[hash].js)
     * 2) add HtmlWebpackPlugin to generate html based on template.ejs which contains the common imports (also specify title)
     */

    output: {
        path: path.resolve('./assets/bundles/'),
        filename: '[name]-[hash].js',
        publicPath: '/assets/bundles/',   // Tell django to use this URL to load packages and not use STATIC_URL + bundle_name
        //hash: true,
    },

    plugins: [
        //new webpack.ProvidePlugin({
        //    $: 'jquery', // used by Bootstrap
        //    jQuery: 'jquery' // used by Bootstrap
        //}),
        new WebpackCleanupPlugin(),

        new HtmlWebpackPlugin({
            title: 'seqr',
            filename: 'dashboard.html',
            chunks: ['Dashboard', 'devServerClient'],
            template: path.resolve('./assets/react-template.ejs'), // Load a custom template
        }),

        /*
        new HtmlWebpackPlugin({
            title: 'seqr',
            filename: 'families.html',
            chunks: ['families', 'devServerClient'],
            template: path.resolve('./assets/react-template.ejs'), // Load a custom template
        }),
        */

        
        new HtmlWebpackPlugin({
            title: 'seqr: Search',
            filename: 'search.html',
            chunks: ['Search', 'devServerClient'],
            template: path.resolve('./assets/react-template.ejs'), // Load a custom template
        }),

        new HtmlWebpackPlugin({
            title: 'seqr: Case Review',
            filename: 'case_review.html',
            chunks: ['CaseReview', 'devServerClient'],
            template: path.resolve('./assets/react-template.ejs'), // Load a custom template
        }),
    ],

    module: {
        loaders: [
            //{test: /\.(ttf|eot|svg|woff(2)?)(\?[a-z0-9]+)?$/, loader: 'file-loader'}, // needed for Bootstrap
            {test: /\.css$/, exclude: /node_modules/, loader: 'style-loader!css-loader'},
            {test: /\.scss$/, exclude: /node_modules/, loader: 'style!css!sass'}
        ],
    },

    resolve: {
        modulesDirectories: ['node_modules', 'bower_components'],
        extensions: ['', '.js', '.jsx', '.css']
    },
}

module.exports = config

