/*eslint-env: nodejs */

var webpack = require('webpack')
var WebpackDevServer = require('webpack-dev-server')
var config = require('./webpack.dev.config')

// TODO: proxy to django server  https://webpack.github.io/docs/webpack-dev-server.html

new WebpackDevServer(webpack(config), {
	publicPath: config.output.publicPath,
	hot: true,
	inline: true,
	historyApiFallback: true,
	proxy: {
	    '/seqr/api': {
		target: 'http://localhost:8000',
		secure: true
	    }
	}
}).listen(3000, '0.0.0.0', function (err, result) {
	if (err) {
        console.log(err)
	}

	console.log('Listening at 0.0.0.0:3000')
})
