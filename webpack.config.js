var path = require("path")
var webpack = require('webpack')
var HtmlWebpackPlugin = require('html-webpack-plugin')
var BundleTracker = require('webpack-bundle-tracker')

module.exports = {
    context: __dirname,

    /**
     * To define a new single-page app:
     * 1) add entry point  (this will be compiled into [name]-[hash].js)
     * 2) add HtmlWebpackPlugin to generate html based on template.ejs which contains the common imports (also specify title)
     */
    entry: {
        dashboard: ['./assets/pages/dashboard/dashboard.jsx', 'webpack/hot/only-dev-server'],
        //dashboard: ['./assets/pages/families/families.jsx', 'webpack/hot/only-dev-server'],
        search: ['./assets/pages/search/search.jsx', 'webpack/hot/only-dev-server'],

        devServerClient: 'webpack-dev-server/client?http://localhost:3000',
    },

    output: {
        path: path.resolve('./assets/bundles/'),
        filename: '[name]-[hash].js',
        publicPath: '/assets/bundles/',   // Tell django to use this URL to load packages and not use STATIC_URL + bundle_name
        hash: true,
    },

    plugins: [
        new webpack.HotModuleReplacementPlugin(),
        new webpack.NoErrorsPlugin(), // don't reload page if there is an error
        new BundleTracker({filename: './webpack-stats.json'}),

        //new webpack.ProvidePlugin({
        //    $: 'jquery', // used by Bootstrap
        //    jQuery: 'jquery' // used by Bootstrap
        //}),

        new HtmlWebpackPlugin({
            title: 'seqr',
            filename: 'dashboard.html',
            chunks: ['dashboard', 'devServerClient'],
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
            title: 'seqr',
            filename: 'search.html',
            chunks: ['search', 'devServerClient'],
            template: path.resolve('./assets/react-template.ejs'), // Load a custom template
        }),
    ],

    module: {
        loaders: [
            //{ // needed for using Bootstrap
            //    test: /\.(ttf|eot|svg|woff(2)?)(\?[a-z0-9]+)?$/,
            //    loader: 'file-loader'
            //},
            {test: /\.jsx?$/, exclude: /node_modules/, loaders: [
                'react-hot',
                'babel?'+JSON.stringify({presets: ['react', 'es2015']}),
                'eslint-loader'
            ]}, // we pass the output from babel loader to react-hot loader
            {test: /\.js$/, exclude: /node_modules/, loader: 'babel-loader!eslint-loader'},
            {test: /\.css$/, exclude: /node_modules/, loader: 'style-loader!css-loader'},
            {test: /\.scss$/, exclude: /node_modules/, loader: 'style!css!sass'}
        ],
    },

    resolve: {
        modulesDirectories: ['node_modules', 'bower_components'],
        extensions: ['', '.js', '.jsx', '.css']
    },
    
    eslint: {
        extends: "eslint:recommended",
        rules: {
            "semi": "off",
            "linebreak-style": [ "error", "unix" ],
            "no-unused-vars": "off"
        },
        parserOptions: {
            ecmaFeatures: {
                experimentalObjectRestSpread: true,
                jsx: true
            },
            sourceType: "module"
        },
        plugins: [ "react" ],
    },

    babel: {
        // list of plugins: http://babeljs.io/docs/plugins/transform-exponentiation-operator/
        "plugins": [
            "babel-plugin-transform-object-rest-spread",
            "babel-plugin-transform-exponentiation-operator"
        ],
    }
}

