from __future__ import unicode_literals

import json
import mock
from unittest import TestCase
from seqr.utils.redis_utils import safe_redis_set_json, safe_redis_get_json


@mock.patch('seqr.utils.redis_utils.logger')
@mock.patch('seqr.utils.redis_utils.redis.StrictRedis')
class RedisUtilsTest(TestCase):

    def test_safe_redis_get_json(self, mock_redis, mock_logger):
        # test with valid json
        mock_redis.return_value.get.side_effect = lambda key: json.dumps({key: 'test'})
        self.assertDictEqual(safe_redis_get_json('test_key'), {'test_key': 'test'})
        mock_logger.info.assert_called_with('Loaded test_key from redis')
        mock_logger.warn.assert_not_called()

        # test with no value in cache
        mock_logger.reset_mock()
        mock_redis.return_value.get.side_effect = lambda key: None
        self.assertIsNone(safe_redis_get_json('test_key'))
        mock_logger.info.assert_not_called()
        mock_logger.warn.assert_not_called()

        # test with invalid json in cache
        mock_logger.reset_mock()
        mock_redis.return_value.get.side_effect = lambda key: key
        self.assertIsNone(safe_redis_get_json('test_key'))
        mock_logger.info.assert_called_with('Loaded test_key from redis')
        warn_args = str(mock_logger.warn.call_args.args[0])
        # Python 2 and 3 return different warning when encountering JSON decoding error
        self.assertIn(warn_args, ['Unable to fetch "test_key" from redis: No JSON object could be decoded',
                                  'Unable to fetch "test_key" from redis: Expecting value: line 1 column 1 (char 0)'])

        # test with redis connection error
        mock_logger.reset_mock()
        mock_redis.side_effect = Exception('invalid redis')
        self.assertIsNone(safe_redis_get_json('test_key'))
        mock_logger.info.assert_not_called()
        mock_logger.warn.assert_called_with('Unable to connect to redis host localhost: invalid redis')

    def test_safe_redis_set_json(self, mock_redis, mock_logger):
        safe_redis_set_json('test_key', {'a': 1})
        mock_redis.return_value.set.assert_called_with('test_key', '{"a": 1}')
        mock_logger.warn.assert_not_called()

        # test with redis connection error
        mock_logger.reset_mock()
        mock_redis.side_effect = Exception('invalid redis')
        safe_redis_set_json('test_key', {'a': 1})
        mock_logger.warn.assert_called_with('Unable to write to redis host localhost: invalid redis')
