from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_127418592


RECIPE_ID = "127418592"
SEED_TYPE = "api_platform_return_response_variant"
TRACK = "workato_api_platform_return_response"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = 'f776f701'
# Public-key distribution endpoint (flow 62549904 v13): the API Platform trigger
# receives GET /<environment> and dereferences ONLY path_params.environment.
# Twelve sequential sibling IF blocks (not elsif, but mutually exclusive: each
# tests the same scalar against a distinct constant; IF #14 has TWO OR'd arms,
# 'preview' OR 'agentic-preview') each declare a hardcoded multi-line
# public_key literal (RSA JWK / PEM / EC JWK) and return it as a terminal
# 200 {key} response. An environment matching no IF executes zero actions and
# returns no API response. All backends are Workato-internal (api_platform +
# workato_variable), so the run is fully mocked per the backend policy.
#
# TWIN NOTE: recipe 126396823 is a structural twin, but the IF order, several
# as-ids, and part of the key material/whitespace differ. Groundtruth is NOT
# shared: every literal below is pinned verbatim from THIS recipe's own
# dataset/input_recipes/127418592/raw_recipe.md and must stay byte-exact (leading spaces and
# newlines inside the key literals are significant).

# Verbatim pin of the trigger's endpoint configuration (path param
# "environment", empty request schema, single 200 response named "public_key"
# with a string "key" body field).
EXPECTED_TRIGGER_INPUT: dict[str, Any] = {
    'request': {
        'content_type': 'json',
        'path_params': '[{"control_type":"text","label":"Environment","type":"string","name":"environment"}]',
        'schema': '[]',
    },
    'response': {
        'content_type': 'json',
        'responses': [
            {
                'body_schema': '[{"control_type":"text","label":"Key","type":"string","name":"key"}]',
                'http_status_code': '200',
                'name': 'public_key',
            },
        ],
    },
}

# Verbatim pin of the 12 environment IF branches in recipe order. Each entry
# pins the IF operand + condition list (datapill lhs strings included) and both
# child actions' as-ids and full inputs (the hardcoded public_key literal, its
# schema string, and the return_response {key: <declare pill>} mapping).
EXPECTED_BRANCHES: list[dict[str, Any]] = [
    # IF #2 (or): environment == 'identity-prod' -> RSA JWK via declare acb05a66 / respond b115ce3b
    {
        'if_number': 2,
        'operand': 'or',
        'conditions': [
            {
                'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"f776f701","path":["path_params", "environment"]}\')}',
                'operand': 'equals_to',
                'rhs': 'identity-prod',
            },
        ],
        'declare': {
            'number': 3,
            'as': 'acb05a66',
            'input': {
                'variables': {
                    'data': {
                        'public_key': '    {\n      "kty": "RSA",\n      "n": "8-ComTvqxnTVhgtEX6Ym_inGP1n8OpaAbw75V51ya2xbyS2-JdrggEmsTmvuj4ngmulNoFlCazKqjG35wER2-TCGPvnahpfgRCLBrBNEkpZs6aMbXOCltP6EOcOlKEEysgWaFddtQ_hOz4sfD8l7LZxs8IbP5A0RDaMrvGAWbmsddZgluybBF0D13SlF-VFQXlrcRH9St_UmFheLRVW6aYvTiaEJOhrZ2TLqcoUbtFAgWPcn7IsmJ3Ef--lLA2Gtzeld4ddGQLtEZvkl-O-muV1M_CtfEkpH8WxHERpAwyyU0ysDquYqiC2zHot69mac0PLnAMMMUBytxHQ-hIZJnRe3XVqgArAJLbeGs7Xndj_WWDITf50ItfWNgUAfDjAgYULQVLwAzcDHwyMsVjaW1Ju8KGYHzOoWNx0SVujaFyjfKAhIVtSK0D65SSbEtAJULIP83sRLnQ5-A897Qjl6TCnen7_MZIn4mspWHd2xwzVCpjmscBW1uhHMz4Ct9IptGBpDaL4f9PKkqhlYcyqN7d1yf4j1n9WLgYdBne1bY_HhSexQp_1EbYe0PdjhSOVNdmSVzdugRsTWP8GuljNWeL6lo-XTdEqzH38n8ioyRe2Z2qMbYgcJuqcdZJ2H36HJeM01PINFuL6wJTce0enj8r8Fr37UUdQrFhI18i7qRkc",\n      "e": "AQAB",\n      "kid": "PueF1L1SSHWxOTJapqOH1PmekMmqIfsJNWUpz1ywddc",\n      "use": "sig",\n      "alg": "RS256"\n    }',
                    },
                    'schema': '[{"name":"public_key","type":"string","optional":true,"label":"Public Key","details":{"real_name":"Public Key"},"control_type":"text","parent":["variables","data"]}]',
                },
            },
        },
        'respond': {
            'number': 4,
            'as': 'b115ce3b',
            'input': {
                'http_status_code': '200',
                'response': {
                    'key': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"acb05a66","path":["public_key"]}\')}',
                },
            },
        },
    },
    # IF #5 (and): environment == 'identity-staging' -> RSA JWK via declare d946790e / respond a15f7475
    {
        'if_number': 5,
        'operand': 'and',
        'conditions': [
            {
                'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"f776f701","path":["path_params", "environment"]}\')}',
                'operand': 'equals_to',
                'rhs': 'identity-staging',
            },
        ],
        'declare': {
            'number': 6,
            'as': 'd946790e',
            'input': {
                'variables': {
                    'data': {
                        'public_key': '{\n      "kty": "RSA",\n      "n": "soK-cEP-DZuWmFDlagcs21h1ZyqFT3sH0NuqKVfRo6idShDbD0znn3DxZSRLX84-hZCLN5P7QRSTGCRYAiZGLUs5v9Z0wCPkWkE_dAcqBYRqUDoAYSsTrmac1OIhjAVD7jbr4A8zqAD7QuW82T8Ro9c9k0P_DC83JIuiSwWqNOImuSrejkmsnsmQ_2YKJ8ZwwcY72OChmQjuDl-IXGXaJtnTmvBJONnBoku7wqjjLNoUtPDJpmV3a1ZQG91wXF0EO3YUgV4k0QYI_dT5Ul-IZqaQNSSCCGh5OEUGWSLYOlj87x8ZtMBdep06Ed-wOZkGm3qx8xzSggpD2BqD3MRfLVYaFmKj3s3-I5ZReVZNaHk5D8mnJz_hj4Px2lbJrKjx-fEBMCuWqFUZtwzumzaRkVPdvRzJvp6MSYx1bQWrcDA2dbcD05GRRXJc3wDC5sQc3u2Wzf4dlgV8yF_eUfSdFhl4Nw9U1H9zXuv0ZWYdQogkJNd_9pFOfLo6PZsR8QPVOQv7KUPW4VTbs6xV1MFw-oC9ZYmIjp7j-3iMiUVQQt4Aa-sMBkX0rycHIs_18EEeAHa4QEck9qxCC4h3NRwhHBgMObV7qXI5Vv1WU8VkS6Rz5wvCA_aX-xQrimEwedqzjLZEmPVsOIfjQ694fsn4j-l3ll2ImbXgkN3YM-2pOOc",\n      "e": "AQAB",\n      "kid": "yrQXyF0OhB0rpiVmYkevXCHsDaKSkfc6DTYaCcr10Fw",\n      "use": "sig",\n      "alg": "RS256"\n}',
                    },
                    'schema': '[{"name":"public_key","type":"string","optional":true,"label":"Public Key","details":{"real_name":"Public Key"},"control_type":"text","parent":["variables","data"]}]',
                },
            },
        },
        'respond': {
            'number': 7,
            'as': 'a15f7475',
            'input': {
                'http_status_code': '200',
                'response': {
                    'key': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"d946790e","path":["public_key"]}\')}',
                },
            },
        },
    },
    # IF #8 (or): environment == 'identity-trial' -> RSA JWK via declare 8903bd81 / respond d0a6a418
    {
        'if_number': 8,
        'operand': 'or',
        'conditions': [
            {
                'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"f776f701","path":["path_params", "environment"]}\')}',
                'operand': 'equals_to',
                'rhs': 'identity-trial',
            },
        ],
        'declare': {
            'number': 9,
            'as': '8903bd81',
            'input': {
                'variables': {
                    'data': {
                        'public_key': '{\n      "kty": "RSA",\n      "n": "sXjUt0IPCf5opZSQe1ScSZeP5TMyEBTi_rfLtochqUsf0gjk4ruz5qzpX4Lt8GzVlFVNn03SGVqzPXLseMe2LuKIpi0806rDTQkgPDCKgkW7_lAfCIJ-DVAUscccLaxITwGOHEadxAvFKduamwCPvXYaXOQFJTy6mfrRvGuGZ2QUbEHdJoB_PXQDafF4CUCW36BMM-7NjarKA-_K3WYag57zMiMctKE7AWLPoLLrfqsLS4JAafxb8bHOfnkGuGnloEXpq7KhGRlniTc8UpVECUHzIboXQYLi4krvydg8Osta668fq1-rT687GRGU6kM07vNmkHt8H8ADl_Uj_OYf0tYo1tOPHUnb_k7KTu-P5WposX5fVZHkc-KkSfJmvNxfF2CtMuaPGWWo2UOdzv-X_70PZlLcw-2soSD3CE1BlXwbrleZuag_2A4pbr80s0QGVI6j84NXgbJEEshM7xUAhqC0rHazaS8KssSPowvCQcQliKIaYxMTvWJfm_tNxqlRddue7Q00ql0fJWaV4GouTDU-beKiZo3gYo-FisPY3bSxeHzBwSlPhl9csgB8b0CgQK3K_v8RbPbUM7gGAYeM6t6kEaLoBwc7F0cLqGs04-acaoZwfnqiWQ27BVrFFS9QFSH1dnjYgroQWCodhcQ1_AI-3NbrWFhCz6rVs1v8B4k",\n      "e": "AQAB",\n      "kid": "_WLH8g7g2BsLoXRq_WDSQLO2fsnuqMt53swPeD77nQE",\n      "use": "sig",\n      "alg": "RS256"\n    }',
                    },
                    'schema': '[{"name":"public_key","type":"string","optional":true,"label":"Public Key","details":{"real_name":"Public Key"},"control_type":"text","parent":["variables","data"]}]',
                },
            },
        },
        'respond': {
            'number': 10,
            'as': 'd0a6a418',
            'input': {
                'http_status_code': '200',
                'response': {
                    'key': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"8903bd81","path":["public_key"]}\')}',
                },
            },
        },
    },
    # IF #11 (or): environment == 'identity-preview' -> RSA JWK via declare 362d926a / respond c3582f3c
    {
        'if_number': 11,
        'operand': 'or',
        'conditions': [
            {
                'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"f776f701","path":["path_params", "environment"]}\')}',
                'operand': 'equals_to',
                'rhs': 'identity-preview',
            },
        ],
        'declare': {
            'number': 12,
            'as': '362d926a',
            'input': {
                'variables': {
                    'data': {
                        'public_key': '{\n      "kty": "RSA",\n      "n": "AoDeyLk0puLnQ-P_Nl4NR8aWevF4SfMu88KVXDE4sMss4FdA8fga2YsJQWG9uQU86m71GEvihnySLvVok6Pk4pQT5kVnLK3bsmH8SqPSwIotXtJbEa-l4FN_QiHbRtB78k3BeOd4qnc7g5EEwAe1y9rDBRjGRjxwOYfKxJlgGIlIXJ-mQGdAv_kD2wWw0brZVVlFHYTi2dGqr-Nbo5aPrWIWYINb_RzBoZG4tBiVJCCUzoZzul4VdNkQHQvNOL4xPD4faKNajDg1EZmBjGBjSpV_32DsgtTDrRUnt-9ag1V2zSFHK5rPHtMSGrIVV1Dd1q8lq3rQDDYdWb-uQSntxTTUUcwTWfoGPgrR3qFgZZzaSoanh48LK9jt7G1OgxevUMN2KutvVVs2eCh0DQFYTxCNiaNBZ04x_Cx-0fkR5ySdsuV3kyUIPoTPlwZl62Hr6yvJXbfMAcSBLlPVtXmyj8meKMWMIELqYDrbafhZjGZcyjQnp-Gnf1nGzXQ3sMJrsGYvCBNybU_uKeLyqKeBs1DWm_IBYqIrvYjF-trMXM47OA8I4tcM9g43YYj7ZJ1e4NqpIzXCU5gqT9EQoFE-6SUKj4ox85XuRDBvYQPLFgFf3yv00AljHGDO_K_E2uPGjRWxd21G0DbzgKSGvqF7nU4r0E5CfavE0hrGFolDxMRX",\n      "e": "AQAB",\n      "kid": "fjHjDj46Aaeedixfje_x5XSfMBHIGdJJwapCVY5Y9kc",\n      "use": "sig",\n      "alg": "RS256"\n}',
                    },
                    'schema': '[{"name":"public_key","type":"string","optional":true,"label":"Public Key","details":{"real_name":"Public Key"},"control_type":"text","parent":["variables","data"]}]',
                },
            },
        },
        'respond': {
            'number': 13,
            'as': 'c3582f3c',
            'input': {
                'http_status_code': '200',
                'response': {
                    'key': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"362d926a","path":["public_key"]}\')}',
                },
            },
        },
    },
    # IF #14 (or): environment == 'preview' OR 'agentic-preview' -> PEM public key via declare d65ca36f / respond b2d74905
    {
        'if_number': 14,
        'operand': 'or',
        'conditions': [
            {
                'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"f776f701","path":["path_params", "environment"]}\')}',
                'operand': 'equals_to',
                'rhs': 'preview',
            },
            {
                'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"f776f701","path":["path_params", "environment"]}\')}',
                'operand': 'equals_to',
                'rhs': 'agentic-preview',
            },
        ],
        'declare': {
            'number': 15,
            'as': 'd65ca36f',
            'input': {
                'variables': {
                    'data': {
                        'public_key': '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwcqXBZw2Xh4CaRQLHzrR\nbXdcbP47IV76uJpDhbTR4017IX3nHikIvl/lHr7Ls/7eWiHwYvdHXmAkDCNBEJav\nBGl/bOkKu6qdfrp0jAIMHK6GedNwGXKcm9gV0vDXXNECSYsREj5bcLSWv9zvm8lC\nuzDjeAuc1ZytHL6qPYLSLAN2yrDOaYWqZl0erYy5hBfFplFiW2Gxn42sOQ3TEoKH\nykhhRoPolsHTii2bpA9ZBdu0zKG0FWo+Ligtc9cyz9a8r3BsNb1cjd1Kshhl5ty4\nlGW2DVyJ5oDxg4LxE2k7ZLJjyMxPzQXq1mVEWgWm6WxF//4sL8aeROEvIZZupAbw\nkwIDAQAB\n-----END PUBLIC KEY-----',
                    },
                    'schema': '[{"name":"public_key","type":"string","optional":true,"label":"Public Key","details":{"real_name":"Public Key"},"control_type":"text","parent":["variables","data"]}]',
                },
            },
        },
        'respond': {
            'number': 16,
            'as': 'b2d74905',
            'input': {
                'http_status_code': '200',
                'response': {
                    'key': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"d65ca36f","path":["public_key"]}\')}',
                },
            },
        },
    },
    # IF #17 (or): environment == 'agentic-prod' -> PEM public key via declare c9689e89 / respond 8ac6307d
    {
        'if_number': 17,
        'operand': 'or',
        'conditions': [
            {
                'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"f776f701","path":["path_params", "environment"]}\')}',
                'operand': 'equals_to',
                'rhs': 'agentic-prod',
            },
        ],
        'declare': {
            'number': 18,
            'as': 'c9689e89',
            'input': {
                'variables': {
                    'data': {
                        'public_key': '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuqxWr1s7FwxXDHMTBaj/\n9IhNpv2TKO4OPkmbUQkhDq+yRAk/mvfHZ2sHcZBP7FVAIzm2cRHY1kGEFqISDgRA\ny2neAIfjKh8jJEBdd8U+bV8+0kdbxdiVDHMcFbcyEqwmwSf0zFogRkIdWFjAHaaD\ncKoYxrZwmwd0pJ55VfIN+LtZjVDqtVOSlPHXKCO4TXbibALaZqNZeaot2CJ+sPNO\nl3S+pTQUNyF2Q5hx2nsCo+MFMLIUyz9B3cyK4KzyRme1WS5jlT9W5Eti/KApvh6m\nmLajgnTyn/G6QY2e+oZ5DTEqZF3t8i8671MYCtlTmbBSa8ZKXbb7+nHnie0aHIQm\nRQIDAQAB\n-----END PUBLIC KEY-----',
                    },
                    'schema': '[{"name":"public_key","type":"string","optional":true,"label":"Public Key","details":{"real_name":"Public Key"},"control_type":"text","parent":["variables","data"]}]',
                },
            },
        },
        'respond': {
            'number': 19,
            'as': '8ac6307d',
            'input': {
                'http_status_code': '200',
                'response': {
                    'key': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"c9689e89","path":["public_key"]}\')}',
                },
            },
        },
    },
    # IF #20 (or): environment == 'agentic-staging' -> PEM public key via declare 3e367e21 / respond 62a96198
    {
        'if_number': 20,
        'operand': 'or',
        'conditions': [
            {
                'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"f776f701","path":["path_params", "environment"]}\')}',
                'operand': 'equals_to',
                'rhs': 'agentic-staging',
            },
        ],
        'declare': {
            'number': 21,
            'as': '3e367e21',
            'input': {
                'variables': {
                    'data': {
                        'public_key': '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwbkRBNJNOvM1qYe8p2in\nmGiJWdm1Ua3t1DQWcpV5DtyFyBJxLUxH8xUj9cSwML7TEcUP583ADkk5mtE/Rk4h\n5aQDIrUjyxNTBPKVQZFfaCKtUnQh8BdTranxLZG9XHhMBy0fFSGWS8bbCXTGfFRI\nsAHahzKdCIp/YQU3T92BkwT411DoMrOd/B3CqT54n2qAzYNdOWr3KRVnYuyL1oPW\nMt6JNSjBgXJV4C7OAMn2cSq0NM0YUJ0zoCFHxeHxu8Bh8FWBvZJmK5gmBmZVfCs/\nn/dKT1aNRBFMx7Y0qOUvLjuyXMvgsLw8hY7bSu2J4YAgaDl1+5o9rufrpNjyPbxa\nnwIDAQAB\n-----END PUBLIC KEY-----',
                    },
                    'schema': '[{"name":"public_key","type":"string","optional":true,"label":"Public Key","details":{"real_name":"Public Key"},"control_type":"text","parent":["variables","data"]}]',
                },
            },
        },
        'respond': {
            'number': 22,
            'as': '62a96198',
            'input': {
                'http_status_code': '200',
                'response': {
                    'key': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"3e367e21","path":["public_key"]}\')}',
                },
            },
        },
    },
    # IF #23 (or): environment == 'agentic-trial' -> PEM public key via declare 83f968a4 / respond 18159162
    {
        'if_number': 23,
        'operand': 'or',
        'conditions': [
            {
                'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"f776f701","path":["path_params", "environment"]}\')}',
                'operand': 'equals_to',
                'rhs': 'agentic-trial',
            },
        ],
        'declare': {
            'number': 24,
            'as': '83f968a4',
            'input': {
                'variables': {
                    'data': {
                        'public_key': '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArTb1oRVtFb/Vt4DCSthT\noqWUUhk9uACyGpYFScPP5mOTLD+C8IUlkIMxfSWF7b3YtSAuDEJUmG7ctVmEhSiR\n53rPa9mB7AduMIehpj3RffCWRsi1caaTNCOQK1QwARfEdA5uYijk6Dg5MZi0AOPx\nSBHkeHIkWuljQSW7zB8PmgQirk3+/XPY71FE712KsvaYqyV6UmriINI5f7BransQ\nNz+p287nAjwsAIgmg9kaKxB1RjhPq5HupjtB8o5rUrjSsNDcjMS5a4g2ZlhMWsqK\nQGjQqRxUEs9/TvX2cWccmKaD/FHrUhwtzXsi6oJin2tljC6FKBUPI2I2gJB07k6u\nmwIDAQAB\n-----END PUBLIC KEY-----',
                    },
                    'schema': '[{"name":"public_key","type":"string","optional":true,"label":"Public Key","details":{"real_name":"Public Key"},"control_type":"text","parent":["variables","data"]}]',
                },
            },
        },
        'respond': {
            'number': 25,
            'as': '18159162',
            'input': {
                'http_status_code': '200',
                'response': {
                    'key': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"83f968a4","path":["public_key"]}\')}',
                },
            },
        },
    },
    # IF #26 (or): environment == 'matrix-preview' -> PEM public key via declare 0691c990 / respond cf971e26
    {
        'if_number': 26,
        'operand': 'or',
        'conditions': [
            {
                'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"f776f701","path":["path_params", "environment"]}\')}',
                'operand': 'equals_to',
                'rhs': 'matrix-preview',
            },
        ],
        'declare': {
            'number': 27,
            'as': '0691c990',
            'input': {
                'variables': {
                    'data': {
                        'public_key': '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1oA5c+WuZeMZ12Y5VSYg\nLCd7xfR15M43lKiIGlPX2DSwj8I94Ln9j4IJa3UztuYlRdhEaRKumVadQShwAZjp\nWElc6YBuCoDBUNcxlsOa1N0d1fCYI/wqBl21Odtlm31ZuQWWvzZoGDRVBe+LQE0L\nT2reitmbwFLV/MFP6nLoxHfNhZYtRKhgGv3R8HPS4EIoMTBevIrY8VuJ/XbL6aFl\nRWr/yWt+D5xEnzUKa+8KnIYrewlKMB6VfMC3ptWwZLJVIIFs0Vaqu+XOyp9HPcut\nYoiRgA2klVaJjj8fMK8k7QwEcnmomnC/IvXEOkYRGAWc3cE8xi+T+z//PUvpeqLp\nMQIDAQAB\n-----END PUBLIC KEY-----',
                    },
                    'schema': '[{"name":"public_key","type":"string","optional":true,"label":"Public Key","details":{"real_name":"Public Key"},"control_type":"text","parent":["variables","data"]}]',
                },
            },
        },
        'respond': {
            'number': 28,
            'as': 'cf971e26',
            'input': {
                'http_status_code': '200',
                'response': {
                    'key': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"0691c990","path":["public_key"]}\')}',
                },
            },
        },
    },
    # IF #29 (or): environment == 'matrix-prod' -> PEM public key via declare 83e1600f / respond 48211044
    {
        'if_number': 29,
        'operand': 'or',
        'conditions': [
            {
                'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"f776f701","path":["path_params", "environment"]}\')}',
                'operand': 'equals_to',
                'rhs': 'matrix-prod',
            },
        ],
        'declare': {
            'number': 30,
            'as': '83e1600f',
            'input': {
                'variables': {
                    'data': {
                        'public_key': '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAkmk92+SjSdTy1HBKZkbD\n6uUaQwhW764QNz06UNxO1PYCXzzPqTvsom4cP/e6qpnd6EaIO33qesUJWa5FAZyX\nflkJfcNckfVRidcV4/hzu4DIr7+CqmOO5hcZoTEF1l9ZrjllNUf6F8yPZ2MWmzFD\norIED53gn3kDRO8Rf7Z//4fnsLFh398Ne4DAEGhJuS1jhM1Ukpzfa0DC2RWdNlCe\nopNWh+BV/sPSUeZISqwiZclOaayv7u6k/cztXkOsVOgU+X8XpHdmYBI+hdyssjHo\nPHdbr+xD3gerUcWOxA+eRhc0ZaL14GDCC37Vvg5RYrI01LtQ2lK6DrGn2YX378GR\ncwIDAQAB\n-----END PUBLIC KEY-----',
                    },
                    'schema': '[{"name":"public_key","type":"string","optional":true,"label":"Public Key","details":{"real_name":"Public Key"},"control_type":"text","parent":["variables","data"]}]',
                },
            },
        },
        'respond': {
            'number': 31,
            'as': '48211044',
            'input': {
                'http_status_code': '200',
                'response': {
                    'key': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"83e1600f","path":["public_key"]}\')}',
                },
            },
        },
    },
    # IF #32 (or): environment == 'matrix-trial' -> PEM public key via declare 86a1a0c7 / respond 7c0cee08
    {
        'if_number': 32,
        'operand': 'or',
        'conditions': [
            {
                'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"f776f701","path":["path_params", "environment"]}\')}',
                'operand': 'equals_to',
                'rhs': 'matrix-trial',
            },
        ],
        'declare': {
            'number': 33,
            'as': '86a1a0c7',
            'input': {
                'variables': {
                    'data': {
                        'public_key': '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnKJdXfFvq/lxj90+ELwM\nctyuwUSC8cMXeV+WXD5Mrg5aDpGs3KUhBzc5Gig/IDRBIDotl2puyUUscamkIkTh\nBf2AvgMrzjFZlAjZDNxqdllcYcIHreCywLQQq4FB+VexgC1HqzT7DYDdJU6zf83a\nsPmvS1JwbIwmImVrXEh+j6fFaX0ToEFu4efqmdVD4ZXeJuzLNj+t3fLVcfF+fA+Y\nuXCierZ7Bz9nb5vW0yxa2GtSMJCmsr+pFKEDkZBFcsqAHz6I9XquiQi3ehCC33/+\nA0U/uqQYore8WjAP3Ttawfur+LEoXljmXs0+yRTBUSzs1ILz0wUQAyDcldbp65CT\n1QIDAQAB\n-----END PUBLIC KEY-----',
                    },
                    'schema': '[{"name":"public_key","type":"string","optional":true,"label":"Public Key","details":{"real_name":"Public Key"},"control_type":"text","parent":["variables","data"]}]',
                },
            },
        },
        'respond': {
            'number': 34,
            'as': '7c0cee08',
            'input': {
                'http_status_code': '200',
                'response': {
                    'key': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"86a1a0c7","path":["public_key"]}\')}',
                },
            },
        },
    },
    # IF #35 (and): environment == 'token-service-preview' -> EC P-256 JWK via declare c46e597a / respond 559e9709
    {
        'if_number': 35,
        'operand': 'and',
        'conditions': [
            {
                'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"f776f701","path":["path_params", "environment"]}\')}',
                'operand': 'equals_to',
                'rhs': 'token-service-preview',
            },
        ],
        'declare': {
            'number': 36,
            'as': 'c46e597a',
            'input': {
                'variables': {
                    'data': {
                        'public_key': '{\n    "alg": "ES256",\n    "crv": "P-256",\n    "kid": "<anon>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee</anon>",\n    "kty": "EC",\n    "use": "sig",\n    "x": "wo1yy5HmLLewRReyual2x9JgJqtzCPT-C8QWqcS796U",\n    "y": "bMSviMInyGTwYbfuKF-29DwWr-piP_ObP8Kq78P7i_k"\n}',
                    },
                    'schema': '[{"name":"public_key","type":"string","optional":true,"label":"Public Key","details":{"real_name":"Public Key"},"control_type":"text","parent":["variables","data"]}]',
                },
            },
        },
        'respond': {
            'number': 37,
            'as': '559e9709',
            'input': {
                'http_status_code': '200',
                'response': {
                    'key': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"c46e597a","path":["public_key"]}\')}',
                },
            },
        },
    },
]

EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_variable", "declare_variable"),
    ("workato_api_platform", "return_response"),
    ("workato_variable", "declare_variable"),
    ("workato_api_platform", "return_response"),
    ("workato_variable", "declare_variable"),
    ("workato_api_platform", "return_response"),
    ("workato_variable", "declare_variable"),
    ("workato_api_platform", "return_response"),
    ("workato_variable", "declare_variable"),
    ("workato_api_platform", "return_response"),
    ("workato_variable", "declare_variable"),
    ("workato_api_platform", "return_response"),
    ("workato_variable", "declare_variable"),
    ("workato_api_platform", "return_response"),
    ("workato_variable", "declare_variable"),
    ("workato_api_platform", "return_response"),
    ("workato_variable", "declare_variable"),
    ("workato_api_platform", "return_response"),
    ("workato_variable", "declare_variable"),
    ("workato_api_platform", "return_response"),
    ("workato_variable", "declare_variable"),
    ("workato_api_platform", "return_response"),
    ("workato_variable", "declare_variable"),
    ("workato_api_platform", "return_response"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = ["workato_api_platform.return_response"]


def validate_127418592(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger as-id changed: {raw.get('as')!r}")
    if "filter" in raw or raw.get("skip"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger gained a filter/skip flag")
    if raw.get("input") != EXPECTED_TRIGGER_INPUT:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger endpoint configuration drifted: {raw.get('input')!r}")
    blocks = raw.get("block") or []
    if len(blocks) != len(EXPECTED_BRANCHES) or not all(isinstance(node, dict) for node in blocks):
        raise RuntimeError(f"recipe {RECIPE_ID} top-level block layout changed")
    summary = []
    for node, exp in zip(blocks, EXPECTED_BRANCHES):
        if node.get("keyword") != "if" or node.get("skip") or node.get("number") != exp["if_number"]:
            raise RuntimeError(f"recipe {RECIPE_ID} step #{exp['if_number']} is no longer an active IF block")
        cond = node.get("input") or {}
        if cond.get("operand") != exp["operand"] or cond.get("conditions") != exp["conditions"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} IF #{exp['if_number']} environment condition drifted: {cond!r}"
            )
        children = [child for child in node.get("block") or [] if isinstance(child, dict)]
        if len(children) != 2 or any(child.get("skip") for child in children):
            raise RuntimeError(f"recipe {RECIPE_ID} IF #{exp['if_number']} branch body changed")
        declare, respond = children
        if (
            (declare.get("keyword"), declare.get("provider"), declare.get("name"))
            != ("action", "workato_variable", "declare_variable")
            or declare.get("number") != exp["declare"]["number"]
            or declare.get("as") != exp["declare"]["as"]
            or declare.get("input") != exp["declare"]["input"]
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} IF #{exp['if_number']} declare_variable drifted "
                f"(public_key literal must stay byte-exact)"
            )
        if (
            (respond.get("keyword"), respond.get("provider"), respond.get("name"))
            != ("action", "workato_api_platform", "return_response")
            or respond.get("number") != exp["respond"]["number"]
            or respond.get("as") != exp["respond"]["as"]
            or respond.get("input") != exp["respond"]["input"]
        ):
            raise RuntimeError(f"recipe {RECIPE_ID} IF #{exp['if_number']} return_response drifted")
        summary.append({
            "if_number": exp["if_number"],
            "operand": exp["operand"],
            "environments": [c.get("rhs") for c in exp["conditions"]],
            "declare_as": exp["declare"]["as"],
            "respond_as": exp["respond"]["as"],
        })
    actions = _collect_actions(raw)
    actual = [(a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": a.get("number"),
                "provider": a.get("provider"),
                "name": a.get("name"),
                "as": a.get("as"),
            }
            for a in actions
        ],
        "branches": summary,
    }


def seed_127418592(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127418592(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    path_params = trigger.get("path_params")
    if (
        not isinstance(path_params, dict)
        or not isinstance(path_params.get("environment"), str)
        or not path_params["environment"]
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must set a non-empty string "
            f"path_params.environment (the raw recipe dereferences it)"
        )
    if not isinstance(data.get("expect"), dict) or not data["expect"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin an explicit expect block "
            f"(branch + exact response groundtruth)"
        )
    seed_in = data.get("seed") if isinstance(data.get("seed"), dict) else {}
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
        "expect": deepcopy(data["expect"]),
    }
    for key, value in seed_in.items():
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_127418592(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127418592(raw)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            # Workato-internal mocks only (api_platform + workato_variable):
            # nothing persists across runs, so there is no backend snapshot and
            # no cleanup obligation.
            "initial_snapshot": {},
            "final_snapshot": {},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_127418592(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
