import clickhouse_connect
import sys

def setup_clickhouse_test_data(host, port, username, password):
    client = clickhouse_connect.get_client(host=host, port=port, username=username, password=password)
    client.command('CREATE DATABASE test_seqr')

    client.command('CREATE TABLE test_seqr.`GRCh37/SNV_INDEL/key_lookup` (`variantId` String, `key` UInt32 CODEC(Delta(8), ZSTD(1))) ENGINE = EmbeddedRocksDB(0) PRIMARY KEY variantId')
    client.insert('GRCh37/SNV_INDEL/key_lookup', data=[['7-143270172-A-G', 1], ['1-39190091-T-G', 2]], database='test_seqr')
    client.command(
        'CREATE DICTIONARY test_seqr.`GRCh37/SNV_INDEL/gt_stats_dict` (key UInt32, ac_wes UInt32, ac_wgs UInt32, hom_wes UInt32, hom_wgs UInt32) PRIMARY KEY key SOURCE(CLICKHOUSE(USER %s PASSWORD %s QUERY "SELECT * FROM VALUES ((1, 4104, 607, 1276, 232), (2, 7, 2, 2, 1))")) LIFETIME(0) LAYOUT(FLAT(MAX_ARRAY_SIZE 500000000))',
        parameters=(username, password),
    )

    client.command('CREATE TABLE test_seqr.`GRCh38/SNV_INDEL/key_lookup` (`variantId` String, `key` UInt32 CODEC(Delta(8), ZSTD(1))) ENGINE = EmbeddedRocksDB(0) PRIMARY KEY variantId')
    client.insert('GRCh38/SNV_INDEL/key_lookup', data=[['1-38724419-T-G', 1]], database='test_seqr')
    client.command(
        'CREATE DICTIONARY test_seqr.`GRCh38/SNV_INDEL/gt_stats_dict` (key UInt32, ac_wes UInt32, ac_wgs UInt32, hom_wes UInt32, hom_wgs UInt32) PRIMARY KEY key SOURCE(CLICKHOUSE(USER %s PASSWORD %s QUERY "SELECT * FROM VALUES ((1, 18, 10, 3, 1))")) LIFETIME(0) LAYOUT(FLAT(MAX_ARRAY_SIZE 500000000))',
        parameters=(username, password),
    )

    client.command("CREATE USER vlm_test_user IDENTIFIED WITH plaintext_password BY 'vlm_test_password'")
    client.command('GRANT SELECT ON test_seqr.`GRCh37/SNV_INDEL/key_lookup` TO vlm_test_user')
    client.command('GRANT SELECT ON test_seqr.`GRCh38/SNV_INDEL/key_lookup` TO vlm_test_user')
    client.command('GRANT dictGet ON test_seqr.`GRCh37/SNV_INDEL/gt_stats_dict` TO vlm_test_user')
    client.command('GRANT dictGet ON test_seqr.`GRCh38/SNV_INDEL/gt_stats_dict` TO vlm_test_user')


if __name__ == '__main__':
    args = sys.argv[1:]
    setup_clickhouse_test_data(*args)
