'use strict';

// Do this as the first thing so that any code reading it knows the right env.
process.env.BABEL_ENV = 'development';
process.env.NODE_ENV = 'development';

// Makes the script crash on unhandled rejections instead of silently
// ignoring them. In the future, promise rejections that are not handled will
// terminate the Node.js process with a non-zero exit code.
process.on('unhandledRejection', err => {
  throw err;
});

// Ensure environment variables are read.
require('../config/env');

const fs = require('fs');
const webpack = require('webpack');
const WebpackDevServer = require('webpack-dev-server');
const { createCompiler, prepareUrls } = require('react-dev-utils/WebpackDevServerUtils');
const paths = require('../config/paths');
const config = require('../config/webpack.config.dev');
const createDevServerConfig = require('../config/webpackDevServer.config');

const useYarn = fs.existsSync(paths.yarnLockFile);

const https = process.env.HTTPS === 'true'
const protocol = https ? 'https' : 'http';
const host = process.env.HOST || 'localhost';
const port = parseInt(process.env.PORT, 10) || 3000;

const appName = require(paths.appPackageJson).name;
const urls = prepareUrls(protocol, host, port);
// Create a webpack compiler that is configured with custom messages.
const compiler = createCompiler({ webpack, config, appName, urls, useYarn });
const serverConfig = createDevServerConfig({ https, host, port });
new WebpackDevServer(serverConfig, compiler).start();
