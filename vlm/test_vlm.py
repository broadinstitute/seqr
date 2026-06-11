from aiohttp.test_utils import AioHTTPTestCase
from aioresponses import aioresponses
from datetime import datetime
import jwt
import logging
import pytest

from vlm.web_app import init_web_app

REQUESTER_CLIENT_ID = 'abc123'

class VlmTestCase(AioHTTPTestCase):

    async def get_application(self):
        return await init_web_app()

    async def test_error(self):
        async with self.client.request('GET', '/foo') as resp:
            self.assertEqual(resp.status, 404)

    async def test_status(self):
        async with self.client.request('GET', '/vlm/status') as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, {'success': True})

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        caplog.set_level(logging.INFO)
        self._caplog = caplog

    @aioresponses(passthrough=['http://127.0.0.1'])
    async def test_match(self, mocked_responses):
        response = {
            'beaconHandovers': [
                {
                    'handoverType': {
                        'id': 'TestVLM',
                        'label': 'TestVLM browser',
                    },
                    'url': 'https://test-seqr.org/variant_lookup?genomeVersion=38&variantId=1-38724419-T-G',
                    'email': None,
                }
            ],
            'meta': {
                'apiVersion': 'v1.0',
                'beaconId': 'com.gnx.beacon.v2',
                'returnedSchemas': [
                    {
                        'entityType': 'genomicVariant',
                        'schema': 'ga4gh-beacon-variant-v2.0.0',
                    }
                ]
            },
            'responseSummary': {
                'exists': True,
                'total': 7,
            },
            'response': {
                'resultSets': [
                    {
                        'exists': True,
                        'id': 'TestVLM Homozygous',
                        'results': [],
                        'resultsCount': 3,
                        'setType': 'genomicVariant'
                    },
                    {
                        'exists': True,
                        'id': 'TestVLM Heterozygous',
                        'results': [],
                        'resultsCount': 4,
                        'setType': 'genomicVariant'
                    },
                    {
                        'exists': False,
                        'id': 'TestVLM Hemizygous',
                        'results': [],
                        'resultsCount': 0,
                        'setType': 'genomicVariant'
                    },
                    {
                        'exists': False,
                        'id': 'TestVLM Unknown',
                        'results': [],
                        'resultsCount': 0,
                        'setType': 'genomicVariant'
                    },
                ],
            }
        }
        only_37_response = {
            'beaconHandovers': [
                {
                    'handoverType': {
                        'id': 'TestVLM',
                        'label': 'TestVLM browser',
                    },
                    'url': 'https://test-seqr.org/variant_lookup?genomeVersion=37&variantId=7-143270172-A-G',
                    'email': None,
                }
            ],
            'meta': {
                'apiVersion': 'v1.0',
                'beaconId': 'com.gnx.beacon.v2',
                'returnedSchemas': [
                    {
                        'entityType': 'genomicVariant',
                        'schema': 'ga4gh-beacon-variant-v2.0.0',
                    }
                ]
            },
            'responseSummary': {
                'exists': True,
                'total': 1,
            },
            'response': {
                'resultSets': [
                    {
                        'exists': True,
                        'id': 'TestVLM Homozygous',
                        'results': [],
                        'resultsCount': 1,
                        'setType': 'genomicVariant'
                    },
                    {
                        'exists': False,
                        'id': 'TestVLM Heterozygous',
                        'results': [],
                        'resultsCount': 0,
                        'setType': 'genomicVariant'
                    },
                    {
                        'exists': False,
                        'id': 'TestVLM Hemizygous',
                        'results': [],
                        'resultsCount': 0,
                        'setType': 'genomicVariant'
                    },
                    {
                        'exists': False,
                        'id': 'TestVLM Unknown',
                        'results': [],
                        'resultsCount': 0,
                        'setType': 'genomicVariant'
                    },
                ],
            }
        }
        empty_response = {
            'beaconHandovers': [
                {
                    'handoverType': {
                        'id': 'TestVLM',
                        'label': 'TestVLM browser',
                    },
                    'url': 'https://test-seqr.org/variant_lookup?genomeVersion=38&variantId=7-143270172-A-G',
                    'email': None,
                }
            ],
            'meta': {
                'apiVersion': 'v1.0',
                'beaconId': 'com.gnx.beacon.v2',
                'returnedSchemas': [
                    {
                        'entityType': 'genomicVariant',
                        'schema': 'ga4gh-beacon-variant-v2.0.0',
                    }
                ]
            },
            'responseSummary': {
                'exists': False,
                'total': 0,
            },
            'response': {
                'resultSets': [
                    {
                        'exists': False,
                        'id': 'TestVLM Homozygous',
                        'results': [],
                        'resultsCount': 0,
                        'setType': 'genomicVariant'
                    },
                    {
                        'exists': False,
                        'id': 'TestVLM Heterozygous',
                        'results': [],
                        'resultsCount': 0,
                        'setType': 'genomicVariant'
                    },
                    {
                        'exists': False,
                        'id': 'TestVLM Hemizygous',
                        'results': [],
                        'resultsCount': 0,
                        'setType': 'genomicVariant'
                    },
                    {
                        'exists': False,
                        'id': 'TestVLM Unknown',
                        'results': [],
                        'resultsCount': 0,
                        'setType': 'genomicVariant'
                    },
                ],
            }
        }
        await self._test_match_endpoint('match', mocked_responses, response, only_37_response, empty_response)

    @aioresponses(passthrough=['http://127.0.0.1'])
    async def test_match_details(self, mocked_responses):
        response = {
            'beaconHandovers': [
                {
                    'handoverType': {
                        'id': 'TestVLM',
                        'label': 'TestVLM browser',
                    },
                    'url': 'https://test-seqr.org/variant_lookup?genomeVersion=38&variantId=1-38724419-T-G',
                    'email': None,
                }
            ],
            'meta': {
                'apiVersion': 'v1.0',
                'beaconId': 'com.gnx.beacon.v2',
                'returnedSchemas': [
                    {
                        'entityType': 'Family',
                        'schema': 'phenopacket-2.0',
                    }
                ]
            },
            'responseSummary': {
                'exists': True,
                'total': 5,
            },
            'response': {
                'resultSets': [
                    {
                        'exists': True,
                        'id': 'TestVLM',
                        'setType': 'Family',
                        'resultsCount': 5,
                        'results': [{
                            'id': 'F_0',
                            'pedigree': {
                                 'persons': [{
                                     'affected_status': 'UNAFFECTED',
                                     'family_id': 'F_0',
                                     'individual_id': 'I_0_0',
                                     'maternal_id': '0',
                                     'paternal_id': '0',
                                     'sex': 'MALE',
                                 }, {
                                     'affected_status': 'AFFECTED',
                                     'family_id': 'F_0',
                                     'individual_id': 'I_0_1',
                                     'maternal_id': '0',
                                     'paternal_id': '0',
                                     'sex': 'OTHER_SEX',
                                 }],
                            },
                            'proband': {
                                'id': 'I_0_1',
                                'interpretations': [{
                                    'diagnosis': {
                                        'disease': {'id': 'OMIM:615123', 'label': None},
                                        'genomic_interpretations': [{
                                            'call': {
                                                'variation_descriptor': {
                                                    'allelic_state': {'id': 'GENO:0000136', 'label': 'homozygous'},
                                                },
                                            },
                                            'interpretation_status': 'UNKNOWN_STATUS',
                                            'subject_or_biosample_id': 'I_0_1',
                                        }],
                                    },
                                    'id': 'I_0_1',
                                    'progress_status': 'UNKNOWN_PROGRESS',
                                }],
                                'phenotypic_features': [
                                    {'id': 'HP:0002011', 'label': 'Morphological central nervous system abnormality'}, # TODO mock requests
                                    {'id': 'HP:0011675', 'label': 'Arrhythmia'},
                                ],
                                'subject': {
                                    'id': 'I_0_1',
                                    'sex': 'OTHER_SEX',
                                },
                                'meta_data': {
                                    'submitted_by': 'test@broadinstitute.org,vlm@broadinstitute.org',
                                    'phenopacket_schema_version': '2.0',
                                    'resources': [{
                                        'id': 'geno',
                                        'iriPrefix': 'http://purl.obolibrary.org/obo/GENO_',
                                        'name': 'GENO ontology',
                                        'namespacePrefix': 'GENO',
                                        'url': 'http://purl.obolibrary.org/obo/geno.owl',
                                        'version': '2026-02-02',
                                    }, {
                                        'id': 'hp',
                                        'iriPrefix': 'http://purl.obolibrary.org/obo/HP_',
                                        'name': 'Human Phenotype Ontology',
                                        'namespacePrefix': 'HP',
                                        'url': 'http://purl.obolibrary.org/obo/hp.owl',
                                        'version': datetime.now().strftime('%Y-%m-%d'),
                                    }, {
                                        'id': 'omim',
                                        'iriPrefix': 'https://www.omim.org/entry/',
                                        'name': 'Online Mendelian Inheritance in Man',
                                        'namespacePrefix': 'OMIM',
                                        'url': 'https://www.omim.org',
                                        'version': datetime.now().strftime('%Y-%m-%d'),
                                    }],
                                },
                            },
                            'relatives': [{
                                'id': 'I_0_0',
                                'interpretations': [{
                                    'diagnosis': {
                                        'disease': {'id': 'OMIM:615123', 'label': None},
                                        'genomic_interpretations': [{
                                            'call': {
                                                'variation_descriptor': {
                                                    'allelic_state': {'id': 'GENO:0000135', 'label': 'heterozygous'},
                                                },
                                            },
                                            'interpretation_status': 'UNKNOWN_STATUS',
                                            'subject_or_biosample_id': 'I_0_0',
                                        }],
                                    },
                                    'id': 'I_0_0',
                                    'progress_status': 'UNKNOWN_PROGRESS',
                                }],
                                'phenotypic_features': [],
                                'subject': {
                                    'id': 'I_0_0',
                                    'sex': 'MALE',
                                },
                                'meta_data': {
                                    'submitted_by': 'test@broadinstitute.org,vlm@broadinstitute.org',
                                    'phenopacket_schema_version': '2.0',
                                    'resources': [{
                                        'id': 'geno',
                                        'iriPrefix': 'http://purl.obolibrary.org/obo/GENO_',
                                        'name': 'GENO ontology',
                                        'namespacePrefix': 'GENO',
                                        'url': 'http://purl.obolibrary.org/obo/geno.owl',
                                        'version': '2026-02-02',
                                    }, {
                                        'id': 'omim',
                                        'iriPrefix': 'https://www.omim.org/entry/',
                                        'name': 'Online Mendelian Inheritance in Man',
                                        'namespacePrefix': 'OMIM',
                                        'url': 'https://www.omim.org',
                                        'version': datetime.now().strftime('%Y-%m-%d'),
                                    }],
                                },
                            }],
                            'meta_data': {'phenopacket_schema_version': '2.0', 'resources': []},
                        }, {
                            'id': 'F_1',
                            'pedigree': {
                                'persons': [{
                                    'affected_status': 'AFFECTED',
                                    'family_id': 'F_1',
                                    'individual_id': 'I_1_0',
                                    'maternal_id': '0',
                                    'paternal_id': '0',
                                    'sex': 'OTHER_SEX',
                                }],
                            },
                            'proband': {
                                'id': 'I_1_0',
                                'interpretations': [{
                                    'diagnosis': {
                                        'disease': {'id': 'OMIM:615123', 'label': None},
                                        'genomic_interpretations': [{
                                            'call': {
                                                'variation_descriptor': {
                                                    'allelic_state': {'id': 'GENO:0000136', 'label': 'homozygous'},
                                                },
                                            },
                                            'interpretation_status': 'UNKNOWN_STATUS',
                                            'subject_or_biosample_id': 'I_1_0',
                                        }],
                                    },
                                    'id': 'I_1_0',
                                    'progress_status': 'UNKNOWN_PROGRESS',
                                }],
                                'phenotypic_features': [
                                    {'id': 'HP:0002011', 'label': 'Morphological central nervous system abnormality'},
                                    {'id': 'HP:0011675', 'label': 'Arrhythmia'},
                                ],
                                'subject': {
                                    'id': 'I_1_0',
                                    'sex': 'OTHER_SEX',
                                },
                                'meta_data': {
                                    'submitted_by': 'test@broadinstitute.org,vlm@broadinstitute.org',
                                    'phenopacket_schema_version': '2.0',
                                    'resources': [{
                                        'id': 'geno',
                                        'iriPrefix': 'http://purl.obolibrary.org/obo/GENO_',
                                        'name': 'GENO ontology',
                                        'namespacePrefix': 'GENO',
                                        'url': 'http://purl.obolibrary.org/obo/geno.owl',
                                        'version': '2026-02-02',
                                    }, {
                                        'id': 'hp',
                                        'iriPrefix': 'http://purl.obolibrary.org/obo/HP_',
                                        'name': 'Human Phenotype Ontology',
                                        'namespacePrefix': 'HP',
                                        'url': 'http://purl.obolibrary.org/obo/hp.owl',
                                        'version': datetime.now().strftime('%Y-%m-%d'),
                                    }, {
                                        'id': 'omim',
                                        'iriPrefix': 'https://www.omim.org/entry/',
                                        'name': 'Online Mendelian Inheritance in Man',
                                        'namespacePrefix': 'OMIM',
                                        'url': 'https://www.omim.org',
                                        'version': datetime.now().strftime('%Y-%m-%d'),
                                    }],
                                },
                            },
                            'relatives': [],
                            'meta_data': {'phenopacket_schema_version': '2.0', 'resources': []},
                        }, {
                            'id': 'F_2',
                            'pedigree': {
                                'persons': [{
                                    'affected_status': 'MISSING',
                                    'family_id': 'F_2',
                                    'individual_id': 'I_2_0',
                                    'maternal_id': '0',
                                    'paternal_id': '0',
                                    'sex': 'UNKNOWN_SEX',
                                }, {
                                    'affected_status': 'MISSING',
                                    'family_id': 'F_2',
                                    'individual_id': 'I_2_1',
                                    'maternal_id': '0',
                                    'paternal_id': '0',
                                    'sex': 'UNKNOWN_SEX',
                                }],
                            },
                            'proband': {
                                'id': 'I_2_0',
                                'interpretations': [{
                                    'diagnosis': {
                                        'genomic_interpretations': [{
                                            'call': {
                                                'variation_descriptor': {
                                                    'allelic_state': {'id': 'GENO:0000135', 'label': 'heterozygous'},
                                                },
                                            },
                                            'interpretation_status': 'UNKNOWN_STATUS',
                                            'subject_or_biosample_id': 'I_2_0',
                                        }],
                                    },
                                    'id': 'I_2_0',
                                    'progress_status': 'UNKNOWN_PROGRESS',
                                }],
                                'phenotypic_features': [],
                                'subject': {
                                    'id': 'I_2_0',
                                    'sex': 'UNKNOWN_SEX',
                                },
                                'meta_data': {
                                    'submitted_by': '',
                                    'phenopacket_schema_version': '2.0',
                                    'resources': [{
                                        'id': 'geno',
                                        'iriPrefix': 'http://purl.obolibrary.org/obo/GENO_',
                                        'name': 'GENO ontology',
                                        'namespacePrefix': 'GENO',
                                        'url': 'http://purl.obolibrary.org/obo/geno.owl',
                                        'version': '2026-02-02',
                                    }],
                                },
                            },
                            'relatives': [{
                                'id': 'I_2_1',
                                'interpretations': [{
                                    'diagnosis': {
                                        'genomic_interpretations': [{
                                            'call': {
                                                'variation_descriptor': {
                                                    'allelic_state': {'id': 'GENO:0000136', 'label': 'homozygous'},
                                                },
                                            },
                                            'interpretation_status': 'UNKNOWN_STATUS',
                                            'subject_or_biosample_id': 'I_2_1',
                                        }],
                                    },
                                    'id': 'I_2_1',
                                    'progress_status': 'UNKNOWN_PROGRESS',
                                }],
                                'phenotypic_features': [],
                                'subject': {
                                    'id': 'I_2_1',
                                    'sex': 'UNKNOWN_SEX',
                                },
                                'meta_data': {
                                    'submitted_by': '',
                                    'phenopacket_schema_version': '2.0',
                                    'resources': [{
                                        'id': 'geno',
                                        'iriPrefix': 'http://purl.obolibrary.org/obo/GENO_',
                                        'name': 'GENO ontology',
                                        'namespacePrefix': 'GENO',
                                        'url': 'http://purl.obolibrary.org/obo/geno.owl',
                                        'version': '2026-02-02',
                                    }],
                                },
                            }],
                            'meta_data': {'phenopacket_schema_version': '2.0', 'resources': []},
                        }, {
                            'id': 'F_3',
                            'pedigree': {
                                'persons': [{
                                    'affected_status': 'AFFECTED',
                                    'family_id': 'F_3',
                                    'individual_id': 'I_3_0',
                                    'maternal_id': '0',
                                    'paternal_id': '0',
                                    'sex': 'MALE',
                                }],
                            },
                            'proband': {
                                'id': 'I_3_0',
                                'interpretations': [{
                                    'diagnosis': {
                                        'genomic_interpretations': [{
                                            'call': {
                                                'variation_descriptor': {
                                                    'allelic_state': {
                                                        'id': 'GENO:0000135', 'label': 'heterozygous'},
                                                },
                                            },
                                            'interpretation_status': 'UNKNOWN_STATUS',
                                            'subject_or_biosample_id': 'I_3_0',
                                        }],
                                    },
                                    'id': 'I_3_0',
                                    'progress_status': 'UNKNOWN_PROGRESS',
                                }],
                                'phenotypic_features': [],
                                'subject': {
                                    'id': 'I_3_0',
                                    'sex': 'MALE',
                                },
                                'meta_data': {
                                    'submitted_by': 'seqr-test@gmail.com,test@broadinstitute.org',
                                    'phenopacket_schema_version': '2.0',
                                    'resources': [{
                                        'id': 'geno',
                                        'iriPrefix': 'http://purl.obolibrary.org/obo/GENO_',
                                        'name': 'GENO ontology',
                                        'namespacePrefix': 'GENO',
                                        'url': 'http://purl.obolibrary.org/obo/geno.owl',
                                        'version': '2026-02-02',
                                    }],
                                },
                            },
                            'relatives': [],
                            'meta_data': {'phenopacket_schema_version': '2.0', 'resources': []},
                        }, {
                            'id': 'F_4',
                            'pedigree': {
                                'persons': [{
                                    'affected_status': 'AFFECTED',
                                    'family_id': 'F_4',
                                    'individual_id': 'I_4_0',
                                    'maternal_id': '0',
                                    'paternal_id': '0',
                                    'sex': 'MALE',
                                }],
                            },
                            'proband': {
                                'id': 'I_4_0',
                                'interpretations': [{
                                    'diagnosis': {
                                        'genomic_interpretations': [{
                                            'call': {
                                                'variation_descriptor': {
                                                    'allelic_state': {'id': 'GENO:0000135', 'label': 'heterozygous'},
                                                },
                                            },
                                            'interpretation_status': 'UNKNOWN_STATUS',
                                            'subject_or_biosample_id': 'I_4_0',
                                        }],
                                    },
                                    'id': 'I_4_0',
                                    'progress_status': 'UNKNOWN_PROGRESS',
                                }],
                                'phenotypic_features': [],
                                'subject': {
                                    'id': 'I_4_0',
                                    'sex': 'MALE',
                                },
                                'meta_data': {
                                    'submitted_by': 'seqr-test@gmail.com,test@broadinstitute.org',
                                    'phenopacket_schema_version': '2.0',
                                    'resources': [{
                                        'id': 'geno',
                                        'iriPrefix': 'http://purl.obolibrary.org/obo/GENO_',
                                        'name': 'GENO ontology',
                                        'namespacePrefix': 'GENO',
                                        'url': 'http://purl.obolibrary.org/obo/geno.owl',
                                        'version': '2026-02-02',
                                    }],
                                },
                            },
                            'relatives': [],
                            'meta_data': {'phenopacket_schema_version': '2.0', 'resources': []},
                        }],
                    },
                ],
            }
        }
        only_37_response = {
            'beaconHandovers': [
                {
                    'handoverType': {
                        'id': 'TestVLM',
                        'label': 'TestVLM browser',
                    },
                    'url': 'https://test-seqr.org/variant_lookup?genomeVersion=37&variantId=7-143270172-A-G',
                    'email': None,
                }
            ],
            'meta': {
                'apiVersion': 'v1.0',
                'beaconId': 'com.gnx.beacon.v2',
                'returnedSchemas': [
                    {
                        'entityType': 'Family',
                        'schema': 'phenopacket-2.0',
                    }
                ]
            },
            'responseSummary': {
                'exists': True,
                'total': 1,
            },
            'response': {
                'resultSets': [
                    {
                        'exists': True,
                        'id': 'TestVLM',
                        'setType': 'Family',
                        'resultsCount': 1,
                        'results': [{
                            'id': 'F_0',
                            'pedigree': {
                                 'persons': [{
                                     'affected_status': 'AFFECTED',
                                     'family_id': 'F_0',
                                     'individual_id': 'I_0_0',
                                     'maternal_id': '0',
                                     'paternal_id': '0',
                                     'sex': 'OTHER_SEX',
                                 }],
                            },
                            'proband': {
                                'id': 'I_0_0',
                                'interpretations': [{
                                    'diagnosis': {
                                        'disease': {'id': 'OMIM:615123', 'label': None},
                                        'genomic_interpretations': [{
                                            'call': {
                                                'variation_descriptor': {
                                                    'allelic_state': {'id': 'GENO:0000136', 'label': 'homozygous'},
                                                },
                                            },
                                            'interpretation_status': 'UNKNOWN_STATUS',
                                            'subject_or_biosample_id': 'I_0_0',
                                        }],
                                    },
                                    'id': 'I_0_0',
                                    'progress_status': 'UNKNOWN_PROGRESS',
                                }],
                                'phenotypic_features': [
                                    {'id': 'HP:0002011', 'label': 'Morphological central nervous system abnormality'},
                                    {'id': 'HP:0011675', 'label': 'Arrhythmia'},
                                ],
                                'subject': {
                                    'id': 'I_0_0',
                                    'sex': 'OTHER_SEX',
                                },
                                'meta_data': {
                                    'submitted_by': 'test@broadinstitute.org,vlm@broadinstitute.org',
                                    'phenopacket_schema_version': '2.0',
                                    'resources': [{
                                        'id': 'geno',
                                        'iriPrefix': 'http://purl.obolibrary.org/obo/GENO_',
                                        'name': 'GENO ontology',
                                        'namespacePrefix': 'GENO',
                                        'url': 'http://purl.obolibrary.org/obo/geno.owl',
                                        'version': '2026-02-02',
                                    }, {
                                        'id': 'hp',
                                        'iriPrefix': 'http://purl.obolibrary.org/obo/HP_',
                                        'name': 'Human Phenotype Ontology',
                                        'namespacePrefix': 'HP',
                                        'url': 'http://purl.obolibrary.org/obo/hp.owl',
                                        'version': datetime.now().strftime('%Y-%m-%d'),
                                    }, {
                                        'id': 'omim',
                                        'iriPrefix': 'https://www.omim.org/entry/',
                                        'name': 'Online Mendelian Inheritance in Man',
                                        'namespacePrefix': 'OMIM',
                                        'url': 'https://www.omim.org',
                                        'version': datetime.now().strftime('%Y-%m-%d'),
                                    }],
                                },
                            },
                            'relatives': [],
                            'meta_data': {'phenopacket_schema_version': '2.0', 'resources': []},
                        }],
                    },
                ],
            }
        }
        empty_response = {
            'beaconHandovers': [
                {
                    'handoverType': {
                        'id': 'TestVLM',
                        'label': 'TestVLM browser',
                    },
                    'url': 'https://test-seqr.org/variant_lookup?genomeVersion=38&variantId=7-143270172-A-G',
                    'email': None,
                }
            ],
            'meta': {
                'apiVersion': 'v1.0',
                'beaconId': 'com.gnx.beacon.v2',
                'returnedSchemas': [
                    {
                        'entityType': 'Family',
                        'schema': 'phenopacket-2.0',
                    }
                ]
            },
            'responseSummary': {
                'exists': False,
                'total': 0,
            },
            'response': {
                'resultSets': [
                    {
                        'exists': False,
                        'id': 'TestVLM',
                        'results': [],
                        'resultsCount': 0,
                        'setType': 'Family'
                    },
                ],
            }
        }
        self.maxDiff = None # TODO
        await self._test_match_endpoint('match_details', mocked_responses, response, only_37_response, empty_response)

    async def _test_match_endpoint(self, path, mocked_responses, response, only_37_response, empty_response):

        mocked_responses.post(
            'https://vlm-auth.us.auth0.com/oauth/token', payload={'access_token': 'test_token'}, repeat=True,  # nosec
        )
        mocked_responses.get(
            f'https://vlm-auth.us.auth0.com/api/v2/clients/{REQUESTER_CLIENT_ID}',
            payload={'tenant': 'vlm-auth', 'name': 'Test Node'},
            repeat=True,
        )
        jwt_body = {'iss': 'https://vlm-auth.us.auth0.com/', 'azp': REQUESTER_CLIENT_ID}
        headers = {'Authorization': f'Bearer {jwt.encode(jwt_body, "")}'}

        async with self.client.request('GET', f'/vlm/{path}?assemblyId=GRCh38&referenceName=1&start=38724419&referenceBases=T&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, response)
        mocked_responses.assert_called_with(
            'https://vlm-auth.us.auth0.com/oauth/token',
            method='POST',
            json={'client_id': 'unknown_client_id', 'client_secret': 'unknown_client_secret', 'audience': 'https://vlm-auth.us.auth0.com/api/v2/', 'grant_type': 'client_credentials'},  # nosec
        )
        mocked_responses.assert_called_with(
            f'https://vlm-auth.us.auth0.com/api/v2/clients/{REQUESTER_CLIENT_ID}',
            headers={'Authorization': 'Bearer test_token'},
        )
        self.assertIn(
            'Received match request from Test Node: assemblyId=GRCh38&referenceName=1&start=38724419&referenceBases=T&alternateBases=G',
            self._caplog.messages,
        )

        async with self.client.request('GET', f'/vlm/{path}?assemblyId=hg19&referenceName=chr7&start=143270172&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, only_37_response)

        async with self.client.request('GET', f'/vlm/{path}?assemblyId=GRCh38&referenceName=chr7&start=143573079&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, only_37_response)

        async with self.client.request('GET', f'/vlm/{path}?assemblyId=hg38&referenceName=chr7&start=143270172&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 200)
            resp_json = await resp.json()
        self.assertDictEqual(resp_json, empty_response)

    @aioresponses(passthrough=['http://127.0.0.1'])
    async def test_match_error(self, mocked_responses):
        await self._test_match_endpoint_error('match', mocked_responses)

    @aioresponses(passthrough=['http://127.0.0.1'])
    async def test_match_details_error(self, mocked_responses):
        await self._test_match_endpoint_error('match_details', mocked_responses)

    async def _test_match_endpoint_error(self, path, mocked_responses):

        mocked_responses.get(
            f'https://vlm-auth.us.auth0.com/api/v2/clients/{REQUESTER_CLIENT_ID}', status=404,
        )

        async with self.client.request('GET', f'/vlm/{path}') as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid authorization header')

        headers = {'Authorization': 'token'}
        async with self.client.request('GET', f'/vlm/{path}', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid authorization header')

        headers['Authorization'] =  'JWT token'
        async with self.client.request('GET', f'/vlm/{path}', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid token scheme')

        headers['Authorization'] = 'Bearer token'
        async with self.client.request('GET', f'/vlm/{path}', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid token: Not enough segments')

        jwt_body = {'iss': 'invalid_issuer'}
        headers['Authorization'] = f'Bearer {jwt.encode(jwt_body, "")}'
        async with self.client.request('GET', f'/vlm/{path}', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid token: Token is missing the "azp" claim')

        jwt_body['azp'] = REQUESTER_CLIENT_ID
        headers['Authorization'] = f'Bearer {jwt.encode(jwt_body, "")}'
        async with self.client.request('GET', f'/vlm/{path}', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid token: Invalid issuer')

        mocked_responses.post('https://vlm-auth.us.auth0.com/oauth/token', status=400, payload={'error': 'invalid_request'})
        jwt_body['iss'] = 'https://vlm-auth.us.auth0.com/'
        headers['Authorization'] = f'Bearer {jwt.encode(jwt_body, "")}'
        async with self.client.request('GET', f'/vlm/{path}', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Credential Check Error')
        self.assertEqual(self._caplog.messages[-3], "Credential Check Error: 400 - {'error': 'invalid_request'}")

        mocked_responses.post('https://vlm-auth.us.auth0.com/oauth/token', payload={'access_token': 'test_token'}, repeat=True)  # nosec
        async with self.client.request('GET', f'/vlm/{path}', headers=headers) as resp:
            self.assertEqual(resp.status, 403)
            self.assertEqual(resp.reason, 'Invalid Client ID abc123')
        self.assertEqual(self._caplog.messages[-3], "Invalid Client ID abc123: 404 - Not Found")

        mocked_responses.get(
            f'https://vlm-auth.us.auth0.com/api/v2/clients/{REQUESTER_CLIENT_ID}',
            payload={'tenant': 'vlm-auth'},
            repeat=True,
        )
        async with self.client.request('GET', f'/vlm/{path}', headers=headers) as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(
                resp.reason,
                'Missing required parameters: assemblyId, referenceName, start, referenceBases, alternateBases',
            )

        async with self.client.request('GET', f'/vlm/{path}?assemblyId=38&referenceName=chr7&start=143270172&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid assemblyId: 38')

        async with self.client.request('GET', f'/vlm/{path}?assemblyId=hg38&referenceName=27&start=143270172&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid referenceName: 27')

        async with self.client.request('GET', f'/vlm/{path}?assemblyId=hg38&referenceName=7&start=1x43270172&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid start: 1x43270172')

        async with self.client.request('GET', f'/vlm/{path}?assemblyId=hg38&referenceName=7&start=999999999&referenceBases=A&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid start: 999999999')

        async with self.client.request('GET', f'/vlm/{path}?assemblyId=hg38&referenceName=7&start=143270172&referenceBases=ATC&alternateBases=G', headers=headers) as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid referenceBases: ATC')

        async with self.client.request('GET', f'/vlm/{path}?assemblyId=hg38&referenceName=7&start=143270172&referenceBases=A&alternateBases=GAG', headers=headers) as resp:
            self.assertEqual(resp.status, 400)
            self.assertEqual(resp.reason,'Invalid alternateBases: GAG')