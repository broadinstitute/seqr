const autoprefixer = require('autoprefixer');
const path = require('path');
const webpack = require('webpack');
const ESLintPlugin = require('eslint-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const CaseSensitivePathsPlugin = require('case-sensitive-paths-webpack-plugin');
const PurgeCSSPlugin = require('purgecss-webpack-plugin');
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;
const eslintFormatter = require('react-dev-utils/eslintFormatter');
const glob = require('glob');
const paths = require('./paths');


// This is the development configuration.

const commonEntryModules = [
  // Include an alternative client for WebpackDevServer. A client's job is to
  // connect to WebpackDevServer by a socket and get notified about changes.
  // When you save a file, the client will either apply hot updates (in case
  // of CSS changes), or refresh the page (in case of JS changes). When you
  // make a syntax error, this client will display a syntax error overlay.
  // Note: instead of the default WebpackDevServer client, we use a custom one
  // to bring better experience for Create React App users. You can replace
  // the line below with these two lines if you prefer the stock client:
  // require.resolve('webpack-dev-server/client') + '?/',
  // require.resolve('webpack/hot/dev-server'),
  //require.resolve('react-dev-utils/webpackHotDevClient'),
  // We ship a few polyfills by default:
  require.resolve('./polyfills'),
]

// This is the development configuration.
// It is focused on developer experience and fast rebuilds.
// The production configuration is different and lives in a separate file.
module.exports = {

  mode: 'development',

  devtool: 'eval', //'cheap-module-eval-source-map', //'cheap-module-source-map', //'eval',

  entry: {
    app: [
      ...commonEntryModules,
      require.resolve('../app.jsx'),
    ],
  },

  output: {
    filename: '[name].js',
    // This is the URL that app is served from. We use "/" in development.
    publicPath: '/',
    pathinfo: true,
  },
  resolve: {
    // This allows you to set a fallback for where Webpack should look for modules.
    // We placed these paths second because we want `node_modules` to "win"
    // if there are any conflicts. This matches Node resolution mechanism.
    // https://github.com/facebookincubator/create-react-app/issues/253
    modules: ['node_modules', paths.appNodeModules].concat(
      // It is guaranteed to exist because we tweak it in `env.js`
      process.env.NODE_PATH.split(path.delimiter).filter(Boolean)
    ),
    // These are the reasonable defaults supported by the Node ecosystem.
    // We also include JSX as a common component filename extension to support
    // some tools, although we do not recommend using it, see:
    // https://github.com/facebookincubator/create-react-app/issues/290
    extensions: ['.mjs', '.js', '.json', '.jsx', '.css', '.ts', '.tsx'],
  },
  module: {
    strictExportPresence: true,
    rules: [
      {
        // "oneOf" will traverse all following loaders until one will
        // match the requirements
        oneOf: [
          // "asset" loader type automatically chooses between exporting a data URI and emitting a separate file
          // depending on file size
          {
            test: [/\.bmp$/, /\.gif$/, /\.jpe?g$/, /\.png$/],
            type: 'asset',
            generator: {
              filename: '[name].[contenthash:8][ext]'
            },
          },
          // Process JS with Babel.
          {
            test: /\.(js|jsx|mjs)$/,
            loader: require.resolve('babel-loader'),
            options: {
              compact: false,
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
            use: [
              {
                loader: require.resolve('style-loader'),
                options: {
                  insert: (styleElement) => {
                    styleElement.setAttribute('nonce', window.__webpack_nonce__)
                    document.querySelector('head').appendChild(styleElement)
                  },
                },
              },
              {
                loader: require.resolve('css-loader'),
                options: {
                  importLoaders: 1,
                },
              },
              {
                loader: require.resolve('postcss-loader'),
                options: {
                  postcssOptions: {
                    // Necessary for external CSS imports to work
                    // https://github.com/facebookincubator/create-react-app/issues/2677
                    ident: 'postcss',
                    plugins: [
                      require('postcss-flexbugs-fixes'),
                      autoprefixer({
                        flexbox: 'no-2009',
                      }),
                    ],
                  },
                },
              },
            ],
          },
          {
            test: /\.(png|woff|woff2|eot|ttf|svg)$/,
            type: 'asset/inline',
          },
          {
            test: /\.(ts|tsx)$/,
            loader: require.resolve("ts-loader"),
          },
        ],
      },
    ],
  },
  plugins: [
    new ESLintPlugin({
      formatter: eslintFormatter,
      extensions: ['js', 'jsx', '.ts', '.tsx'],
    }),
    new webpack.LoaderOptionsPlugin({ options: {} }),

    new PurgeCSSPlugin({
      paths: glob.sync(path.join(__dirname, 'pages/*.html')),
    }),

    new HtmlWebpackPlugin({
      filename: 'app.html',
      chunks: ['app', 'devServerClient'],
      template: path.resolve('./app.html'), // Load a custom template
      inject: true,
    }),

    // Makes some environment variables available to the JS code, for example:
    // if (process.env.NODE_ENV === 'development') { ... }. See `./env.js`.
    new webpack.DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify('development'),
    }),
    new CaseSensitivePathsPlugin(),
    // Moment.js is an extremely popular library that bundles large locale files
    // by default due to how Webpack interprets its code. This is a practical
    // solution that requires the user to opt into importing specific locales.
    // https://github.com/jmblog/how-to-optimize-momentjs-with-webpack
    // You can remove this if you don't use Moment.js:
    new webpack.IgnorePlugin({
      resourceRegExp: /^\.\/locale$/,
      contextRegExp: /moment$/,
    }),

    new webpack.ProvidePlugin({
      $: "jquery/dist/jquery.min",
      d3: require.resolve('./d3-bundle'),
    }),

    new BundleAnalyzerPlugin({
      // Opens a browser tab with detailed breakdown of bundle size. Set analyzerMode to 'server' to enable
      analyzerMode: 'disabled', // 'server'
    }),
  ],
  // Turn off performance hints during development because we don't do any
  // splitting or minification in interest of speed. These warnings become
  // cumbersome.
  performance: {
    hints: false,
  },
};
