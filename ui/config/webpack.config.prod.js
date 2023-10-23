/* eslint-disable global-require */

const autoprefixer = require('autoprefixer');
const ESLintPlugin = require('eslint-webpack-plugin');
const CssMinimizerPlugin = require("css-minimizer-webpack-plugin");
const path = require('path');
const webpack = require('webpack');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const CaseSensitivePathsPlugin = require('case-sensitive-paths-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const { WebpackManifestPlugin } = require('webpack-manifest-plugin');
const TerserPlugin = require("terser-webpack-plugin");
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;
const eslintFormatter = require('react-dev-utils/eslintFormatter');
const paths = require('./paths');
const getClientEnvironment = require('./env');

// Webpack uses `publicPath` to determine where the app is being served from.
// It requires a trailing slash, or the file assets will get an incorrect path.
const publicPath = paths.servedPath;
// `publicUrl` is just like `publicPath`, but we will provide it to our app
// as %PUBLIC_URL% in `index.html` and `process.env.PUBLIC_URL` in JavaScript.
// Omit trailing slash as %PUBLIC_URL%/xyz looks better than %PUBLIC_URL%xyz.
const publicUrl = publicPath.slice(0, -1);
// Get environment variables to inject into our app.
const env = getClientEnvironment(publicUrl);

// Assert this just to be safe.
// Development builds of React are slow and not intended for production.
if (env.stringified['process.env'].NODE_ENV !== '"production"') {
  throw new Error('Production builds must have NODE_ENV=production.');
}

// Note: defined here because it will be used more than once.
const cssFilename = '[name].[contenthash:8].css';

const htmlPluginOptions = {
  inject: true,
  template: path.resolve('./app.html'), // Load a custom template
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

// This is the production configuration.
// It compiles slowly and is focused on producing a fast and minimal bundle.
// The development configuration is different and lives in a separate file.
module.exports = {
  mode: 'production',
  // Don't attempt to continue if there are any errors.
  bail: true,

  entry: {
    app: [
      require.resolve('./polyfills'),
      require.resolve('../app.jsx'),
    ],
  },

  output: {
    path: path.resolve('./dist/'),
    filename: '[name]-[contenthash:8].js',
    publicPath: '/static/',
  },
  resolve: {
    // This allows you to set a fallback for where Webpack should look for modules.
    // We placed these paths second because we want `node_modules` to "win"
    // if there are any conflicts. This matches Node resolution mechanism.
    // https://github.com/facebookincubator/create-react-app/issues/253
    modules: ['node_modules', paths.appNodeModules],
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
            include: paths.appSrc,
            loader: require.resolve('babel-loader'),
            options: {
              compact: true,
            },
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
            use: [
              {
                loader: MiniCssExtractPlugin.loader,
              },
              {
                loader: require.resolve('css-loader'),
                options: {
                  sourceMap: true,
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
                  }
                },
              }
            ],
          },
          {
            test: /\.(png|woff|woff2|eot|ttf|svg)$/,
            type: 'asset',
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
    // Makes some environment variables available to the JS code, for example:
    // if (process.env.NODE_ENV === 'production') { ... }. See `./env.js`.
    // It is absolutely essential that NODE_ENV was set to production here.
    // Otherwise React will be compiled in the very slow development mode.
    new webpack.DefinePlugin({
      // removes a lot of debugging code in React
      'process.env.NODE_ENV': JSON.stringify('production'),
    }),

    new CleanWebpackPlugin(),

    new HtmlWebpackPlugin(Object.assign({}, {
      filename: 'app.html',
      chunks: ['app'],
    }, htmlPluginOptions)),

    new MiniCssExtractPlugin({
      filename: cssFilename,
    }),
    new CaseSensitivePathsPlugin(),

    // Generate a manifest file which contains a mapping of all asset filenames
    // to their corresponding output file so that tools can pick it up without
    // having to parse `index.html`.
    new WebpackManifestPlugin({
      fileName: 'asset-manifest.json',
    }),

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
  optimization: {
    minimize: true,
    minimizer: [
      new TerserPlugin({
        terserOptions: {
          format: {
            comments: false,
          },
        },
        extractComments: false,
      }),
      new CssMinimizerPlugin({
        minimizerOptions: {
          preset: [
            "default",
            {
              discardComments: { removeAll: true },
            },
          ],
        },
      }),
    ],
  },
};
