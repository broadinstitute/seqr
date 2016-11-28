/*eslint-env: nodejs */

const webpack = require('webpack')
const WebpackDevServer = require('webpack-dev-server')
const config = require('./webpack.dev.config')

new WebpackDevServer(webpack(config), {
  publicPath: config.output.publicPath,
  hot: true,
  inline: true,
  historyApiFallback: true,
  proxy: [
    {
      context: ['/api', '/media', '/project'],
      target: 'http://localhost:8000',
      secure: true,
    },
  ],
}).listen(3000, '0.0.0.0', (err) => {
  if (err) {
    console.log(err)
  }

  console.log('Listening at 0.0.0.0:3000')
})
