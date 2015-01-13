require 'socket'
require 'timeout'


module Puppet
  module Util
    class MongodbValidator
      attr_reader :mongodb_server
      attr_reader :mongodb_port

      def initialize(mongodb_server, mongodb_port)
        @mongodb_server = mongodb_server
        @mongodb_port   = mongodb_port
      end

      # Utility method; attempts to make an https connection to the mongodb server.
      # This is abstracted out into a method so that it can be called multiple times
      # for retry attempts.
      #
      # @return true if the connection is successful, false otherwise.
      def attempt_connection
        Timeout::timeout(Puppet[:configtimeout]) do
          begin
            TCPSocket.new(@mongodb_server, @mongodb_port).close
            true
          rescue Errno::ECONNREFUSED, Errno::EHOSTUNREACH => e
            Puppet.debug "Unable to connect to mongodb server (#{@mongodb_server}:#{@mongodb_port}): #{e.message}"
            false
          end
        end
      rescue Timeout::Error
        false
      end
    end
  end
end

