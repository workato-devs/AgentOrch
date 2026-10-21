# Recipe 64112882 Raw Recipe

Order source: benchmark input folder order.
The complete raw recipe JSON is embedded in this file.

CSV metadata:

```json
{
  "category": "standalone",
  "created_at": "2023-08-18 07:17:14.266535+00:00",
  "flow_id": "28566537",
  "updated_at": "2023-08-18 07:17:14.266535+00:00",
  "version_no": "1"
}
```

Raw recipe summary:

```json
{
  "actions": [
    {
      "as": "1bd64b3a",
      "name": "get_records",
      "number": 3,
      "provider": "workato_db_table"
    },
    {
      "as": "c3fb8151",
      "name": "return_response",
      "number": 6,
      "provider": "workato_api_platform"
    },
    {
      "as": "ac43c95c",
      "name": "return_response",
      "number": 8,
      "provider": "workato_api_platform"
    }
  ],
  "trigger": {
    "as": "8bd2b676",
    "name": "receive_request",
    "number": 1,
    "provider": "workato_api_platform"
  }
}
```

Complete raw recipe:

```json
{
  "as": "8bd2b676",
  "block": [
    {
      "block": [
        {
          "as": "1bd64b3a",
          "dynamicPickListSelection": {
            "filters.0.field_id": "Churn Oppty ID",
            "table_id": "[QTC] Open Invoices"
          },
          "extended_input_schema": [
            {
              "control_type": "text",
              "default": "integer",
              "extends_schema": false,
              "label": "$internal_value_028d15b9-ac99-401c-b25f-c44a1ce7c5db",
              "name": "028d15b9-ac99-401c-b25f-c44a1ce7c5db",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "string",
              "extends_schema": false,
              "label": "$internal_value_3faa69d3-6a7e-4d7c-aced-a1ba0b0442fe",
              "name": "3faa69d3-6a7e-4d7c-aced-a1ba0b0442fe",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "string",
              "extends_schema": false,
              "label": "$internal_value_1e5fd270-2211-4c58-8dfa-95b6ee3b7b9c",
              "name": "1e5fd270-2211-4c58-8dfa-95b6ee3b7b9c",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "string",
              "extends_schema": false,
              "label": "$internal_value_665410c4-9b6f-46fe-93cd-8253dbcd3308",
              "name": "665410c4-9b6f-46fe-93cd-8253dbcd3308",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "date",
              "extends_schema": false,
              "label": "$internal_value_7d01c55a-176b-47dc-ad8c-b06899074107",
              "name": "7d01c55a-176b-47dc-ad8c-b06899074107",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "date",
              "extends_schema": false,
              "label": "$internal_value_f9a16194-15bd-4f03-a294-678f8c953df9",
              "name": "f9a16194-15bd-4f03-a294-678f8c953df9",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "string",
              "extends_schema": false,
              "label": "$internal_value_6044c826-e8b1-4524-b299-5d5d9c63a5a1",
              "name": "6044c826-e8b1-4524-b299-5d5d9c63a5a1",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "number",
              "extends_schema": false,
              "label": "$internal_value_eef0c324-141b-46ad-a5aa-dd09b57e2ecd",
              "name": "eef0c324-141b-46ad-a5aa-dd09b57e2ecd",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "number",
              "extends_schema": false,
              "label": "$internal_value_634d81b9-6dfe-4fc8-a02c-78c49ca13b0f",
              "name": "634d81b9-6dfe-4fc8-a02c-78c49ca13b0f",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "number",
              "extends_schema": false,
              "label": "$internal_value_6b5097f5-ac84-4c8d-8c21-654da728eafb",
              "name": "6b5097f5-ac84-4c8d-8c21-654da728eafb",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "string",
              "extends_schema": false,
              "label": "$internal_value_144af657-99db-483a-9ed8-a1324849d522",
              "name": "144af657-99db-483a-9ed8-a1324849d522",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "string",
              "extends_schema": false,
              "label": "$internal_value_595fbc67-aef7-407b-813f-dd5b723d88cd",
              "name": "595fbc67-aef7-407b-813f-dd5b723d88cd",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "number",
              "extends_schema": false,
              "label": "$internal_value_0be8c260-33ba-4646-862c-ec74b765350a",
              "name": "0be8c260-33ba-4646-862c-ec74b765350a",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "string",
              "extends_schema": false,
              "label": "$internal_value_ad862ef9-2e1e-462e-ab20-c149ce29997f",
              "name": "ad862ef9-2e1e-462e-ab20-c149ce29997f",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "id",
              "extends_schema": false,
              "label": "$internal_value_11fbe9a6-a16d-4d7e-86ea-afe42ec03005",
              "name": "11fbe9a6-a16d-4d7e-86ea-afe42ec03005",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "date_time",
              "extends_schema": false,
              "label": "$internal_value_a5612739-5401-4ae7-bd07-782c1a6fb2d1",
              "name": "a5612739-5401-4ae7-bd07-782c1a6fb2d1",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "default": "date_time",
              "extends_schema": false,
              "label": "$internal_value_61aae604-a95e-4519-9091-bb0bf754a67f",
              "name": "61aae604-a95e-4519-9091-bb0bf754a67f",
              "ngIf": "false",
              "optional": true,
              "type": "string"
            }
          ],
          "extended_output_schema": [
            {
              "extends_schema": false,
              "label": "Records",
              "name": "records",
              "of": "object",
              "properties": [
                {
                  "control_type": "text",
                  "extends_schema": false,
                  "label": "Record ID",
                  "name": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
                  "type": "string"
                },
                {
                  "control_type": "number",
                  "extends_schema": false,
                  "label": "Past Due",
                  "name": "028d15b9_ac99_401c_b25f_c44a1ce7c5db",
                  "parse_output": "integer_conversion",
                  "type": "integer"
                },
                {
                  "control_type": "text",
                  "extends_schema": false,
                  "label": "NetSuite Customer ID",
                  "name": "3faa69d3_6a7e_4d7c_aced_a1ba0b0442fe",
                  "type": "string"
                },
                {
                  "control_type": "text",
                  "extends_schema": false,
                  "label": "NetSuite Invoice ID",
                  "name": "1e5fd270_2211_4c58_8dfa_95b6ee3b7b9c",
                  "type": "string"
                },
                {
                  "control_type": "text",
                  "extends_schema": false,
                  "label": "NetSuite Invoice No.",
                  "name": "665410c4_9b6f_46fe_93cd_8253dbcd3308",
                  "type": "string"
                },
                {
                  "control_type": "date",
                  "extends_schema": false,
                  "label": "Invoice Date",
                  "name": "7d01c55a_176b_47dc_ad8c_b06899074107",
                  "parse_output": "date_conversion",
                  "render_input": "date_conversion",
                  "type": "date"
                },
                {
                  "control_type": "date",
                  "extends_schema": false,
                  "label": "Due Date",
                  "name": "f9a16194_15bd_4f03_a294_678f8c953df9",
                  "parse_output": "date_conversion",
                  "render_input": "date_conversion",
                  "type": "date"
                },
                {
                  "control_type": "text",
                  "extends_schema": false,
                  "label": "Payment Terms",
                  "name": "6044c826_e8b1_4524_b299_5d5d9c63a5a1",
                  "type": "string"
                },
                {
                  "control_type": "number",
                  "extends_schema": false,
                  "label": "Subtotal",
                  "name": "eef0c324_141b_46ad_a5aa_dd09b57e2ecd",
                  "parse_output": "float_conversion",
                  "type": "number"
                },
                {
                  "control_type": "number",
                  "extends_schema": false,
                  "label": "Amount",
                  "name": "634d81b9_6dfe_4fc8_a02c_78c49ca13b0f",
                  "parse_output": "float_conversion",
                  "type": "number"
                },
                {
                  "control_type": "number",
                  "extends_schema": false,
                  "label": "Balance",
                  "name": "6b5097f5_ac84_4c8d_8c21_654da728eafb",
                  "parse_output": "float_conversion",
                  "type": "number"
                },
                {
                  "control_type": "text",
                  "extends_schema": false,
                  "label": "Salesforce Invoice ID",
                  "name": "144af657_99db_483a_9ed8_a1324849d522",
                  "type": "string"
                },
                {
                  "control_type": "text",
                  "extends_schema": false,
                  "label": "Salesforce Account ID",
                  "name": "595fbc67_aef7_407b_813f_dd5b723d88cd",
                  "type": "string"
                },
                {
                  "control_type": "number",
                  "extends_schema": false,
                  "label": "Current ARR",
                  "name": "0be8c260_33ba_4646_862c_ec74b765350a",
                  "parse_output": "float_conversion",
                  "type": "number"
                },
                {
                  "control_type": "text",
                  "extends_schema": false,
                  "label": "Churn Oppty ID",
                  "name": "ad862ef9_2e1e_462e_ab20_c149ce29997f",
                  "type": "string"
                },
                {
                  "control_type": "date_time",
                  "extends_schema": false,
                  "label": "Created at",
                  "name": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
                  "parse_output": "date_time_conversion",
                  "render_input": "date_time_conversion",
                  "type": "date_time"
                },
                {
                  "control_type": "date_time",
                  "extends_schema": false,
                  "label": "Updated at",
                  "name": "61aae604_a95e_4519_9091_bb0bf754a67f",
                  "parse_output": "date_time_conversion",
                  "render_input": "date_time_conversion",
                  "type": "date_time"
                }
              ],
              "type": "array"
            },
            {
              "control_type": "text",
              "extends_schema": false,
              "label": "Next Page Token",
              "name": "continuation_token",
              "type": "string"
            }
          ],
          "input": {
            "028d15b9-ac99-401c-b25f-c44a1ce7c5db": "integer",
            "0be8c260-33ba-4646-862c-ec74b765350a": "number",
            "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id",
            "144af657-99db-483a-9ed8-a1324849d522": "string",
            "1e5fd270-2211-4c58-8dfa-95b6ee3b7b9c": "string",
            "3faa69d3-6a7e-4d7c-aced-a1ba0b0442fe": "string",
            "595fbc67-aef7-407b-813f-dd5b723d88cd": "string",
            "6044c826-e8b1-4524-b299-5d5d9c63a5a1": "string",
            "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time",
            "634d81b9-6dfe-4fc8-a02c-78c49ca13b0f": "number",
            "665410c4-9b6f-46fe-93cd-8253dbcd3308": "string",
            "6b5097f5-ac84-4c8d-8c21-654da728eafb": "number",
            "7d01c55a-176b-47dc-ad8c-b06899074107": "date",
            "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time",
            "ad862ef9-2e1e-462e-ab20-c149ce29997f": "string",
            "eef0c324-141b-46ad-a5aa-dd09b57e2ecd": "number",
            "f9a16194-15bd-4f03-a294-678f8c953df9": "date",
            "filters": [
              {
                "field_id": "ad862ef9-2e1e-462e-ab20-c149ce29997f",
                "op_default": "eq",
                "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"8bd2b676\",\"path\":[\"request\", \"oppty_id\"]}')}"
              }
            ],
            "limit": "200",
            "order_direction": "asc",
            "table_id": "1670"
          },
          "keyword": "action",
          "name": "get_records",
          "number": 3,
          "provider": "workato_db_table",
          "skip": false,
          "toggleCfg": {},
          "uuid": "bd6f5e39-ee36-455a-822f-cb3bdd856dc5"
        },
        {
          "block": [
            {
              "comment": "Amount of invoices found hits table storage limit, please consider increasing search size",
              "dynamicPickListSelection": {},
              "extended_input_schema": [],
              "extended_output_schema": [],
              "input": {
                "stop_reason": "Amount of invoices found hits table storage limit, please consider increasing search size",
                "stop_with_error": "true"
              },
              "keyword": "stop",
              "number": 5,
              "skip": false,
              "toggleCfg": {},
              "uuid": "2ed2d100-8a84-4edd-b0c6-3d62024be4b2"
            }
          ],
          "dynamicPickListSelection": {},
          "extended_input_schema": [],
          "extended_output_schema": [],
          "input": {
            "conditions": [
              {
                "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1bd64b3a\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}",
                "operand": "equals_to",
                "rhs": "200"
              }
            ],
            "operand": "and",
            "type": "compound"
          },
          "keyword": "if",
          "number": 4,
          "skip": false,
          "toggleCfg": {},
          "uuid": "4a8f0aed-9aaa-48bf-aa81-377a70c56353"
        },
        {
          "as": "c3fb8151",
          "dynamicPickListSelection": {},
          "extended_input_schema": [
            {
              "change_on_blur": true,
              "control_type": "select",
              "extends_schema": true,
              "label": "Response",
              "name": "http_status_code",
              "pick_list": [
                [
                  "Success",
                  "200"
                ],
                [
                  "Failed",
                  "400"
                ]
              ],
              "type": "string"
            },
            {
              "extends_schema": false,
              "label": "Response body",
              "name": "response",
              "properties": [
                {
                  "extends_schema": false,
                  "label": "Invoices",
                  "name": "invoices",
                  "of": "object",
                  "optional": true,
                  "properties": [
                    {
                      "control_type": "text",
                      "extends_schema": false,
                      "label": "Invoice ID",
                      "name": "id",
                      "optional": true,
                      "sticky": true,
                      "type": "string"
                    },
                    {
                      "control_type": "text",
                      "extends_schema": false,
                      "label": "Invoice Number",
                      "name": "number",
                      "optional": true,
                      "sticky": true,
                      "type": "string"
                    }
                  ],
                  "sticky": true,
                  "type": "array"
                }
              ],
              "type": "object"
            }
          ],
          "extended_output_schema": [
            {
              "change_on_blur": true,
              "control_type": "select",
              "extends_schema": true,
              "label": "Response",
              "name": "http_status_code",
              "pick_list": [
                [
                  "Success",
                  "200"
                ],
                [
                  "Failed",
                  "400"
                ]
              ],
              "type": "string"
            },
            {
              "extends_schema": false,
              "label": "Response body",
              "name": "response",
              "properties": [
                {
                  "extends_schema": false,
                  "label": "Invoices",
                  "name": "invoices",
                  "of": "object",
                  "optional": true,
                  "properties": [
                    {
                      "control_type": "text",
                      "extends_schema": false,
                      "label": "Invoice ID",
                      "name": "id",
                      "optional": true,
                      "sticky": true,
                      "type": "string"
                    },
                    {
                      "control_type": "text",
                      "extends_schema": false,
                      "label": "Invoice Number",
                      "name": "number",
                      "optional": true,
                      "sticky": true,
                      "type": "string"
                    }
                  ],
                  "sticky": true,
                  "type": "array"
                }
              ],
              "type": "object"
            }
          ],
          "input": {
            "http_status_code": "200",
            "response": {
              "invoices": {
                "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"1bd64b3a\",\"path\":[\"records\"]}')}",
                "id": "=_('data.workato_db_table.1bd64b3a.records.first.1e5fd270_2211_4c58_8dfa_95b6ee3b7b9c').presence or nil",
                "number": "=_('data.workato_db_table.1bd64b3a.records.first.665410c4_9b6f_46fe_93cd_8253dbcd3308').presence or nil"
              }
            }
          },
          "keyword": "action",
          "name": "return_response",
          "number": 6,
          "provider": "workato_api_platform",
          "skip": false,
          "toggleCfg": {},
          "uuid": "9aff27ca-f30b-40b7-97f2-0932afb78fe4"
        },
        {
          "as": "46b155df",
          "block": [
            {
              "as": "ac43c95c",
              "dynamicPickListSelection": {},
              "extended_input_schema": [
                {
                  "change_on_blur": true,
                  "control_type": "select",
                  "extends_schema": true,
                  "label": "Response",
                  "name": "http_status_code",
                  "pick_list": [
                    [
                      "Success",
                      "200"
                    ],
                    [
                      "Failed",
                      "400"
                    ]
                  ],
                  "type": "string"
                },
                {
                  "extends_schema": false,
                  "label": "Response body",
                  "name": "response",
                  "properties": [
                    {
                      "control_type": "text",
                      "extends_schema": false,
                      "label": "Error",
                      "name": "error",
                      "optional": false,
                      "type": "string"
                    }
                  ],
                  "type": "object"
                }
              ],
              "extended_output_schema": [
                {
                  "change_on_blur": true,
                  "control_type": "select",
                  "extends_schema": true,
                  "label": "Response",
                  "name": "http_status_code",
                  "pick_list": [
                    [
                      "Success",
                      "200"
                    ],
                    [
                      "Failed",
                      "400"
                    ]
                  ],
                  "type": "string"
                },
                {
                  "extends_schema": false,
                  "label": "Response body",
                  "name": "response",
                  "properties": [
                    {
                      "control_type": "text",
                      "extends_schema": false,
                      "label": "Error",
                      "name": "error",
                      "optional": false,
                      "type": "string"
                    }
                  ],
                  "type": "object"
                }
              ],
              "input": {
                "http_status_code": "400",
                "response": {
                  "error": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"46b155df\",\"path\":[\"message\"]}')}"
                }
              },
              "keyword": "action",
              "name": "return_response",
              "number": 8,
              "provider": "workato_api_platform",
              "skip": false,
              "toggleCfg": {},
              "uuid": "b4bde0c1-dafa-49c2-9d56-d38c2f96fa7c"
            }
          ],
          "dynamicPickListSelection": {},
          "extended_input_schema": [],
          "extended_output_schema": [],
          "input": {
            "max_retry_count": "0",
            "retry_interval": "2"
          },
          "keyword": "catch",
          "number": 7,
          "skip": false,
          "toggleCfg": {},
          "uuid": "05626c3c-9703-42ae-af29-140cf266d7e3"
        }
      ],
      "dynamicPickListSelection": {},
      "extended_input_schema": [],
      "extended_output_schema": [],
      "input": {},
      "keyword": "try",
      "number": 2,
      "skip": false,
      "toggleCfg": {},
      "uuid": "32883b25-6881-456d-aa47-b983d0680552"
    }
  ],
  "comment": "Define the request and response parameters for this API endpoint",
  "dynamicPickListSelection": {
    "response.responses.0.http_status_code": "200 - OK",
    "response.responses.1.http_status_code": "400 - Bad Request"
  },
  "extended_input_schema": [],
  "extended_output_schema": [
    {
      "extends_schema": false,
      "label": "Context",
      "name": "context",
      "properties": [
        {
          "control_type": "text",
          "extends_schema": false,
          "label": "Calling IP address",
          "name": "calling_ip",
          "optional": true,
          "type": "string"
        },
        {
          "extends_schema": false,
          "label": "Access profile",
          "name": "access_profile",
          "properties": [
            {
              "control_type": "integer",
              "extends_schema": false,
              "label": "Access profile ID",
              "name": "id",
              "optional": true,
              "parse_output": "integer_conversion",
              "type": "integer"
            },
            {
              "control_type": "text",
              "extends_schema": false,
              "label": "Access profile name",
              "name": "name",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "extends_schema": false,
              "label": "Access profile authentication type",
              "name": "type",
              "optional": true,
              "type": "string"
            }
          ],
          "type": "object"
        },
        {
          "extends_schema": false,
          "label": "API client",
          "name": "client",
          "properties": [
            {
              "control_type": "text",
              "extends_schema": false,
              "label": "API client ID",
              "name": "id",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "extends_schema": false,
              "label": "API client name",
              "name": "name",
              "optional": true,
              "type": "string"
            }
          ],
          "type": "object"
        },
        {
          "extends_schema": false,
          "label": "JWT claims",
          "name": "jwt_payload",
          "properties": [
            {
              "control_type": "integer",
              "extends_schema": false,
              "label": "Issued At",
              "name": "iat",
              "optional": true,
              "parse_output": "date_time_conversion",
              "render_input": "date_time_conversion",
              "type": "date_time"
            },
            {
              "control_type": "integer",
              "extends_schema": false,
              "label": "Not Before",
              "name": "nbf",
              "optional": true,
              "parse_output": "date_time_conversion",
              "render_input": "date_time_conversion",
              "type": "date_time"
            },
            {
              "control_type": "integer",
              "extends_schema": false,
              "label": "Expiration Time",
              "name": "exp",
              "optional": true,
              "parse_output": "date_time_conversion",
              "render_input": "date_time_conversion",
              "type": "date_time"
            },
            {
              "control_type": "text",
              "extends_schema": false,
              "label": "Audience",
              "name": "aud",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "extends_schema": false,
              "label": "JWT ID",
              "name": "jti",
              "optional": true,
              "type": "string"
            },
            {
              "control_type": "text",
              "extends_schema": false,
              "label": "Issuer",
              "name": "iss",
              "optional": true,
              "type": "string"
            }
          ],
          "type": "object"
        }
      ],
      "type": "object"
    },
    {
      "extends_schema": false,
      "label": "Request parameters",
      "name": "request",
      "properties": [
        {
          "control_type": "text",
          "extends_schema": false,
          "hint": "Opportunity ID of the churn oppty",
          "label": "Opportunity ID",
          "name": "oppty_id",
          "optional": false,
          "type": "string"
        }
      ],
      "type": "object"
    }
  ],
  "input": {
    "request": {
      "content_type": "json",
      "schema": "[{\"control_type\":\"text\",\"label\":\"Opportunity ID\",\"name\":\"oppty_id\",\"type\":\"string\",\"optional\":false,\"hint\":\"Opportunity ID of the churn oppty\"}]"
    },
    "response": {
      "content_type": "json",
      "responses": [
        {
          "body_schema": "[{\"name\":\"invoices\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Invoices\",\"optional\":true,\"sticky\":true,\"properties\":[{\"control_type\":\"text\",\"label\":\"Invoice ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":true,\"sticky\":true},{\"control_type\":\"text\",\"label\":\"Invoice Number\",\"name\":\"number\",\"type\":\"string\",\"optional\":true,\"sticky\":true}]}]",
          "http_status_code": "200",
          "name": "Success"
        },
        {
          "body_schema": "[{\"name\":\"error\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Error\"}]",
          "http_status_code": "400",
          "name": "Failed"
        }
      ]
    }
  },
  "keyword": "trigger",
  "name": "receive_request",
  "number": 1,
  "provider": "workato_api_platform",
  "skip": false,
  "toggleCfg": {
    "response.responses.0.http_status_code": true,
    "response.responses.1.http_status_code": true
  },
  "uuid": "af9cab82-426e-49a6-82bb-a973b4edd8cf"
}
```
