const config = require('./webpack.config.dev');

module.exports = function(proxyConfig) {
  return {
    ...proxyConfig,
    //open the browser after server had been started.
    open: true,
    // Allows to close dev server and exit the process on SIGINT and SIGTERM signals.
    setupExitSignals: true,
    client: {
      // Silence WebpackDevServer's own logs since they're generally not useful.
      // It will still show compile warnings and errors with this setting.
      logging: 'none',
      overlay: false,
    },
    // Enable hot reloading server. It will provide /sockjs-node/ endpoint
    // for the WebpackDevServer client so it can learn when the files were
    // updated. The WebpackDevServer client is included as an entry point
    // in the Webpack development configuration. Note that only changes
    // to CSS are currently hot reloaded. JS changes will refresh the browser.
    hot: true,
    devMiddleware: {
      // It is important to tell WebpackDevServer to use the same "root" path
      // as we specified in the config. In development, we always serve from /.
      publicPath: config.output.publicPath,
    },
    proxy: [
      {
        context: ['/', '/api', '/media', '/project', '/login', '/logout', '/static', '/xstatic'],
        target: 'http://localhost:8000',
        secure: true,
      },
    ],
    historyApiFallback: {
      // Paths with dots should still use the history fallback.
      // See https://github.com/facebookincubator/create-react-app/issues/387.
      disableDotRule: true,
    },
  };
};
