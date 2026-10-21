# Case Study: Runtime Observation Resolves a Nested Reference

This case study presents one complete benchmark instance without ellipses or
synthetic reconstruction. It compares Global View and ReAct on recipe
`102467097`, variant `00`, using Claude Opus 5 and the simulated connector
backend. Every model-visible prompt, every model action and observation, and
the complete evaluator-only ground truth are reproduced below. Large prompt
sections are placed in collapsible blocks only to keep the rendered document
navigable; collapsing does not remove content.

## Case overview

The task asks an automation agent to verify that a caller is authorized and,
if so, return up to 200 deprecated package versions in chronological order.
Variant `00` contains an enabled authorization record and one qualifying
package-version record. The package reference is represented at runtime as a
nested object:

```json
{
  "display_name": "Bench display_name",
  "record_id": "Bench record_id"
}
```

This representation creates the decisive difference. Global View must emit a
single symbolic workflow before seeing connector results. Its plan maps the
entire nested object to `package_id` and attempts to read `display_name` from
the record's top level. ReAct observes the nested object first and then reads
its `record_id` and `display_name` members correctly.

| Setting | Trace | Side effect | Orchestration | Terminal | Final |
| --- | ---: | ---: | ---: | ---: | ---: |
| Global View | 0.8 | 1.0 | 0.9 | 0.0 | 0.0 |
| ReAct | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

For Global View, the five trace components are
$(1,1,1,0,1)$ for tool selection, tool order, successful execution, required
arguments, and control path. Therefore,
$\mathrm{TraceAcc}=0.2(1+1+1+0+1)=0.8$ and
$\mathrm{OrchAcc}=0.5(0.8)+0.5(1)=0.9$. The task is read-only, so the expected
state is preserved and Side-Effect Accuracy is one. The malformed terminal
response makes Terminal Accuracy and Final Accuracy zero. ReAct receives one
on all five trace components and produces the correct terminal response.

## Artifact provenance

The exact sources and SHA-256 hashes are listed here so the transcription can
be audited against the released artifacts. The two Global prompt hashes stored
in the model run use the evaluator's `stable_hash`, which hashes canonical JSON
text; the table additionally gives the ordinary SHA-256 of the reproduced
prompt block, including its final newline.

| Content | Source relative to `benchmark/` | Verification digest |
| --- | --- | --- |
| Global system input | Runtime render from `input/recipes/102467097/PUBLIC_PACKAGE.json` using `verification/backends/shared/src/task/workflow_plan.py` | run `stable_hash`: `17c231c6a1c33a9ab992fcd62f7a97e37269de94c63536cc5f976a014d325192`; reproduced block SHA-256: `93bc894f35e7faa8769261b2f774278438d799dfdc03b15d0e5860033cc4ad81` |
| Global user input | Same runtime render and source | run `stable_hash`: `9bbfeff5f00665657756b394ce8b6a1a21f7ec7530cbcc82ff29b3172aec1502`; reproduced block SHA-256: `a268617cb2769ce70ce1b5b71d5d99bc5d979cfd4a19abda50777cde4fec9945` |
| ReAct system input | Runtime render from the ReAct artifact's `input` object, `PUBLIC_PACKAGE.json`, and `verification/backends/shared/src/task/prompt.py` | reproduced block SHA-256: `15eeb38142287cad0f24e92aac6267f5ad2c2912285c9e66a1b9b60331b3d31d` |
| ReAct initial user input | `input/recipes/102467097/REACT_variant_00_user.txt` | `f3b1bbea2cebd92fac80740c88552b1ef39dc9bd884dad7b7846db9f7ace8ca0` |
| Global model plan record | `outputs/full_eval/global-react-final-20260814/plans/claude-opus-5/102467097/initial_plan.json` | `f1d6c16b6dd5da1f34e20f2da34d105d7e695a9b29ca09f2a613d8879ccd16a2` |
| Global per-instance artifact | `outputs/full_eval/global-react-final-20260814/claude-opus-5/plan_execute/artifacts/102467097__v00.json` | `b92f4d69975d5f3a93759c71cad1c00877ef102722709712f60eea926fa52840` |
| ReAct per-instance artifact | `outputs/full_eval/api-3models-clean-sim-global-react-20260814/claude-opus-5/react/artifacts/102467097__v00.json` | `7464167c9046e4d83e18b9833d46164aa1a421cc98f88c0ceb0acf38b3ad80a0` |
| Ground truth | `groundtruth/recipes/102467097/variant_00.json` | `69b951f27f936055f3eae91a57f0222fcda37ac183598c7fa57e25a7d665ce4e` |

The complete ReAct `output` object below is taken from the per-instance API
artifact listed in the table. Its `steps` and `trajectory` are structurally
identical to the corresponding record in
`outputs/full_eval/global-react-final-20260814/claude-opus-5/react/trajectories.jsonl`
after canonical JSON key sorting.

The standalone exported Global prompt files predate two small runtime-renderer
changes: the runtime schema explicitly includes an empty `execution_context`,
and its system message names `finish` and `submit_answer` directly. The blocks
below reproduce the prompts that generated the recorded plan, as verified by
the run's stored hashes, rather than silently pairing the plan with the older
exported text. Likewise, any literal `...` token visible inside a prompt is
part of the original protocol examples or tool documentation; no editorial
ellipsis has been inserted into any reproduced block.

## Complete Global View input

### System message

<details>
<summary>Complete Global View system message</summary>

```text
You design complete, executable automation workflows.

Create one complete recipe-level WorkflowPlan covering every behavior in the
task. Infer tool selection, causal order, every branch/loop/exception path,
symbolic dataflow, and every tool argument from the public capability
contracts. Requirements may be in arbitrary presentation order.

Follow every nested tool input schema exactly. Workspace field identifiers are
values to place in the schema's field-id slots; they are not substitutes for
the schema's object keys. Available tools and workspace resources are
candidates, not prescribed workflow steps. Select the necessary subset and
infer filters, limits, ordering, and other arguments from the business
requirements, public schemas, and data dependencies.

Never copy a concrete runtime value, assume a tool result, or invent a private
identifier. Express each argument and condition with typed symbolic values:
literal, input_ref, output_ref, resource_ref, loop_ref, error_ref, or a listed
deterministic expression. A call may bind its result; later output_ref values
refer to that bind name. Include only necessary tools. Do not include finish or
submit_answer calls. Represent a recipe-level result with a `return` control
node. The low-level `workato_genie.workflow_return_result` and
`workato_recipe_function.return_result` catalog entries are authoring-layer
forms of that control and must not be emitted as business tool calls. Return exactly one JSON object and no prose.
```

</details>

### User message

<details>
<summary>Complete Global View user message</summary>

```text
Design the complete symbolic WorkflowPlan for this task.

## Task
The requirements below describe the desired behavior. Do not treat their
presentation order as the execution order; determine the workflow from the
requirements, dependencies, and conditions.

Objective
Provide authorized callers with a bounded, chronologically ordered listing of package versions deprecated after a supplied timestamp.

Requirements
- For an authorized caller, return a 200 Success response containing up to 200 deprecated package versions, ordered from earliest to latest deprecation. Each deprecations item must contain the version ID, version name, associated package ID, associated package name, and deprecation timestamp.
- A package version qualifies only when it is marked deprecated and its deprecation timestamp is strictly later than request.deprecated_since.
- If protected deprecation retrieval or construction of the success response fails, do not retry; return a 400 Failed response whose error is exactly "Unexpected Error".
- Create one deprecations item for every retrieved qualifying package-version record, preserving its version ID, version name, associated package ID, associated package name, and deprecation timestamp.
- The 401 Unauthorized response, 200 Success response, and handled 400 Failed response each terminate processing.
- If no enabled workspace authorization record links the caller's access profile to request.workspace_user_id, return a 401 Unauthorized response with no body; otherwise, provide the protected deprecation-listing response path.

## Public input schema
{
  "properties": {
    "context": {
      "properties": {
        "access_profile": {
          "properties": {
            "id": {
              "title": "Id",
              "type": "string"
            }
          },
          "title": "Access Profile",
          "type": "object"
        }
      },
      "title": "Context",
      "type": "object"
    },
    "execution_context": {
      "properties": {},
      "type": "object"
    },
    "request": {
      "properties": {
        "deprecated_since": {
          "format": "date-time",
          "title": "Deprecated since",
          "type": "string"
        },
        "workspace_user_id": {
          "minLength": 1,
          "title": "Workspace user ID",
          "type": [
            "integer",
            "string"
          ]
        }
      },
      "required": [
        "workspace_user_id"
      ],
      "title": "Request",
      "type": "object"
    }
  },
  "required": [
    "request"
  ],
  "type": "object"
}

## Public output schema
{
  "declared_responses": [
    {
      "body_schema": [
        {
          "label": "Deprecations",
          "name": "deprecations",
          "of": "object",
          "optional": false,
          "properties": [
            {
              "control_type": "text",
              "label": "ID",
              "name": "id",
              "optional": false,
              "type": "string"
            },
            {
              "control_type": "text",
              "label": "Name",
              "name": "name",
              "optional": false,
              "type": "string"
            },
            {
              "control_type": "text",
              "label": "Package ID",
              "name": "package_id",
              "optional": false,
              "type": "string"
            },
            {
              "control_type": "text",
              "label": "Package name",
              "name": "package_name",
              "optional": false,
              "type": "string"
            },
            {
              "control_type": "date_time",
              "label": "Deprecated at",
              "name": "deprecated_at",
              "optional": false,
              "parse_output": "date_time_conversion",
              "render_input": "date_time_conversion",
              "type": "date_time"
            }
          ],
          "type": "array"
        }
      ],
      "content_type": "json",
      "delivery": "explicit_tool_call",
      "http_status_code": "200",
      "name": "Success"
    },
    {
      "body_schema": [
        {
          "control_type": "text",
          "label": "Error",
          "name": "error",
          "optional": false,
          "type": "string"
        }
      ],
      "content_type": "json",
      "delivery": "explicit_tool_call",
      "http_status_code": "400",
      "name": "Failed"
    },
    {
      "body_schema": [],
      "content_type": "json",
      "delivery": "explicit_tool_call",
      "http_status_code": "401",
      "name": "Unauthorized"
    }
  ],
  "scalar_encoding_semantics": {
    "workato_checkbox_control": "Boolean-declared checkbox controls accept JSON booleans or the authoring strings true and false.",
    "workato_numeric_control": "Integer and number response controls accept mathematically compatible numeric expressions; numeric strings are coerced by controls that declare numeric output conversion.",
    "workato_text_control": "String-declared text controls accept string, integer, number, or boolean scalar expressions and apply Workato's text coercion."
  },
  "schema_version": "public-output-interface"
}

## Public workspace context
{
  "communication_templates": [],
  "execution_context_schema": {
    "properties": {},
    "type": "object"
  },
  "workspace_resources": [
    {
      "fields": [
        {
          "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "label": "Record ID",
          "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "type": "string"
        },
        {
          "argument_field_id": "50dd1528_57bf_4ed5_a678_03e9c709b140",
          "field_id": "50dd1528_57bf_4ed5_a678_03e9c709b140",
          "label": "api_client_id",
          "output_field_id": "50dd1528_57bf_4ed5_a678_03e9c709b140",
          "type": "string"
        },
        {
          "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "label": "Updated at",
          "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "type": "date_time"
        },
        {
          "argument_field_id": "8016f9ed_ec17_40fd_a45b_4511efa3daf9",
          "field_id": "8016f9ed_ec17_40fd_a45b_4511efa3daf9",
          "label": "name",
          "output_field_id": "8016f9ed_ec17_40fd_a45b_4511efa3daf9",
          "type": "string"
        },
        {
          "argument_field_id": "856d93af_9a6e_4091_af46_051211c25a75",
          "field_id": "856d93af_9a6e_4091_af46_051211c25a75",
          "label": "access_profile_id",
          "output_field_id": "856d93af_9a6e_4091_af46_051211c25a75",
          "type": "string"
        },
        {
          "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "label": "Created at",
          "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "type": "date_time"
        },
        {
          "argument_field_id": "c3f5a247_f6d7_498f_a5fa_6b469edb74d9",
          "field_id": "c3f5a247_f6d7_498f_a5fa_6b469edb74d9",
          "label": "enabled",
          "output_field_id": "c3f5a247_f6d7_498f_a5fa_6b469edb74d9",
          "type": "boolean"
        },
        {
          "argument_field_id": "continuation_token",
          "field_id": "continuation_token",
          "label": "Next Page Token",
          "output_field_id": "continuation_token",
          "type": "string"
        },
        {
          "argument_field_id": "faf6d561_0a7e_42d1_8f8c_ec11f9f86c31",
          "field_id": "faf6d561_0a7e_42d1_8f8c_ec11f9f86c31",
          "label": "workspace_id",
          "output_field_id": "faf6d561_0a7e_42d1_8f8c_ec11f9f86c31",
          "type": "string"
        }
      ],
      "name": "OpenAI Proxy Workspaces",
      "public_id": "11026",
      "resource_kind": "data_table",
      "resource_ref": "resource_5638644dcaf2"
    },
    {
      "fields": [
        {
          "argument_field_id": "01124e6e_cc78_4ef8_be38_cc6d23617b6b",
          "field_id": "01124e6e_cc78_4ef8_be38_cc6d23617b6b",
          "label": "Cancellation Processed",
          "output_field_id": "01124e6e_cc78_4ef8_be38_cc6d23617b6b",
          "type": "boolean"
        },
        {
          "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "label": "Record ID",
          "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "type": "string"
        },
        {
          "argument_field_id": "167199db_4b09_4eee_856d_de4da13762a4",
          "field_id": "167199db_4b09_4eee_856d_de4da13762a4",
          "label": "Date of 4th Event",
          "output_field_id": "167199db_4b09_4eee_856d_de4da13762a4",
          "type": "date"
        },
        {
          "argument_field_id": "167f2a3b_ae11_46eb_85c2_8b9eb0fdcd58",
          "field_id": "167f2a3b_ae11_46eb_85c2_8b9eb0fdcd58",
          "label": "Last Name",
          "output_field_id": "167f2a3b_ae11_46eb_85c2_8b9eb0fdcd58",
          "type": "string"
        },
        {
          "argument_field_id": "18c0d693_fada_4736_8c14_ff92031785cb",
          "field_id": "18c0d693_fada_4736_8c14_ff92031785cb",
          "label": "Hours Event 5",
          "output_field_id": "18c0d693_fada_4736_8c14_ff92031785cb",
          "type": "number"
        },
        {
          "argument_field_id": "1cfaf695_ab64_48c9_87fa_17e809c68169",
          "field_id": "1cfaf695_ab64_48c9_87fa_17e809c68169",
          "label": "First Name",
          "output_field_id": "1cfaf695_ab64_48c9_87fa_17e809c68169",
          "type": "string"
        },
        {
          "argument_field_id": "20e3ee39_1689_48cb_8bc0_8239c4d124d0",
          "field_id": "20e3ee39_1689_48cb_8bc0_8239c4d124d0",
          "label": "Activity Country Record ID",
          "output_field_id": "20e3ee39_1689_48cb_8bc0_8239c4d124d0",
          "type": "string"
        },
        {
          "argument_field_id": "25953fff_bdef_42bd_8e66_d205465e97a1",
          "field_id": "25953fff_bdef_42bd_8e66_d205465e97a1",
          "label": "Approved by",
          "output_field_id": "25953fff_bdef_42bd_8e66_d205465e97a1",
          "type": "string"
        },
        {
          "argument_field_id": "2f960f40_2f77_4619_bd23_dadae6bd3ec2",
          "field_id": "2f960f40_2f77_4619_bd23_dadae6bd3ec2",
          "label": "Numbers Helped",
          "output_field_id": "2f960f40_2f77_4619_bd23_dadae6bd3ec2",
          "type": "integer"
        },
        {
          "argument_field_id": "3dc4d7e4_9803_4033_b92e_b437afeb72c2",
          "field_id": "3dc4d7e4_9803_4033_b92e_b437afeb72c2",
          "label": "Date of 7th Event",
          "output_field_id": "3dc4d7e4_9803_4033_b92e_b437afeb72c2",
          "type": "date"
        },
        {
          "argument_field_id": "404b52eb_8549_49a4_bccb_f9bc987dd849",
          "field_id": "404b52eb_8549_49a4_bccb_f9bc987dd849",
          "label": "Hours Event 3",
          "output_field_id": "404b52eb_8549_49a4_bccb_f9bc987dd849",
          "type": "number"
        },
        {
          "argument_field_id": "40d6f8f4_505a_46fb_b8ec_cdfe56ba806f",
          "field_id": "40d6f8f4_505a_46fb_b8ec_cdfe56ba806f",
          "label": "Activity City",
          "output_field_id": "40d6f8f4_505a_46fb_b8ec_cdfe56ba806f",
          "type": "string"
        },
        {
          "argument_field_id": "410f1576_4a3b_4f90_993f_369ca6208e70",
          "field_id": "410f1576_4a3b_4f90_993f_369ca6208e70",
          "label": "Hours Event 7",
          "output_field_id": "410f1576_4a3b_4f90_993f_369ca6208e70",
          "type": "number"
        },
        {
          "argument_field_id": "4689ede5_c4d0_4cc8_88ba_abdeac672762",
          "field_id": "4689ede5_c4d0_4cc8_88ba_abdeac672762",
          "label": "Activity Contact Email",
          "output_field_id": "4689ede5_c4d0_4cc8_88ba_abdeac672762",
          "type": "string"
        },
        {
          "argument_field_id": "4727fb54_1245_444e_b9a0_5ef1d9ba8165",
          "field_id": "4727fb54_1245_444e_b9a0_5ef1d9ba8165",
          "label": "Remarks",
          "output_field_id": "4727fb54_1245_444e_b9a0_5ef1d9ba8165",
          "type": "string"
        },
        {
          "argument_field_id": "52bc22f6_e74d_4852_a071_2d37cf0f02b2",
          "field_id": "52bc22f6_e74d_4852_a071_2d37cf0f02b2",
          "label": "Cancellation Approved by",
          "output_field_id": "52bc22f6_e74d_4852_a071_2d37cf0f02b2",
          "type": "string"
        },
        {
          "argument_field_id": "554d3e32_a9e4_492a_915c_8fc5eee4551d",
          "field_id": "554d3e32_a9e4_492a_915c_8fc5eee4551d",
          "label": "Email Record ID",
          "output_field_id": "554d3e32_a9e4_492a_915c_8fc5eee4551d",
          "type": "string"
        },
        {
          "argument_field_id": "5e209040_8b16_48a3_9007_c03cd76dde16",
          "field_id": "5e209040_8b16_48a3_9007_c03cd76dde16",
          "label": "Date of 1st Event",
          "output_field_id": "5e209040_8b16_48a3_9007_c03cd76dde16",
          "type": "date"
        },
        {
          "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "label": "Updated at",
          "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "type": "date_time"
        },
        {
          "argument_field_id": "69246342_8538_4ac7_a570_bd69df6e6eb4",
          "field_id": "69246342_8538_4ac7_a570_bd69df6e6eb4",
          "label": "Hours Event 9",
          "output_field_id": "69246342_8538_4ac7_a570_bd69df6e6eb4",
          "type": "number"
        },
        {
          "argument_field_id": "69849ff0_cdb7_40b3_a977_b01b258fef6b",
          "field_id": "69849ff0_cdb7_40b3_a977_b01b258fef6b",
          "label": "Cancellation Reason",
          "output_field_id": "69849ff0_cdb7_40b3_a977_b01b258fef6b",
          "type": "string"
        },
        {
          "argument_field_id": "69934d20_5a3a_421b_973a_d48c324013d0",
          "field_id": "69934d20_5a3a_421b_973a_d48c324013d0",
          "label": "Error",
          "output_field_id": "69934d20_5a3a_421b_973a_d48c324013d0",
          "type": "boolean"
        },
        {
          "argument_field_id": "6c944059_f21e_43a7_b935_19166b5432fa",
          "field_id": "6c944059_f21e_43a7_b935_19166b5432fa",
          "label": "Date of 10th Event",
          "output_field_id": "6c944059_f21e_43a7_b935_19166b5432fa",
          "type": "date"
        },
        {
          "argument_field_id": "7102349b_0e89_49a3_bd7d_19682607f1d9",
          "field_id": "7102349b_0e89_49a3_bd7d_19682607f1d9",
          "label": "Date of 3rd Event",
          "output_field_id": "7102349b_0e89_49a3_bd7d_19682607f1d9",
          "type": "date"
        },
        {
          "argument_field_id": "7253ca9f_cada_49d3_99ba_129962c45e97",
          "field_id": "7253ca9f_cada_49d3_99ba_129962c45e97",
          "label": "Employee Country Record ID",
          "output_field_id": "7253ca9f_cada_49d3_99ba_129962c45e97",
          "type": "string"
        },
        {
          "argument_field_id": "74abc251_e97c_462f_bad0_2a4be1ad65d8",
          "field_id": "74abc251_e97c_462f_bad0_2a4be1ad65d8",
          "label": "Edit Type",
          "output_field_id": "74abc251_e97c_462f_bad0_2a4be1ad65d8",
          "type": "string"
        },
        {
          "argument_field_id": "760bbef6_46ee_40a3_9aa3_430452dead2f",
          "field_id": "760bbef6_46ee_40a3_9aa3_430452dead2f",
          "label": "$internal_value_760bbef6-46ee-40a3-9aa3-430452dead2f",
          "output_field_id": "760bbef6_46ee_40a3_9aa3_430452dead2f",
          "type": "string"
        },
        {
          "argument_field_id": "7928fb21_5d0c_40ea_b486_ef56cdddf941",
          "field_id": "7928fb21_5d0c_40ea_b486_ef56cdddf941",
          "label": "Activity Description",
          "output_field_id": "7928fb21_5d0c_40ea_b486_ef56cdddf941",
          "type": "string"
        },
        {
          "argument_field_id": "7afbd433_45b2_49c7_b826_782e80a49010",
          "field_id": "7afbd433_45b2_49c7_b826_782e80a49010",
          "label": "Hours Event 10",
          "output_field_id": "7afbd433_45b2_49c7_b826_782e80a49010",
          "type": "number"
        },
        {
          "argument_field_id": "7ef9ec80_c50c_4c89_9c82_7d059c9f083f",
          "field_id": "7ef9ec80_c50c_4c89_9c82_7d059c9f083f",
          "label": "Sequence Number",
          "output_field_id": "7ef9ec80_c50c_4c89_9c82_7d059c9f083f",
          "type": "integer"
        },
        {
          "argument_field_id": "7fee37e0_2499_4b16_848a_9571d68407c7",
          "field_id": "7fee37e0_2499_4b16_848a_9571d68407c7",
          "label": "Date of 9th Event",
          "output_field_id": "7fee37e0_2499_4b16_848a_9571d68407c7",
          "type": "date"
        },
        {
          "argument_field_id": "802fd7fe_8871_4620_bf45_22f6e8ba5fc2",
          "field_id": "802fd7fe_8871_4620_bf45_22f6e8ba5fc2",
          "label": "Organization Supported",
          "output_field_id": "802fd7fe_8871_4620_bf45_22f6e8ba5fc2",
          "type": "string"
        },
        {
          "argument_field_id": "876153d1_7763_4c4a_8dab_b901b5bcc007",
          "field_id": "876153d1_7763_4c4a_8dab_b901b5bcc007",
          "label": "Date of 2nd Event",
          "output_field_id": "876153d1_7763_4c4a_8dab_b901b5bcc007",
          "type": "date"
        },
        {
          "argument_field_id": "877856ae_d57b_479c_90b7_cd25cf04cf09",
          "field_id": "877856ae_d57b_479c_90b7_cd25cf04cf09",
          "label": "Number of Repeats",
          "output_field_id": "877856ae_d57b_479c_90b7_cd25cf04cf09",
          "type": "integer"
        },
        {
          "argument_field_id": "8a711850_6e92_4ab7_90a7_4ad66539f306",
          "field_id": "8a711850_6e92_4ab7_90a7_4ad66539f306",
          "label": "Employee City",
          "output_field_id": "8a711850_6e92_4ab7_90a7_4ad66539f306",
          "type": "string"
        },
        {
          "argument_field_id": "9e9bd915_2a6e_4a73_812d_bb2c5baec4f0",
          "field_id": "9e9bd915_2a6e_4a73_812d_bb2c5baec4f0",
          "label": "Approval Date",
          "output_field_id": "9e9bd915_2a6e_4a73_812d_bb2c5baec4f0",
          "type": "date"
        },
        {
          "argument_field_id": "a2335e02_cdaf_435d_b842_e18b69dcce29",
          "field_id": "a2335e02_cdaf_435d_b842_e18b69dcce29",
          "label": "Date of 5th Event",
          "output_field_id": "a2335e02_cdaf_435d_b842_e18b69dcce29",
          "type": "date"
        },
        {
          "argument_field_id": "a51e7a67_fa77_4d54_9423_6475b28cb091",
          "field_id": "a51e7a67_fa77_4d54_9423_6475b28cb091",
          "label": "Hours Event 6",
          "output_field_id": "a51e7a67_fa77_4d54_9423_6475b28cb091",
          "type": "number"
        },
        {
          "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "label": "Created at",
          "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "type": "date_time"
        },
        {
          "argument_field_id": "ad2a9320_2230_45ed_b689_9caef4dae5e9",
          "field_id": "ad2a9320_2230_45ed_b689_9caef4dae5e9",
          "label": "Cancellation Date",
          "output_field_id": "ad2a9320_2230_45ed_b689_9caef4dae5e9",
          "type": "date"
        },
        {
          "argument_field_id": "aece0ef4_7b3b_4621_9073_687670fc14a6",
          "field_id": "aece0ef4_7b3b_4621_9073_687670fc14a6",
          "label": "Team Name",
          "output_field_id": "aece0ef4_7b3b_4621_9073_687670fc14a6",
          "type": "string"
        },
        {
          "argument_field_id": "b36957f0_00e4_44e6_a465_ab063e6ac998",
          "field_id": "b36957f0_00e4_44e6_a465_ab063e6ac998",
          "label": "Activity Contact Name",
          "output_field_id": "b36957f0_00e4_44e6_a465_ab063e6ac998",
          "type": "string"
        },
        {
          "argument_field_id": "b3914c90_f85d_40db_a152_bc83fdcff759",
          "field_id": "b3914c90_f85d_40db_a152_bc83fdcff759",
          "label": "Donation Amount in USD",
          "output_field_id": "b3914c90_f85d_40db_a152_bc83fdcff759",
          "type": "number"
        },
        {
          "argument_field_id": "b6240623_a906_419f_8482_e8c87a553c16",
          "field_id": "b6240623_a906_419f_8482_e8c87a553c16",
          "label": "Employee Region",
          "output_field_id": "b6240623_a906_419f_8482_e8c87a553c16",
          "type": "string"
        },
        {
          "argument_field_id": "b7b769ad_f990_412e_9875_0bb7b7f856e8",
          "field_id": "b7b769ad_f990_412e_9875_0bb7b7f856e8",
          "label": "Confirm Action",
          "output_field_id": "b7b769ad_f990_412e_9875_0bb7b7f856e8",
          "type": "boolean"
        },
        {
          "argument_field_id": "b864a786_6329_46fb_a72a_c8e79f78c02b",
          "field_id": "b864a786_6329_46fb_a72a_c8e79f78c02b",
          "label": "Activity State Record ID",
          "output_field_id": "b864a786_6329_46fb_a72a_c8e79f78c02b",
          "type": "string"
        },
        {
          "argument_field_id": "b94dbd14_5a98_42ca_872b_00e804a5833f",
          "field_id": "b94dbd14_5a98_42ca_872b_00e804a5833f",
          "label": "Currency Record ID",
          "output_field_id": "b94dbd14_5a98_42ca_872b_00e804a5833f",
          "type": "string"
        },
        {
          "argument_field_id": "bc37fa3a_9da2_4763_938c_3aaa8afc3a01",
          "field_id": "bc37fa3a_9da2_4763_938c_3aaa8afc3a01",
          "label": "Cancellation in Progress",
          "output_field_id": "bc37fa3a_9da2_4763_938c_3aaa8afc3a01",
          "type": "boolean"
        },
        {
          "argument_field_id": "bd58f2c4_b532_485d_985d_bbca305b7b0f",
          "field_id": "bd58f2c4_b532_485d_985d_bbca305b7b0f",
          "label": "Repeating Event",
          "output_field_id": "bd58f2c4_b532_485d_985d_bbca305b7b0f",
          "type": "string"
        },
        {
          "argument_field_id": "c19f32dd_7a33_43af_9371_a733764e2680",
          "field_id": "c19f32dd_7a33_43af_9371_a733764e2680",
          "label": "Date of 6th Event",
          "output_field_id": "c19f32dd_7a33_43af_9371_a733764e2680",
          "type": "date"
        },
        {
          "argument_field_id": "c4ef3a4a_5dcd_4aa0_958c_e41d270bcc0a",
          "field_id": "c4ef3a4a_5dcd_4aa0_958c_e41d270bcc0a",
          "label": "Hours Event 4",
          "output_field_id": "c4ef3a4a_5dcd_4aa0_958c_e41d270bcc0a",
          "type": "number"
        },
        {
          "argument_field_id": "cb7bb8c4_ff9c_45b6_a3f1_de847e8ceb9c",
          "field_id": "cb7bb8c4_ff9c_45b6_a3f1_de847e8ceb9c",
          "label": "Donation Amount",
          "output_field_id": "cb7bb8c4_ff9c_45b6_a3f1_de847e8ceb9c",
          "type": "number"
        },
        {
          "argument_field_id": "continuation_token",
          "field_id": "continuation_token",
          "label": "Next Page Token",
          "output_field_id": "continuation_token",
          "type": "string"
        },
        {
          "argument_field_id": "d4d22a2e_f94f_4c44_844d_fd997d55ebe6",
          "field_id": "d4d22a2e_f94f_4c44_844d_fd997d55ebe6",
          "label": "Hours Event 8",
          "output_field_id": "d4d22a2e_f94f_4c44_844d_fd997d55ebe6",
          "type": "number"
        },
        {
          "argument_field_id": "dab764eb_dff8_4547_b8bb_67aae5df53c3",
          "field_id": "dab764eb_dff8_4547_b8bb_67aae5df53c3",
          "label": "Type",
          "output_field_id": "dab764eb_dff8_4547_b8bb_67aae5df53c3",
          "type": "string"
        },
        {
          "argument_field_id": "display_name",
          "field_id": "display_name",
          "label": "Employee ID",
          "output_field_id": "display_name",
          "type": "string"
        },
        {
          "argument_field_id": "e2bfdbe9_ccb2_4bfb_9c71_6d64d938d575",
          "field_id": "e2bfdbe9_ccb2_4bfb_9c71_6d64d938d575",
          "label": "Job Title",
          "output_field_id": "e2bfdbe9_ccb2_4bfb_9c71_6d64d938d575",
          "type": "string"
        },
        {
          "argument_field_id": "e39035d7_23cc_4fc5_b5f4_49a3c5be5932",
          "field_id": "e39035d7_23cc_4fc5_b5f4_49a3c5be5932",
          "label": "Date of 8th Event",
          "output_field_id": "e39035d7_23cc_4fc5_b5f4_49a3c5be5932",
          "type": "date"
        },
        {
          "argument_field_id": "e6d6384f_8eb2_4dd2_8ff6_1f0bdaa3d298",
          "field_id": "e6d6384f_8eb2_4dd2_8ff6_1f0bdaa3d298",
          "label": "Status",
          "output_field_id": "e6d6384f_8eb2_4dd2_8ff6_1f0bdaa3d298",
          "type": "string"
        },
        {
          "argument_field_id": "e8a8c5cb_6101_46bf_8573_1e1c3d26e5f9",
          "field_id": "e8a8c5cb_6101_46bf_8573_1e1c3d26e5f9",
          "label": "Employee ID Record ID",
          "output_field_id": "e8a8c5cb_6101_46bf_8573_1e1c3d26e5f9",
          "type": "string"
        },
        {
          "argument_field_id": "ec745f6d_2207_40c6_a674_5e8b6539f5eb",
          "field_id": "ec745f6d_2207_40c6_a674_5e8b6539f5eb",
          "label": "WC Record ID",
          "output_field_id": "ec745f6d_2207_40c6_a674_5e8b6539f5eb",
          "type": "string"
        },
        {
          "argument_field_id": "eff58340_4fde_41e0_963d_fb218d22f75d",
          "field_id": "eff58340_4fde_41e0_963d_fb218d22f75d",
          "label": "Department Name",
          "output_field_id": "eff58340_4fde_41e0_963d_fb218d22f75d",
          "type": "string"
        },
        {
          "argument_field_id": "f405f394_4ccf_499f_9673_c23875c72a4e",
          "field_id": "f405f394_4ccf_499f_9673_c23875c72a4e",
          "label": "Board Member",
          "output_field_id": "f405f394_4ccf_499f_9673_c23875c72a4e",
          "type": "boolean"
        },
        {
          "argument_field_id": "f56cd8f8_9d3a_4879_8864_ea652f4acb05",
          "field_id": "f56cd8f8_9d3a_4879_8864_ea652f4acb05",
          "label": "Hours Event 1",
          "output_field_id": "f56cd8f8_9d3a_4879_8864_ea652f4acb05",
          "type": "number"
        },
        {
          "argument_field_id": "fabd425b_634d_49f8_8726_76ba9d3ae9bf",
          "field_id": "fabd425b_634d_49f8_8726_76ba9d3ae9bf",
          "label": "Hours Event 2",
          "output_field_id": "fabd425b_634d_49f8_8726_76ba9d3ae9bf",
          "type": "number"
        },
        {
          "argument_field_id": "file_content",
          "field_id": "file_content",
          "label": "File contents",
          "output_field_id": "file_content",
          "type": "string"
        },
        {
          "argument_field_id": "filename",
          "field_id": "filename",
          "label": "File name",
          "output_field_id": "filename",
          "type": "string"
        },
        {
          "argument_field_id": "record_id",
          "field_id": "record_id",
          "label": "Record ID",
          "output_field_id": "record_id",
          "type": "string"
        }
      ],
      "name": "[SUB] Workato Cares Submission Raw Data",
      "public_id": "13821",
      "resource_kind": "data_table",
      "resource_ref": "resource_f6ecaffe74c8"
    },
    {
      "fields": [
        {
          "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "label": "Record ID",
          "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "type": "string"
        },
        {
          "argument_field_id": "24313710_ea71_43c5_9694_b5f55c56a5b7",
          "field_id": "24313710_ea71_43c5_9694_b5f55c56a5b7",
          "label": "Examples",
          "output_field_id": "24313710_ea71_43c5_9694_b5f55c56a5b7",
          "type": "string"
        },
        {
          "argument_field_id": "595299b9_812f_497c_b041_d43e6172fa67",
          "field_id": "595299b9_812f_497c_b041_d43e6172fa67",
          "label": "Name",
          "output_field_id": "595299b9_812f_497c_b041_d43e6172fa67",
          "type": "string"
        },
        {
          "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "label": "Updated at",
          "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "type": "date_time"
        },
        {
          "argument_field_id": "8389efac_4a35_447b_a378_8152c43250c4",
          "field_id": "8389efac_4a35_447b_a378_8152c43250c4",
          "label": "Level",
          "output_field_id": "8389efac_4a35_447b_a378_8152c43250c4",
          "type": "string"
        },
        {
          "argument_field_id": "<anon>aaaaaaaa_bbbb_cccc_dddd_eeeeeeeeeeee</anon>",
          "field_id": "<anon>aaaaaaaa_bbbb_cccc_dddd_eeeeeeeeeeee</anon>",
          "label": "Primary key",
          "output_field_id": "<anon>aaaaaaaa_bbbb_cccc_dddd_eeeeeeeeeeee</anon>",
          "resource_role": "primary_key"
        },
        {
          "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "label": "Created at",
          "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "type": "date_time"
        },
        {
          "argument_field_id": "a65c1011_c527_429b_ad1d_ad3ed4a485b8",
          "field_id": "a65c1011_c527_429b_ad1d_ad3ed4a485b8",
          "label": "Description",
          "output_field_id": "a65c1011_c527_429b_ad1d_ad3ed4a485b8",
          "type": "string"
        }
      ],
      "name": "[AC] WORKATO_INTEGRATION_LEVEL",
      "public_id": "20686",
      "resource_kind": "data_table",
      "resource_ref": "resource_f27e54a7c867"
    },
    {
      "fields": [
        {
          "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "label": "Record ID",
          "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "type": "string"
        },
        {
          "argument_field_id": "13b82b43_2f7a_4d98_a50d_1a5af68bc4c3",
          "field_id": "13b82b43_2f7a_4d98_a50d_1a5af68bc4c3",
          "label": "Quest Name",
          "output_field_id": "13b82b43_2f7a_4d98_a50d_1a5af68bc4c3",
          "type": "string"
        },
        {
          "argument_field_id": "3c779a6b_a7ca_44fc_acb8_69ce179d9584",
          "field_id": "3c779a6b_a7ca_44fc_acb8_69ce179d9584",
          "label": "Credited Date",
          "output_field_id": "3c779a6b_a7ca_44fc_acb8_69ce179d9584",
          "type": "string"
        },
        {
          "argument_field_id": "614e8425_fe37_4acd_b67b_1ed72fc8568a",
          "field_id": "614e8425_fe37_4acd_b67b_1ed72fc8568a",
          "label": "User ID",
          "output_field_id": "614e8425_fe37_4acd_b67b_1ed72fc8568a",
          "type": "string"
        },
        {
          "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "label": "Updated at",
          "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "type": "date_time"
        },
        {
          "argument_field_id": "68240f61_d77a_49f4_8252_24fc373a730d",
          "field_id": "68240f61_d77a_49f4_8252_24fc373a730d",
          "label": "Status",
          "output_field_id": "68240f61_d77a_49f4_8252_24fc373a730d",
          "type": "string"
        },
        {
          "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "label": "Created at",
          "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "type": "date_time"
        },
        {
          "argument_field_id": "acc76697_ddd7_4d13_87fc_5a6e0b5d6860",
          "field_id": "acc76697_ddd7_4d13_87fc_5a6e0b5d6860",
          "label": "Quest Code",
          "output_field_id": "acc76697_ddd7_4d13_87fc_5a6e0b5d6860",
          "type": "string"
        },
        {
          "argument_field_id": "continuation_token",
          "field_id": "continuation_token",
          "label": "Next Page Token",
          "output_field_id": "continuation_token",
          "type": "string"
        },
        {
          "argument_field_id": "d98a88e6_2320_492f_bd4b_eb600a86e0a1",
          "field_id": "d98a88e6_2320_492f_bd4b_eb600a86e0a1",
          "label": "Points Earned",
          "output_field_id": "d98a88e6_2320_492f_bd4b_eb600a86e0a1",
          "type": "integer"
        },
        {
          "argument_field_id": "ddd2fcd3_e629_4d80_9e78_fe3fb5c9f88b",
          "field_id": "ddd2fcd3_e629_4d80_9e78_fe3fb5c9f88b",
          "label": "$internal_value_ddd2fcd3-e629-4d80-9e78-fe3fb5c9f88b",
          "output_field_id": "ddd2fcd3_e629_4d80_9e78_fe3fb5c9f88b",
          "type": "string"
        },
        {
          "argument_field_id": "file_content",
          "field_id": "file_content",
          "label": "File contents",
          "output_field_id": "file_content",
          "type": "string"
        },
        {
          "argument_field_id": "filename",
          "field_id": "filename",
          "label": "File name",
          "output_field_id": "filename",
          "type": "string"
        }
      ],
      "name": "[WWW] Quest Activity",
      "public_id": "28115",
      "resource_kind": "data_table",
      "resource_ref": "resource_68aa4a601ed9"
    },
    {
      "fields": [
        {
          "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "label": "Record ID",
          "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "type": "string"
        },
        {
          "argument_field_id": "3ac3e90c_8e9b_4b58_b019_715ecd63b3d4",
          "field_id": "3ac3e90c_8e9b_4b58_b019_715ecd63b3d4",
          "label": "Application ID",
          "output_field_id": "3ac3e90c_8e9b_4b58_b019_715ecd63b3d4",
          "resource_role": "primary_key",
          "type": "string"
        },
        {
          "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "label": "Updated at",
          "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "type": "date_time"
        },
        {
          "argument_field_id": "7b20b969_f842_4eaa_8f35_753fe911fbee",
          "field_id": "7b20b969_f842_4eaa_8f35_753fe911fbee",
          "label": "Resume URL",
          "output_field_id": "7b20b969_f842_4eaa_8f35_753fe911fbee",
          "type": "string"
        },
        {
          "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "label": "Created at",
          "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "type": "date_time"
        },
        {
          "argument_field_id": "a7ba4bb3_7e03_4298_8f2e_f302d17fff39",
          "field_id": "a7ba4bb3_7e03_4298_8f2e_f302d17fff39",
          "label": "Job ID",
          "output_field_id": "a7ba4bb3_7e03_4298_8f2e_f302d17fff39",
          "type": "string"
        },
        {
          "argument_field_id": "c90c7596_43bf_466c_8a8f_b6d9819e2169",
          "field_id": "c90c7596_43bf_466c_8a8f_b6d9819e2169",
          "label": "Status",
          "output_field_id": "c90c7596_43bf_466c_8a8f_b6d9819e2169",
          "type": "string"
        },
        {
          "argument_field_id": "d32edade_33fa_4613_b8f7_976915faf727",
          "field_id": "d32edade_33fa_4613_b8f7_976915faf727",
          "label": "Log",
          "output_field_id": "d32edade_33fa_4613_b8f7_976915faf727",
          "type": "string"
        },
        {
          "argument_field_id": "fe5cbb7e_f1ba_4cc2_8cd3_509e81f6b4d1",
          "field_id": "fe5cbb7e_f1ba_4cc2_8cd3_509e81f6b4d1",
          "label": "Role",
          "output_field_id": "fe5cbb7e_f1ba_4cc2_8cd3_509e81f6b4d1",
          "type": "string"
        }
      ],
      "name": "30554",
      "public_id": "30554",
      "resource_kind": "data_table",
      "resource_ref": "resource_9888316085dd"
    },
    {
      "fields": [
        {
          "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "label": "Record ID",
          "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "type": "string"
        },
        {
          "argument_field_id": "1b9473c2_54ae_47f3_9576_c3ec76f3bd6d",
          "field_id": "1b9473c2_54ae_47f3_9576_c3ec76f3bd6d",
          "label": "target_project",
          "output_field_id": "1b9473c2_54ae_47f3_9576_c3ec76f3bd6d",
          "type": "string"
        },
        {
          "argument_field_id": "347bdaaf_5194_4363_a3e0_2a1e04f8aca2",
          "field_id": "347bdaaf_5194_4363_a3e0_2a1e04f8aca2",
          "label": "product_area",
          "output_field_id": "347bdaaf_5194_4363_a3e0_2a1e04f8aca2",
          "type": "string"
        },
        {
          "argument_field_id": "45e4add0_f5a6_4d3d_bcd0_2ed9e0cc15a8",
          "field_id": "45e4add0_f5a6_4d3d_bcd0_2ed9e0cc15a8",
          "label": "ticket_url",
          "output_field_id": "45e4add0_f5a6_4d3d_bcd0_2ed9e0cc15a8",
          "type": "string"
        },
        {
          "argument_field_id": "4fd3d64a_5fa4_4a8f_b5db_22a214b39b9f",
          "field_id": "4fd3d64a_5fa4_4a8f_b5db_22a214b39b9f",
          "label": "key",
          "output_field_id": "4fd3d64a_5fa4_4a8f_b5db_22a214b39b9f",
          "resource_role": "primary_key",
          "type": "string"
        },
        {
          "argument_field_id": "5a7eb53b_e407_41fd_a227_8f93e6a9c023",
          "field_id": "5a7eb53b_e407_41fd_a227_8f93e6a9c023",
          "label": "customer_company",
          "output_field_id": "5a7eb53b_e407_41fd_a227_8f93e6a9c023",
          "type": "string"
        },
        {
          "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "label": "Updated at",
          "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "type": "date_time"
        },
        {
          "argument_field_id": "68cbd891_51dd_4e33_92fa_8651d7e09441",
          "field_id": "68cbd891_51dd_4e33_92fa_8651d7e09441",
          "label": "updated",
          "output_field_id": "68cbd891_51dd_4e33_92fa_8651d7e09441",
          "type": "date_time"
        },
        {
          "argument_field_id": "75551508_f290_41de_88fd_d77306bebea5",
          "field_id": "75551508_f290_41de_88fd_d77306bebea5",
          "label": "summary",
          "output_field_id": "75551508_f290_41de_88fd_d77306bebea5",
          "type": "string"
        },
        {
          "argument_field_id": "a08c09e7_53d4_46dc_9bc7_a308696dc6c1",
          "field_id": "a08c09e7_53d4_46dc_9bc7_a308696dc6c1",
          "label": "status",
          "output_field_id": "a08c09e7_53d4_46dc_9bc7_a308696dc6c1",
          "type": "string"
        },
        {
          "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "label": "Created at",
          "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "type": "date_time"
        },
        {
          "argument_field_id": "b2ae037d_640f_4c56_aeee_17d61b531080",
          "field_id": "b2ae037d_640f_4c56_aeee_17d61b531080",
          "label": "pm_triage_breach_time",
          "output_field_id": "b2ae037d_640f_4c56_aeee_17d61b531080",
          "type": "date_time"
        },
        {
          "argument_field_id": "b57087c4_57c9_4d82_a27e_af9969896e53",
          "field_id": "b57087c4_57c9_4d82_a27e_af9969896e53",
          "label": "source_of_enhancement_request",
          "output_field_id": "b57087c4_57c9_4d82_a27e_af9969896e53",
          "type": "string"
        },
        {
          "argument_field_id": "d3779dbf_043c_4826_8c8e_d83c2e46b8fb",
          "field_id": "d3779dbf_043c_4826_8c8e_d83c2e46b8fb",
          "label": "description",
          "output_field_id": "d3779dbf_043c_4826_8c8e_d83c2e46b8fb",
          "type": "string"
        },
        {
          "argument_field_id": "d71da57a_cf54_48ca_89a5_51e4ea1bd675",
          "field_id": "d71da57a_cf54_48ca_89a5_51e4ea1bd675",
          "label": "product_manager",
          "output_field_id": "d71da57a_cf54_48ca_89a5_51e4ea1bd675",
          "type": "string"
        },
        {
          "argument_field_id": "e267c871_7ff1_4b0b_a7bc_b1e39a5ed39b",
          "field_id": "e267c871_7ff1_4b0b_a7bc_b1e39a5ed39b",
          "label": "created",
          "output_field_id": "e267c871_7ff1_4b0b_a7bc_b1e39a5ed39b",
          "type": "date_time"
        },
        {
          "argument_field_id": "e8bf2d92_807a_477b_9c2a_de56a876b993",
          "field_id": "e8bf2d92_807a_477b_9c2a_de56a876b993",
          "label": "pe_team",
          "output_field_id": "e8bf2d92_807a_477b_9c2a_de56a876b993",
          "type": "string"
        },
        {
          "argument_field_id": "f7651665_4dd2_413d_a704_f81972a4c1d4",
          "field_id": "f7651665_4dd2_413d_a704_f81972a4c1d4",
          "label": "pm_triage_breach",
          "output_field_id": "f7651665_4dd2_413d_a704_f81972a4c1d4",
          "type": "string"
        }
      ],
      "name": "PSM Enhancements Data",
      "public_id": "33563",
      "resource_kind": "data_table",
      "resource_ref": "resource_d5e66c9a88f3"
    },
    {
      "fields": [
        {
          "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "label": "Record ID",
          "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "type": "string"
        },
        {
          "argument_field_id": "1398de92_647f_4c1a_b1b3_77c53af0ed78",
          "field_id": "1398de92_647f_4c1a_b1b3_77c53af0ed78",
          "label": "assets_and_dependencies",
          "output_field_id": "1398de92_647f_4c1a_b1b3_77c53af0ed78",
          "type": "string"
        },
        {
          "argument_field_id": "13f19e63_dd47_4682_81c0_47c4bcaeeae3",
          "field_id": "13f19e63_dd47_4682_81c0_47c4bcaeeae3",
          "label": "released_at",
          "output_field_id": "13f19e63_dd47_4682_81c0_47c4bcaeeae3",
          "type": "date_time"
        },
        {
          "argument_field_id": "205f0633_0893_447e_a24f_146797dd3dfe",
          "field_id": "205f0633_0893_447e_a24f_146797dd3dfe",
          "label": "release_notes",
          "output_field_id": "205f0633_0893_447e_a24f_146797dd3dfe",
          "type": "string"
        },
        {
          "argument_field_id": "2069a23e_4fcc_4674_9f81_094ac5e8c95d",
          "field_id": "2069a23e_4fcc_4674_9f81_094ac5e8c95d",
          "label": "$internal_value_2069a23e-4fcc-4674-9f81-094ac5e8c95d",
          "output_field_id": "2069a23e_4fcc_4674_9f81_094ac5e8c95d",
          "type": "string"
        },
        {
          "argument_field_id": "225a1c1a_9719_4d19_bb71_8d5762009d49",
          "field_id": "225a1c1a_9719_4d19_bb71_8d5762009d49",
          "label": "expires_at",
          "output_field_id": "225a1c1a_9719_4d19_bb71_8d5762009d49",
          "type": "date_time"
        },
        {
          "argument_field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
          "field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
          "label": "deprecated_at",
          "output_field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
          "type": "date_time"
        },
        {
          "argument_field_id": "4612b15c_300f_4120_870b_1884489c3736",
          "field_id": "4612b15c_300f_4120_870b_1884489c3736",
          "label": "version_number",
          "output_field_id": "4612b15c_300f_4120_870b_1884489c3736",
          "type": "integer"
        },
        {
          "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "label": "Updated at",
          "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "type": "date_time"
        },
        {
          "argument_field_id": "622152c7_a09f_4d54_80f7_add539bee209",
          "field_id": "622152c7_a09f_4d54_80f7_add539bee209",
          "label": "$internal_value_622152c7-a09f-4d54-80f7-add539bee209",
          "output_field_id": "622152c7_a09f_4d54_80f7_add539bee209",
          "type": "string"
        },
        {
          "argument_field_id": "6e0f65d3_4376_4264_a472_c705bd4d41b4",
          "field_id": "6e0f65d3_4376_4264_a472_c705bd4d41b4",
          "label": "directory",
          "output_field_id": "6e0f65d3_4376_4264_a472_c705bd4d41b4",
          "type": "string"
        },
        {
          "argument_field_id": "7b0540a6_7322_42dd_b6cf_89cf8759fb73",
          "field_id": "7b0540a6_7322_42dd_b6cf_89cf8759fb73",
          "label": "installed_from_package_version_id",
          "output_field_id": "7b0540a6_7322_42dd_b6cf_89cf8759fb73",
          "type": "string"
        },
        {
          "argument_field_id": "891c88dd_6aa1_46a3_80ef_92fbb6c21f53",
          "field_id": "891c88dd_6aa1_46a3_80ef_92fbb6c21f53",
          "label": "$internal_value_891c88dd-6aa1-46a3-80ef-92fbb6c21f53",
          "output_field_id": "891c88dd_6aa1_46a3_80ef_92fbb6c21f53",
          "type": "string"
        },
        {
          "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "label": "Created at",
          "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "type": "date_time"
        },
        {
          "argument_field_id": "cc31f2eb_b841_498c_bced_247d9dd78edb",
          "field_id": "cc31f2eb_b841_498c_bced_247d9dd78edb",
          "label": "name",
          "output_field_id": "cc31f2eb_b841_498c_bced_247d9dd78edb",
          "type": "string"
        },
        {
          "argument_field_id": "continuation_token",
          "field_id": "continuation_token",
          "label": "Next Page Token",
          "output_field_id": "continuation_token",
          "type": "string"
        },
        {
          "argument_field_id": "d1a07df5_2696_436d_930b_9a3ba82e0f26",
          "field_id": "d1a07df5_2696_436d_930b_9a3ba82e0f26",
          "label": "job_id",
          "output_field_id": "d1a07df5_2696_436d_930b_9a3ba82e0f26",
          "type": "string"
        },
        {
          "argument_field_id": "dfdac2d4_7384_4916_8416_0bc42c29d36f",
          "field_id": "dfdac2d4_7384_4916_8416_0bc42c29d36f",
          "label": "jira_issue_key",
          "output_field_id": "dfdac2d4_7384_4916_8416_0bc42c29d36f",
          "type": "string"
        },
        {
          "argument_field_id": "display_name",
          "field_id": "display_name",
          "label": "name",
          "output_field_id": "display_name",
          "type": "string"
        },
        {
          "argument_field_id": "e2bf4aa4_a19c_4cbe_92b3_0ff50bcbbfbc",
          "field_id": "e2bf4aa4_a19c_4cbe_92b3_0ff50bcbbfbc",
          "label": "manifest",
          "output_field_id": "e2bf4aa4_a19c_4cbe_92b3_0ff50bcbbfbc",
          "type": "string"
        },
        {
          "argument_field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
          "field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
          "label": "deprecated",
          "output_field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
          "type": "boolean"
        },
        {
          "argument_field_id": "e6395bdd_5e77_4ce7_8dbc_256c798486f9",
          "field_id": "e6395bdd_5e77_4ce7_8dbc_256c798486f9",
          "label": "resume_token",
          "output_field_id": "e6395bdd_5e77_4ce7_8dbc_256c798486f9",
          "type": "string"
        },
        {
          "argument_field_id": "fc7aac95_0564_472c_a07f_9b20ba8e5a7b",
          "field_id": "fc7aac95_0564_472c_a07f_9b20ba8e5a7b",
          "label": "released",
          "output_field_id": "fc7aac95_0564_472c_a07f_9b20ba8e5a7b",
          "type": "boolean"
        },
        {
          "argument_field_id": "record_id",
          "field_id": "record_id",
          "label": "Record ID",
          "output_field_id": "record_id",
          "type": "string"
        }
      ],
      "name": "Package Versions",
      "public_id": "7199",
      "resource_kind": "data_table",
      "resource_ref": "resource_f360808d806b"
    },
    {
      "fields": [
        {
          "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "label": "Record ID",
          "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "type": "string"
        },
        {
          "argument_field_id": "25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e",
          "field_id": "25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e",
          "label": "name",
          "output_field_id": "25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e",
          "type": "string"
        },
        {
          "argument_field_id": "27bdf527_6657_412d_a106_293c28940a44",
          "field_id": "27bdf527_6657_412d_a106_293c28940a44",
          "label": "include_packaging_assets_for_installations",
          "output_field_id": "27bdf527_6657_412d_a106_293c28940a44",
          "type": "boolean"
        },
        {
          "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "label": "Updated at",
          "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "type": "date_time"
        },
        {
          "argument_field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
          "field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
          "label": "enabled",
          "output_field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
          "type": "boolean"
        },
        {
          "argument_field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
          "field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
          "label": "user_id",
          "output_field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
          "type": "string"
        },
        {
          "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "label": "Created at",
          "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "type": "date_time"
        },
        {
          "argument_field_id": "continuation_token",
          "field_id": "continuation_token",
          "label": "Next Page Token",
          "output_field_id": "continuation_token",
          "type": "string"
        },
        {
          "argument_field_id": "e12c33da_6a37_4ecd_86e1_9cb2dafd0787",
          "field_id": "e12c33da_6a37_4ecd_86e1_9cb2dafd0787",
          "label": "collection",
          "output_field_id": "e12c33da_6a37_4ecd_86e1_9cb2dafd0787",
          "type": "string"
        },
        {
          "argument_field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
          "field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
          "label": "access_profile_id",
          "output_field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
          "type": "string"
        }
      ],
      "name": "Workspaces",
      "public_id": "7201",
      "resource_kind": "data_table",
      "resource_ref": "resource_0f7c5bb6a482"
    },
    {
      "fields": [
        {
          "argument_field_id": "0f34f995_2a34_4fcf_b5c3_0270f8f718d0",
          "field_id": "0f34f995_2a34_4fcf_b5c3_0270f8f718d0",
          "label": "workspace",
          "output_field_id": "0f34f995_2a34_4fcf_b5c3_0270f8f718d0",
          "type": "string"
        },
        {
          "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "label": "Record ID",
          "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
          "type": "string"
        },
        {
          "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "label": "Updated at",
          "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
          "type": "date_time"
        },
        {
          "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "label": "Created at",
          "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
          "type": "date_time"
        },
        {
          "argument_field_id": "continuation_token",
          "field_id": "continuation_token",
          "label": "Next Page Token",
          "output_field_id": "continuation_token",
          "type": "string"
        },
        {
          "argument_field_id": "db77c09c_5f9c_4681_8135_50f0c39af67a",
          "field_id": "db77c09c_5f9c_4681_8135_50f0c39af67a",
          "label": "package",
          "output_field_id": "db77c09c_5f9c_4681_8135_50f0c39af67a",
          "type": "string"
        },
        {
          "argument_field_id": "display_name",
          "field_id": "display_name",
          "label": "name",
          "output_field_id": "display_name",
          "type": "string"
        },
        {
          "argument_field_id": "fc952b5a_bf20_4985_a1bd_5cfa657e8c74",
          "field_id": "fc952b5a_bf20_4985_a1bd_5cfa657e8c74",
          "label": "$internal_value_fc952b5a-bf20-4985-a1bd-5cfa657e8c74",
          "output_field_id": "fc952b5a_bf20_4985_a1bd_5cfa657e8c74",
          "type": "string"
        },
        {
          "argument_field_id": "record_id",
          "field_id": "record_id",
          "label": "Record ID",
          "output_field_id": "record_id",
          "type": "string"
        }
      ],
      "name": "Workspace Package Installations",
      "public_id": "9008",
      "resource_kind": "data_table",
      "resource_ref": "resource_d9c99396091b"
    }
  ]
}

For workspace field cards, use `argument_field_id` when constructing tool
arguments and `output_field_id` when reading tool results. These are public
adapter field paths, not private recipe identifiers. Refer to a candidate
workspace resource by its opaque `resource_ref`; `resource_kind` is descriptive
and is not a tool argument name.

## Available tool contracts
[
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Replay a Workato clock wait interval without sleeping during benchmark execution. Advance the simulated clock only when the task explicitly requires waiting. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "interval": {
          "type": "string"
        }
      },
      "required": [
        "interval"
      ],
      "type": "object"
    },
    "name": "clock.wait_for_interval",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "clock",
      "operation": "operation",
      "side_effect": true,
      "when_to_use": "Advance the simulated clock only when the task explicitly requires waiting."
    }
  },
  {
    "canonical_argument_rules": {
      "argument_shape": {
        "always": [
          "parent_id",
          "name"
        ]
      },
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "parent_encoding": "Use parent_id only. folderId is connector-authoring input and is not a canonical benchmark argument alias.",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Create a folder in the in-process Google Drive simulator. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "folderId": {
          "type": "string"
        },
        "name": {
          "type": "string"
        },
        "parent_id": {
          "type": "string"
        }
      },
      "required": [
        "parent_id",
        "name"
      ],
      "type": "object"
    },
    "name": "google_drive.create_folder",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "google_drive",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Append one row to the simulated Google Sheet. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "data": {
          "type": "object"
        },
        "headers": {
          "type": "array"
        },
        "sheet": {
          "type": "string"
        },
        "spreadsheet": {
          "type": "string"
        }
      },
      "required": [
        "data"
      ],
      "type": "object"
    },
    "name": "google_sheets.add_spreadsheet_row_v4",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "google_sheets",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Retrieve rows from the simulated Google Sheet. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "range": {
          "type": "string"
        },
        "sheet": {
          "type": "string"
        },
        "spreadsheet": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "name": "google_sheets.get_spreadsheet_rows_v4",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "read",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "google_sheets",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  },
  {
    "canonical_argument_rules": {
      "argument_shape": {
        "always": [
          "spreadsheet",
          "sheet",
          "data",
          "count"
        ]
      },
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "count_encoding": "count is a non-negative JSON integer when present and null when absent. Numeric strings are not canonical.",
      "filter_encoding": "data is the exact object of column-name equality filters; do not move a filter into a query string.",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Search rows in the simulated Google Sheet using exact column filters. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "count": {
          "minimum": 0,
          "type": [
            "integer",
            "null"
          ]
        },
        "data": {
          "type": "object"
        },
        "sheet": {
          "type": "string"
        },
        "spreadsheet": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "name": "google_sheets.search_spreadsheet_rows_v4_new",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "read",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "google_sheets",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Update one row in the simulated Google Sheet. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "data": {
          "type": "object"
        },
        "row_number": {
          "type": "integer"
        },
        "sheet": {
          "type": "string"
        },
        "spreadsheet": {
          "type": "string"
        }
      },
      "required": [
        "row_number",
        "data"
      ],
      "type": "object"
    },
    "name": "google_sheets.update_row_v4_new",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "google_sheets",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
    }
  },
  {
    "canonical_argument_rules": {
      "argument_shape": {
        "always": [
          "project_issuetype",
          "summary",
          "description",
          "priority",
          "labels"
        ]
      },
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "optional_value_encoding": "All five canonical keys are present. Unconfigured optional text fields are empty strings and unconfigured labels is null.",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Create an issue in the in-process Jira simulator. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "required": [
        "project_issuetype",
        "summary"
      ],
      "type": "object"
    },
    "name": "jira.create_issue",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "jira",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Add a batch of entries to a controlled Workato lookup table. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "entries": {
          "items": {
            "type": "object"
          },
          "type": "array"
        },
        "lookup_table_id": {
          "type": "string"
        }
      },
      "required": [
        "lookup_table_id",
        "entries"
      ],
      "type": "object"
    },
    "name": "lookup_table.add_batch_of_entries",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "lookup_table",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Add an entry to a controlled Workato lookup table. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "lookup_table_id": {
          "type": "string"
        },
        "parameters": {
          "type": "object"
        }
      },
      "required": [
        "lookup_table_id",
        "parameters"
      ],
      "type": "object"
    },
    "name": "lookup_table.add_entry",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "lookup_table",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Delete an entry from a controlled Workato lookup table. Destructive operation. Use only when deletion is explicitly required and the target is unambiguous. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "id": {},
        "ignore_not_found": {},
        "lookup_table_id": {
          "type": "string"
        }
      },
      "required": [
        "lookup_table_id",
        "id"
      ],
      "type": "object"
    },
    "name": "lookup_table.delete_entry",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "lookup_table",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Destructive operation. Use only when deletion is explicitly required and the target is unambiguous."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Read entries from a controlled Workato lookup table. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "lookup_table_id": {
          "type": "string"
        }
      },
      "required": [
        "lookup_table_id"
      ],
      "type": "object"
    },
    "name": "lookup_table.get_entries",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "read",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "lookup_table",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Read one entry from a controlled Workato lookup table. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "id": {},
        "lookup_table_id": {
          "type": "string"
        },
        "parameters": {
          "type": "object"
        }
      },
      "required": [
        "lookup_table_id"
      ],
      "type": "object"
    },
    "name": "lookup_table.get_entry",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "read",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "lookup_table",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Search entries in a controlled Workato lookup table. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "lookup_table_id": {
          "type": "string"
        },
        "parameters": {
          "type": "object"
        }
      },
      "required": [
        "lookup_table_id",
        "parameters"
      ],
      "type": "object"
    },
    "name": "lookup_table.search_entries",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "read",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "lookup_table",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Delete all entries from a controlled Workato lookup table. Destructive operation. Use only when deletion is explicitly required and the target is unambiguous. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "lookup_table_id": {
          "type": "string"
        }
      },
      "required": [
        "lookup_table_id"
      ],
      "type": "object"
    },
    "name": "lookup_table.truncate",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "lookup_table",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Destructive operation. Use only when deletion is explicitly required and the target is unambiguous."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Update an entry in a controlled Workato lookup table. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "id": {},
        "lookup_table_id": {
          "type": "string"
        },
        "parameters": {
          "type": "object"
        }
      },
      "required": [
        "lookup_table_id",
        "id",
        "parameters"
      ],
      "type": "object"
    },
    "name": "lookup_table.update_entry",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "lookup_table",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Create a simulated Salesforce record. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. Connector selection concepts cross-checked against workato-recipe-skills/skills/salesforce-recipes; the simulator schema below is the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "fields": {
          "type": "object"
        },
        "sobject": {
          "type": "string"
        }
      },
      "required": [
        "sobject",
        "fields"
      ],
      "type": "object"
    },
    "name": "salesforce.create_record",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "salesforce",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
    }
  },
  {
    "canonical_argument_rules": {
      "argument_shape": {
        "always": [
          "sobject",
          "query"
        ],
        "optional": [
          "filters",
          "limit"
        ]
      },
      "boolean_encoding": "Equality-filter values use JSON booleans for boolean fields. Boolean tokens inside query remain query syntax.",
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_non_query_arguments_plus_query_semantics",
      "limit_encoding": "Limit placement is part of query semantics. If supplied as a connector field, its transport type is a non-negative JSON integer. Do not encode it as a numeric string.",
      "object_key_order": "canonical_json_sorted_keys",
      "query_comparison": "runtime_result_or_state_equivalence",
      "query_encoding": "SOQL spelling and structure are not compared directly. The Salesforce object stays exact and the executed selection must return the same business records on every variant.",
      "query_normalization": "No syntax normalization defines correctness; execute the connector and compare the selected row multiset.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "selection_mode": "SOQL text, equality filters, and a separate limit are one query surface. Alternative encodings are accepted only when the executed connector returns the same row multiset.",
      "semantic_rewrites": "query_surface_only"
    },
    "description": "Search simulated Salesforce records. Use exactly one mode: either a non-empty SOQL-style query with filters omitted, or query='' with simple equality filters containing only field and value. Never send both. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. Connector selection concepts cross-checked against workato-recipe-skills/skills/salesforce-recipes; the simulator schema below is the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "oneOf": [
        {
          "properties": {
            "filters": {
              "maxItems": 0,
              "type": "array"
            },
            "query": {
              "minLength": 1,
              "type": "string"
            }
          }
        },
        {
          "properties": {
            "filters": {
              "minItems": 1,
              "type": "array"
            },
            "query": {
              "const": ""
            }
          },
          "required": [
            "filters"
          ]
        }
      ],
      "properties": {
        "filters": {
          "items": {
            "additionalProperties": false,
            "properties": {
              "field": {
                "type": "string"
              },
              "value": {}
            },
            "required": [
              "field",
              "value"
            ],
            "type": "object"
          },
          "type": "array"
        },
        "limit": {
          "minimum": 0,
          "type": "integer"
        },
        "query": {
          "type": "string"
        },
        "sobject": {
          "type": "string"
        }
      },
      "required": [
        "sobject",
        "query"
      ],
      "type": "object"
    },
    "name": "salesforce.search_records",
    "output_schema": {
      "properties": {
        "count": {
          "type": "integer"
        },
        "ok": {
          "type": "boolean"
        },
        "records": {
          "items": {
            "type": "object"
          },
          "type": "array"
        }
      },
      "required": [
        "ok",
        "records",
        "count"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "read",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "salesforce",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  },
  {
    "canonical_argument_rules": {
      "argument_shape": {
        "batch": [
          "sobject",
          "records"
        ],
        "scalar": [
          "sobject",
          "id",
          "fields"
        ]
      },
      "batch_encoding": "A scalar record update uses exactly {sobject, id, fields}. An imported composite/batch update uses exactly {sobject, records}, where every records item is {sobject, id, fields}. Batch form is retained even when runtime expansion yields one item; cardinality never changes the argument shape.",
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "field_encoding": "fields contains only mapped Salesforce fields. Connector authoring metadata is omitted, and an absent optional value is omitted rather than encoded as null.",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Update a simulated Salesforce record. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. Connector selection concepts cross-checked against workato-recipe-skills/skills/salesforce-recipes; the simulator schema below is the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "oneOf": [
        {
          "required": [
            "sobject",
            "id",
            "fields"
          ]
        },
        {
          "required": [
            "sobject",
            "records"
          ]
        }
      ],
      "properties": {
        "fields": {
          "type": "object"
        },
        "id": {
          "type": "string"
        },
        "records": {
          "items": {
            "additionalProperties": false,
            "properties": {
              "fields": {
                "type": "object"
              },
              "id": {
                "type": "string"
              },
              "sobject": {
                "type": "string"
              }
            },
            "required": [
              "sobject",
              "id",
              "fields"
            ],
            "type": "object"
          },
          "type": "array"
        },
        "sobject": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "name": "salesforce.update_record",
    "output_schema": {
      "properties": {
        "id": {
          "type": "string"
        },
        "ok": {
          "type": "boolean"
        }
      },
      "required": [
        "ok"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "salesforce",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Upsert a simulated Salesforce record by a primary key field. Use when the task requires create-or-update behavior keyed by the match fields in the schema. Supply only grounded identifiers and values. Connector selection concepts cross-checked against workato-recipe-skills/skills/salesforce-recipes; the simulator schema below is the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "fields": {
          "type": "object"
        },
        "key_field": {
          "type": "string"
        },
        "sobject": {
          "type": "string"
        }
      },
      "required": [
        "sobject",
        "key_field",
        "fields"
      ],
      "type": "object"
    },
    "name": "salesforce.upsert_record",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "salesforce",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use when the task requires create-or-update behavior keyed by the match fields in the schema. Supply only grounded identifiers and values."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Delete a simulated Slack message by channel and timestamp. Destructive operation. Use only when deletion is explicitly required and the target is unambiguous. Native Slack versus interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "channel": {
          "type": "string"
        },
        "ts": {
          "type": "string"
        }
      },
      "required": [
        "channel",
        "ts"
      ],
      "type": "object"
    },
    "name": "slack.delete_message",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "slack",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Destructive operation. Use only when deletion is explicitly required and the target is unambiguous."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Post a message to the in-process Slack simulator. Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends. Native Slack versus interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "attachments": {
          "items": {
            "additionalProperties": false,
            "properties": {
              "actions": {
                "type": "array"
              },
              "color": {
                "type": "string"
              },
              "fields": {
                "items": {
                  "additionalProperties": false,
                  "properties": {
                    "short": {
                      "type": "boolean"
                    },
                    "title": {
                      "type": "string"
                    },
                    "value": {
                      "type": "string"
                    }
                  },
                  "required": [
                    "title",
                    "value"
                  ],
                  "type": "object"
                },
                "type": "array"
              },
              "footer": {
                "type": "string"
              },
              "footer_icon": {
                "type": "string"
              },
              "pretext": {
                "type": "string"
              },
              "text": {
                "type": "string"
              },
              "title": {
                "type": "string"
              },
              "title_link": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": "array"
        },
        "blocks": {
          "type": "array"
        },
        "channel": {
          "type": "string"
        },
        "text": {
          "type": "string"
        },
        "thread_ts": {
          "type": "string"
        },
        "ts": {
          "type": "string"
        }
      },
      "required": [
        "channel",
        "text"
      ],
      "type": "object"
    },
    "name": "slack.post_message",
    "output_schema": {
      "properties": {
        "channel": {
          "type": "string"
        },
        "message": {
          "type": "object"
        },
        "ok": {
          "type": "boolean"
        },
        "thread_ts": {
          "type": "string"
        },
        "ts": {
          "type": "string"
        }
      },
      "required": [
        "ok"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "communication",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "slack",
      "operation": "communication",
      "side_effect": true,
      "when_to_use": "Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "invoking_context_encoding": "The invoking channel, thread timestamp, user, and original timestamp are connector-injected transport context and are omitted from the canonical request. Omit false optional mode flags; include ephemeral, replace_original, or delete_original only when true. Destination correctness is still checked from the resulting Slack side effect.",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Reply to the invoking Slack bot-command conversation, or to an explicit channel/thread when supplied. Omitting channel uses the invoking conversation routed through benchmark isolation. The reply may contain text, Block Kit blocks, or both; it may be requester-only, replace the original command response, or delete the original while posting the reply when those modes are set. Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends. Native Slack versus interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "blocks": {
          "items": {
            "type": "object"
          },
          "type": "array"
        },
        "channel": {
          "type": "string"
        },
        "delete_original": {
          "type": "boolean"
        },
        "ephemeral": {
          "type": "boolean"
        },
        "original_ts": {
          "type": "string"
        },
        "replace_original": {
          "type": "boolean"
        },
        "text": {
          "type": "string"
        },
        "thread_ts": {
          "type": "string"
        },
        "user": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "name": "slack.post_reply",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "communication",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "slack",
      "operation": "communication",
      "side_effect": true,
      "when_to_use": "Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Update a simulated Slack message by replacing or removing Block Kit blocks with matching block IDs. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. Native Slack versus interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "blocks_to_update": {
          "type": "array"
        },
        "message_json": {}
      },
      "required": [
        "message_json",
        "blocks_to_update"
      ],
      "type": "object"
    },
    "name": "slack.update_blocks_by_block_id",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "slack",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Open a Slack modal in the simulator. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. Interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "trigger_id": {
          "type": "string"
        },
        "view": {
          "type": "object"
        }
      },
      "required": [
        "trigger_id",
        "view"
      ],
      "type": "object"
    },
    "name": "slack_bot.block_kit_modals",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "slack_bot",
      "operation": "transform",
      "side_effect": false,
      "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Return dynamic menu options for a Slack trigger payload. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. Interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "options": {
          "items": {
            "additionalProperties": false,
            "properties": {
              "label": {
                "type": "string"
              },
              "value": {
                "type": "string"
              }
            },
            "required": [
              "label",
              "value"
            ],
            "type": "object"
          },
          "type": "array"
        }
      },
      "required": [
        "options"
      ],
      "type": "object"
    },
    "name": "slack_bot.generate_menu_options",
    "output_schema": {
      "properties": {
        "ok": {
          "type": "boolean"
        },
        "options": {
          "type": "array"
        }
      },
      "required": [
        "ok",
        "options"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "slack_bot",
      "operation": "transform",
      "side_effect": false,
      "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Look up a deterministic simulated Slack user by email or id. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. Interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "email": {
          "type": "string"
        },
        "id": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "name": "slack_bot.get_user_by_email",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "read",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "slack_bot",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Publish a Slack App Home view in the simulator. Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends. Interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "user_id": {
          "type": "string"
        },
        "view": {
          "type": "object"
        }
      },
      "required": [
        "user_id",
        "view"
      ],
      "type": "object"
    },
    "name": "slack_bot.open_bot_app_home",
    "output_schema": {
      "properties": {
        "ok": {
          "type": "boolean"
        }
      },
      "required": [
        "ok"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "slack_bot",
      "operation": "communication",
      "side_effect": true,
      "when_to_use": "Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends."
    }
  },
  {
    "canonical_argument_rules": {
      "argument_shape": {
        "always": [
          "sql",
          "parameters"
        ]
      },
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_non_query_arguments_plus_query_semantics",
      "object_key_order": "canonical_json_sorted_keys",
      "parameter_encoding": "parameters is exactly the configured parameters.data object, or {} when absent.",
      "query_comparison": "runtime_result_or_state_equivalence",
      "query_encoding": "SQL spelling and structure are not compared directly. Reads must return the same row multiset; mutating statements must leave the same Snowflake table state on every variant.",
      "query_normalization": "No syntax normalization defines correctness; execute reads and compare row multisets, or execute writes and compare the final Snowflake table state.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "query_surface_only"
    },
    "description": "Run constrained Snowflake SQL against isolated benchmark state. Supports SELECT, INSERT INTO ... SELECT, ALTER TABLE ... ADD, COPY INTO from a declared stage, retention DELETE, TRUNCATE TABLE, and CREATE OR REPLACE TABLE AS SELECT within the documented simulator SQL subset. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "limit": {},
        "offset": {},
        "parameters": {
          "type": "object"
        },
        "sql": {
          "type": "string"
        }
      },
      "required": [
        "sql"
      ],
      "type": "object"
    },
    "name": "snowflake.run_custom_sql",
    "output_schema": {
      "properties": {
        "ok": {
          "type": "boolean"
        },
        "row_count": {
          "type": "integer"
        },
        "rows": {
          "items": {
            "type": "object"
          },
          "type": "array"
        },
        "rows_affected": {
          "type": "integer"
        }
      },
      "required": [
        "ok",
        "rows",
        "rows_affected"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "snowflake",
      "operation": "transform",
      "side_effect": false,
      "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
    }
  },
  {
    "canonical_argument_rules": {
      "argument_shape": {
        "always": [
          "table",
          "where",
          "parameters",
          "limit",
          "offset",
          "orderby",
          "output_columns"
        ]
      },
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "pagination_encoding": "limit and offset are JSON integers when present and null when absent. Numeric strings are not canonical.",
      "parameter_encoding": "parameters is exactly the configured parameters.data object, or {} when absent.",
      "query_encoding": "where, orderby, and output_columns remain separate fields; do not replace this structured call with SQL text.",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Search rows in an isolated benchmark Snowflake table state. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "limit": {
          "minimum": 0,
          "type": [
            "integer",
            "null"
          ]
        },
        "offset": {
          "minimum": 0,
          "type": [
            "integer",
            "null"
          ]
        },
        "orderby": {
          "type": "string"
        },
        "output_columns": {
          "description": "Optional projection of returned fields. Accepts a newline- or comma-separated field list.",
          "type": "string"
        },
        "parameters": {
          "type": "object"
        },
        "table": {
          "type": "string"
        },
        "where": {
          "type": "string"
        }
      },
      "required": [
        "table"
      ],
      "type": "object"
    },
    "name": "snowflake.search_rows",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "read",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "snowflake",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  },
  {
    "canonical_argument_rules": {
      "argument_shape": {
        "always": [
          "sql",
          "parameters",
          "limit",
          "offset"
        ]
      },
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_non_query_arguments_plus_query_semantics",
      "object_key_order": "canonical_json_sorted_keys",
      "pagination_encoding": "limit and offset are JSON integers when present and null when absent. Numeric strings are not canonical.",
      "parameter_encoding": "parameters is exactly the configured parameters.data object, or {} when absent.",
      "query_comparison": "runtime_result_or_state_equivalence",
      "query_encoding": "SQL spelling and structure are not compared directly. The executed read must return the same row multiset on every variant; parameters and pagination participate in that query result semantics.",
      "query_normalization": "No syntax normalization defines correctness; execute the connector and compare the selected row multiset.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "query_surface_only"
    },
    "description": "Run a constrained SELECT query against isolated benchmark Snowflake table state. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "limit": {
          "minimum": 0,
          "type": [
            "integer",
            "null"
          ]
        },
        "offset": {
          "minimum": 0,
          "type": [
            "integer",
            "null"
          ]
        },
        "parameters": {
          "type": "object"
        },
        "sql": {
          "type": "string"
        }
      },
      "required": [
        "sql"
      ],
      "type": "object"
    },
    "name": "snowflake.search_rows_sql",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "read",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "snowflake",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Update rows in an isolated benchmark Snowflake target table. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "columns": {
          "type": "object"
        },
        "table": {
          "type": "string"
        },
        "where": {
          "type": "string"
        }
      },
      "required": [
        "table",
        "where",
        "columns"
      ],
      "type": "object"
    },
    "name": "snowflake.update_rows",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "snowflake",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Upsert rows into an isolated benchmark Snowflake target table. Use when the task requires create-or-update behavior keyed by the match fields in the schema. Supply only grounded identifiers and values. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "key_columns": {},
        "rows": {
          "type": "array"
        },
        "table": {
          "type": "string"
        }
      },
      "required": [
        "table",
        "key_columns",
        "rows"
      ],
      "type": "object"
    },
    "name": "snowflake.upsert_rows_batch",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "snowflake",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use when the task requires create-or-update behavior keyed by the match fields in the schema. Supply only grounded identifiers and values."
    }
  },
  {
    "canonical_argument_rules": {
      "argument_shape": {
        "always": [
          "http_status_code",
          "response"
        ],
        "optional": [
          "response_headers"
        ]
      },
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden",
      "status_encoding": "http_status_code is a JSON string; use '200' only when the recipe declares no other status."
    },
    "description": "Controlled Workato API Platform return_response action. Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "http_status_code": {
          "type": "string"
        },
        "response": {},
        "response_headers": {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        }
      },
      "required": [
        "http_status_code"
      ],
      "type": "object"
    },
    "name": "workato_api_platform.return_response",
    "output_schema": {
      "properties": {
        "http_status_code": {
          "type": "string"
        },
        "ok": {
          "type": "boolean"
        },
        "response": {},
        "response_headers": {
          "additionalProperties": {
            "type": "string"
          },
          "type": "object"
        }
      },
      "required": [
        "ok",
        "http_status_code"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "behavior_notes": [
        "A successful return_response is inherently recipe-terminal regardless of HTTP status."
      ],
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "terminal_response",
      "mutates_external_state": false,
      "terminal_on_success": true
    },
    "usage": {
      "connector_family": "workato_api_platform",
      "operation": "terminal",
      "side_effect": true,
      "when_to_use": "Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Get a controlled Workato app recipe's details (deterministic seeded state). Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "recipe_id": {
          "type": "string"
        }
      },
      "required": [
        "recipe_id"
      ],
      "type": "object"
    },
    "name": "workato_app.get_recipe",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "read",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_app",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "List controlled Workato app jobs (deterministic seeded state). Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "recipe_id": {
          "type": "string"
        },
        "status": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "name": "workato_app.list_jobs",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "read",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_app",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Controlled Workato app recipe-lifecycle rerun_jobs action. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "job_ids": {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        "recipe_id": {
          "type": "string"
        }
      },
      "required": [
        "job_ids"
      ],
      "type": "object"
    },
    "name": "workato_app.rerun_jobs",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "lifecycle_transition",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_app",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Controlled Workato app recipe-lifecycle start_recipe action. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "recipe_id": {
          "type": "string"
        }
      },
      "required": [
        "recipe_id"
      ],
      "type": "object"
    },
    "name": "workato_app.start_recipe",
    "output_schema": {
      "properties": {
        "ok": {
          "type": "boolean"
        },
        "recipe_id": {
          "type": "string"
        }
      },
      "required": [
        "ok",
        "recipe_id"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "lifecycle_transition",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_app",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Controlled Workato app recipe-lifecycle stop_recipe action. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "recipe_id": {
          "type": "string"
        }
      },
      "required": [
        "recipe_id"
      ],
      "type": "object"
    },
    "name": "workato_app.stop_recipe",
    "output_schema": {
      "properties": {
        "ok": {
          "type": "boolean"
        },
        "recipe_id": {
          "type": "string"
        }
      },
      "required": [
        "ok",
        "recipe_id"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "lifecycle_transition",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_app",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Add a record to a controlled Workato data table. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "record": {
          "type": "object"
        },
        "record_id_field": {
          "type": "string"
        },
        "table_id": {
          "type": "string"
        }
      },
      "required": [
        "table_id",
        "record"
      ],
      "type": "object"
    },
    "name": "workato_db_table.add_record",
    "output_schema": {
      "properties": {
        "ok": {
          "type": "boolean"
        },
        "record": {
          "type": "object"
        }
      },
      "required": [
        "ok"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_db_table",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Delete a record from a controlled Workato data table. Destructive operation. Use only when deletion is explicitly required and the target is unambiguous. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "record_id": {},
        "table_id": {
          "type": "string"
        }
      },
      "required": [
        "table_id",
        "record_id"
      ],
      "type": "object"
    },
    "name": "workato_db_table.delete_record",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_db_table",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Destructive operation. Use only when deletion is explicitly required and the target is unambiguous."
    }
  },
  {
    "canonical_argument_rules": {
      "argument_shape": {
        "always": [
          "table_id",
          "filters"
        ],
        "optional": [
          "continuation_token",
          "limit",
          "order_by_field_id",
          "order_direction"
        ]
      },
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "filter_encoding": "Each filter is exactly {field_id, op, value}. Replace '-' with '_' in field_id. Lowercase op and canonicalize equals to eq. Encode istrue/isfalse as op='eq' with JSON boolean true/false. Preserve an explicitly configured value for isnull/isnotnull; use null only when no value was configured.",
      "modifier_encoding": "Omit editor defaults limit=100 and order_direction='asc' when order_by_field_id is absent. Retain a non-default limit as a JSON integer. When order_by_field_id is present, replace '-' with '_', include order_direction (default 'asc'), and retain an explicitly configured limit.",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Read records from a controlled Workato data table. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "continuation_token": {
          "type": "string"
        },
        "filters": {
          "items": {
            "properties": {
              "field_id": {
                "type": "string"
              },
              "op": {
                "enum": [
                  "eq",
                  "ne",
                  "gte",
                  "gt",
                  "lte",
                  "lt",
                  "starts_with",
                  "isnull",
                  "isnotnull"
                ],
                "type": "string"
              },
              "value": {}
            },
            "required": [
              "field_id",
              "op"
            ],
            "type": "object"
          },
          "type": "array"
        },
        "limit": {
          "type": "integer"
        },
        "order_by_field_id": {
          "type": "string"
        },
        "order_direction": {
          "enum": [
            "asc",
            "desc"
          ],
          "type": "string"
        },
        "table_id": {
          "type": "string"
        }
      },
      "required": [
        "table_id"
      ],
      "type": "object"
    },
    "name": "workato_db_table.get_records",
    "output_schema": {
      "properties": {
        "continuation_token": {
          "type": [
            "string",
            "number",
            "null"
          ]
        },
        "ok": {
          "type": "boolean"
        },
        "records": {
          "items": {
            "type": "object"
          },
          "type": "array"
        }
      },
      "required": [
        "ok",
        "records"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation",
      "filter_operator_semantics": {
        "eq": "Field value equals the supplied value.",
        "gt": "Field value is greater than the supplied value.",
        "gte": "Field value is greater than or equal to the supplied value.",
        "isnotnull": "Field is neither null nor empty. Any supplied value is retained in the call but ignored by this presence test.",
        "isnull": "Field is null or empty. Any supplied value is retained in the call but ignored by this presence test.",
        "lt": "Field value is less than the supplied value.",
        "lte": "Field value is less than or equal to the supplied value.",
        "ne": "Field value does not equal the supplied value.",
        "starts_with": "Field text starts with the supplied value."
      }
    },
    "side_effects": {
      "class": "read",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_db_table",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Search records in a controlled Workato data table. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "query": {
          "type": "string"
        },
        "table_id": {
          "type": "string"
        }
      },
      "required": [
        "table_id",
        "query"
      ],
      "type": "object"
    },
    "name": "workato_db_table.search_records",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "read",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_db_table",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Delete all records from a controlled Workato data table. Destructive operation. Use only when deletion is explicitly required and the target is unambiguous. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "table_id": {
          "type": "string"
        }
      },
      "required": [
        "table_id"
      ],
      "type": "object"
    },
    "name": "workato_db_table.truncate_table",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_db_table",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Destructive operation. Use only when deletion is explicitly required and the target is unambiguous."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Update a record in a controlled Workato data table. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "record": {
          "type": "object"
        },
        "record_id": {},
        "record_id_field": {
          "type": "string"
        },
        "table_id": {
          "type": "string"
        }
      },
      "required": [
        "table_id",
        "record_id",
        "record"
      ],
      "type": "object"
    },
    "name": "workato_db_table.update_record",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_db_table",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
    }
  },
  {
    "canonical_argument_rules": {
      "argument_shape": {
        "always": [
          "table_id",
          "primary_field_id",
          "record"
        ]
      },
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "field_encoding": "Replace '-' with '_' in primary_field_id and record keys.",
      "identity_encoding": "Use primary_field_id only. record_id and record_id_field are not aliases in the canonical upsert call.",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Create or update a record in a controlled Workato data table. Use when the task requires create-or-update behavior keyed by the match fields in the schema. Supply only grounded identifiers and values. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "primary_field_id": {
          "type": "string"
        },
        "record": {
          "type": "object"
        },
        "record_id": {},
        "record_id_field": {
          "type": "string"
        },
        "table_id": {
          "type": "string"
        }
      },
      "required": [
        "table_id",
        "record"
      ],
      "type": "object"
    },
    "name": "workato_db_table.upsert_record",
    "output_schema": {
      "properties": {
        "ok": {
          "type": "boolean"
        },
        "record": {
          "type": "object"
        }
      },
      "required": [
        "ok"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_db_table",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use when the task requires create-or-update behavior keyed by the match fields in the schema. Supply only grounded identifiers and values."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Controlled Workato Genie workflow_return_result action. Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "result": {}
      },
      "type": "object"
    },
    "name": "workato_genie.workflow_return_result",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_genie",
      "operation": "terminal",
      "side_effect": true,
      "when_to_use": "Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Controlled Workato pub/sub publish action. Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "message": {},
        "topic_id": {
          "type": "string"
        }
      },
      "required": [
        "topic_id",
        "message"
      ],
      "type": "object"
    },
    "name": "workato_pub_sub.publish_to_topic",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_pub_sub",
      "operation": "communication",
      "side_effect": true,
      "when_to_use": "Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Controlled Workato pub/sub batch publish action. Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "messages": {
          "type": "array"
        },
        "topic_id": {
          "type": "string"
        }
      },
      "required": [
        "topic_id",
        "messages"
      ],
      "type": "object"
    },
    "name": "workato_pub_sub.publish_to_topic_batch",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_pub_sub",
      "operation": "communication",
      "side_effect": true,
      "when_to_use": "Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Controlled Workato recipe-function return_result action. Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "result": {
          "type": "object"
        }
      },
      "required": [
        "result"
      ],
      "type": "object"
    },
    "name": "workato_recipe_function.return_result",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_recipe_function",
      "operation": "terminal",
      "side_effect": true,
      "when_to_use": "Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Append one item to the current accumulator and return the accumulated list. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "list_item": {}
      },
      "required": [
        "list_item"
      ],
      "type": "object"
    },
    "name": "workato_runtime.accumulate_list_items",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "recipe_local_state",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_runtime",
      "operation": "transform",
      "side_effect": false,
      "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
    }
  },
  {
    "canonical_argument_rules": {
      "argument_shape": {
        "always": [
          "name",
          "size"
        ]
      },
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden",
      "size_encoding": "size is one non-negative JSON integer. Numeric strings are not canonical; when the recipe creates a list from a source, size is the resolved source length."
    },
    "description": "Create an indexed list of the configured non-negative size. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "name": {
          "type": "string"
        },
        "size": {
          "minimum": 0,
          "type": "integer"
        }
      },
      "required": [
        "name",
        "size"
      ],
      "type": "object"
    },
    "name": "workato_runtime.create_list",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "recipe_local_state",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_runtime",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Declare a recipe list with an optional initial list_items array. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "list_item_schema_json": {
          "type": "string"
        },
        "list_items": {
          "type": "array"
        },
        "name": {
          "type": "string"
        }
      },
      "required": [
        "name"
      ],
      "type": "object"
    },
    "name": "workato_runtime.declare_list",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "recipe_local_state",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_runtime",
      "operation": "transform",
      "side_effect": false,
      "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Declare recipe variables and return their initial values. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "name": {
          "type": "string"
        },
        "value": {},
        "variables": {
          "type": "object"
        }
      },
      "type": "object"
    },
    "name": "workato_runtime.declare_variable",
    "output_schema": {
      "additionalProperties": true,
      "description": "An object containing each declared variable and its resolved value.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "recipe_local_state",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_runtime",
      "operation": "transform",
      "side_effect": false,
      "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Insert one item at the start or end of a recipe list. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "list_item": {},
        "location": {
          "type": "string"
        },
        "name": {
          "type": "string"
        }
      },
      "required": [
        "name",
        "list_item"
      ],
      "type": "object"
    },
    "name": "workato_runtime.insert_to_list",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "recipe_local_state",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_runtime",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Insert an array of items at the start or end of a recipe list. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "list_items": {
          "type": "array"
        },
        "location": {
          "type": "string"
        },
        "name": {
          "type": "string"
        }
      },
      "required": [
        "name",
        "list_items"
      ],
      "type": "object"
    },
    "name": "workato_runtime.insert_to_list_batch",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "recipe_local_state",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_runtime",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Write one deterministic runtime log message with an optional INFO, WARN, or ERROR severity and centralized-log visibility. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "log_level": {
          "enum": [
            "INFO",
            "WARN",
            "ERROR"
          ],
          "type": "string"
        },
        "message": {
          "type": "string"
        },
        "user_logs_enabled": {
          "type": "boolean"
        }
      },
      "required": [
        "message"
      ],
      "type": "object"
    },
    "name": "workato_runtime.log_message",
    "output_schema": {
      "properties": {
        "log_level": {
          "type": "string"
        },
        "message": {
          "type": "string"
        },
        "ok": {
          "type": "boolean"
        },
        "user_logs_enabled": {
          "type": "boolean"
        }
      },
      "required": [
        "ok",
        "message"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "recipe_local_state",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_runtime",
      "operation": "transform",
      "side_effect": false,
      "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Parse a JSON document into a structured value. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "document": {
          "type": [
            "string",
            "object",
            "array"
          ]
        }
      },
      "required": [
        "document"
      ],
      "type": "object"
    },
    "name": "workato_runtime.parse_json",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "recipe_local_state",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_runtime",
      "operation": "transform",
      "side_effect": false,
      "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Update recipe variables; pass variable fields alongside the configured name metadata. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "additionalProperties": true,
      "properties": {
        "input_mode": {
          "type": "string"
        },
        "name": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "name": "workato_runtime.update_variables",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "recipe_local_state",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_runtime",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Invoke a controlled callable recipe. The simulator returns the exact deterministic seeded reply for the supplied flow and request. Invoke a configured child service only when its result or side effect is required. The synchronous form returns a seeded reply; the asynchronous form returns only an acknowledgement. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "flow_id": {
          "type": "string"
        },
        "request": {}
      },
      "required": [
        "flow_id"
      ],
      "type": "object"
    },
    "name": "workato_service.call_service",
    "output_schema": {
      "properties": {
        "ok": {
          "type": "boolean"
        },
        "reply": {}
      },
      "required": [
        "ok"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_service",
      "operation": "operation",
      "side_effect": true,
      "when_to_use": "Invoke a configured child service only when its result or side effect is required. The synchronous form returns a seeded reply; the asynchronous form returns only an acknowledgement."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Controlled Workato async callable-recipe invocation; returns an ack only (no reply). Invoke a configured child service only when its result or side effect is required. The synchronous form returns a seeded reply; the asynchronous form returns only an acknowledgement. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "flow_id": {
          "type": "string"
        },
        "request": {}
      },
      "required": [
        "flow_id"
      ],
      "type": "object"
    },
    "name": "workato_service.call_service_async",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_service",
      "operation": "operation",
      "side_effect": true,
      "when_to_use": "Invoke a configured child service only when its result or side effect is required. The synchronous form returns a seeded reply; the asynchronous form returns only an acknowledgement."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Controlled Workato service (callable recipe) send_reply action. Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "message": {},
        "reply": {},
        "reply_type": {
          "type": "string"
        }
      },
      "required": [
        "reply_type"
      ],
      "type": "object"
    },
    "name": "workato_service.send_reply",
    "output_schema": {
      "properties": {
        "message": {},
        "ok": {
          "type": "boolean"
        },
        "reply": {},
        "reply_type": {
          "type": "string"
        }
      },
      "required": [
        "ok",
        "reply_type"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "external_write",
      "mutates_external_state": true,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_service",
      "operation": "terminal",
      "side_effect": true,
      "when_to_use": "Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Create the configured in-memory smart list and return its rows and columns. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "list_name": {
          "type": "string"
        }
      },
      "required": [
        "list_name"
      ],
      "type": "object"
    },
    "name": "workato_smart_list.create_list",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "recipe_local_state",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_smart_list",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Create the configured in-memory smart list from CSV columns. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "columns": {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        "list_name": {
          "type": "string"
        }
      },
      "required": [
        "list_name",
        "columns"
      ],
      "type": "object"
    },
    "name": "workato_smart_list.create_list_from_csv",
    "output_schema": {
      "additionalProperties": true,
      "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
      "type": "object"
    },
    "semantic_constraints": {
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "recipe_local_state",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_smart_list",
      "operation": "mutation",
      "side_effect": true,
      "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
    }
  },
  {
    "canonical_argument_rules": {
      "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
      "comparison": "exact_canonical_arguments",
      "object_key_order": "canonical_json_sorted_keys",
      "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
      "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
      "schema_version": "agentorch-canonical-argument-rules-v1",
      "semantic_rewrites": "forbidden"
    },
    "description": "Run the configured SQL statement over in-memory smart lists. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
    "error_schema": {
      "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
      "pattern": "^ERROR:",
      "type": "string"
    },
    "input_schema": {
      "properties": {
        "sql": {
          "type": "string"
        }
      },
      "required": [
        "sql"
      ],
      "type": "object"
    },
    "name": "workato_smart_list.query_list",
    "output_schema": {
      "properties": {
        "columns": {
          "type": "object"
        },
        "count": {
          "type": "integer"
        },
        "ok": {
          "type": "boolean"
        },
        "row_count": {
          "type": "integer"
        },
        "rows": {
          "items": {
            "type": "object"
          },
          "type": "array"
        }
      },
      "required": [
        "ok",
        "rows",
        "row_count",
        "count"
      ],
      "type": "object"
    },
    "semantic_constraints": {
      "behavior_notes": [
        "SQL doubled apostrophes inside quoted string literals are decoded to a single apostrophe when values are stored and returned."
      ],
      "error_delivery": "error_observation"
    },
    "side_effects": {
      "class": "recipe_local_state",
      "mutates_external_state": false,
      "terminal_on_success": false
    },
    "usage": {
      "connector_family": "workato_smart_list",
      "operation": "read",
      "side_effect": false,
      "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
    }
  }
]

## Symbolic value shapes
{"kind":"literal","value":<JSON>}
{"kind":"input_ref","path":["field"]}
{"kind":"output_ref","binding":"search_result","path":["records",0,"Id"]}
{"kind":"resource_ref","resource":"<public resource name/id>","path":[]}
{"kind":"loop_ref","binding":"item","path":["field"]}
{"kind":"error_ref","binding":"caught_error","path":["message"]}
{"kind":"expression","op":"<op>","args":[]}

Expression ops: ["add", "and", "array", "call_function", "call_method", "canonical_optional_integer", "coalesce", "concat", "contains", "count", "divide", "duration", "eq", "filter", "get", "get_dynamic", "gt", "gte", "if", "interpolate", "is_blank", "is_present", "join", "length", "lower", "lt", "lte", "map", "merge", "modulo", "multiply", "ne", "negate", "not", "object", "or", "path_exists", "pluck", "project", "range", "ruby_or", "salesforce_sobject", "schema_boolean", "slack_attachments", "slack_text", "sort_by", "subtract", "upper", "workato_add", "workato_clear", "workato_divide", "workato_now", "workato_skip", "workato_subtract", "workato_text", "workato_today", "workato_uuid"]. Use `object` with fields,
`array` with items, and `interpolate` with parts. `map`, `project`, and `filter`
require item_bind plus value or condition. `sort_by`/`pluck` use path;
`sort_by` may set direction to asc or desc.

Every `input_ref.path` is relative to the root of the displayed Public input
schema. Include a `request` path component only when `request` is actually a
property at that root; never add an implicit wrapper. Public execution
metadata, when available, appears under the explicit `execution_context`
property and is referenced with an input_ref such as
`["execution_context","recipe_url"]`; it is not a caught-error field.

## Node shapes
{"kind":"call","tool":"<tool>","arguments":{},"bind":"optional_result","purpose":"optional"}
{"kind":"transform","expression":<symbolic value>,"bind":"result"}
{"kind":"if","condition":<symbolic value>,"then":[],"else":[]}
{"kind":"foreach","items":<symbolic value>,"item_bind":"item","batch_size":<optional symbolic positive integer>,"body":[]}
{"kind":"repeat","body":[],"until":<symbolic value>}
{"kind":"try","error_bind":"caught_error","body":[],"catch":[]}
{"kind":"stop","arguments":{"stop_reason":<symbolic value>,"stop_with_error":<symbolic value>}}
{"kind":"return","value":<symbolic value>}

Do not include node IDs; the benchmark assigns them.
The top-level response is exactly {"plan":[]}.
```

</details>

## Complete Global View model output

The following is the model's complete raw response. It is shown exactly as
returned, including its original compact JSON formatting.

```json
{"plan":[{"kind":"call","tool":"workato_db_table.get_records","arguments":{"filters":[{"field_id":"e417aefa_9690_4edd_83c5_8e3f8749fc24","op":"eq","value":{"kind":"input_ref","path":["context","access_profile","id"]}},{"field_id":"9d00233f_dc89_4f40_b0f4_c2b6ee765ed2","op":"eq","value":{"kind":"input_ref","path":["request","workspace_user_id"]}},{"field_id":"73fd1e82_f4d2_48a9_8ff2_96713f5acd63","op":"eq","value":true}],"limit":1,"table_id":"7201"},"bind":"authorization_lookup","purpose":"Find an enabled workspace authorization record linking the caller's access profile to the requested workspace user"},{"kind":"if","condition":{"kind":"expression","op":"is_present","args":[{"kind":"output_ref","binding":"authorization_lookup","path":["records",0]}]},"then":[{"kind":"try","error_bind":"caught_error","body":[{"kind":"call","tool":"workato_db_table.get_records","arguments":{"filters":[{"field_id":"e3bdb7a7_3561_48c0_b600_c210f5d64bb7","op":"eq","value":true},{"field_id":"3c0b720b_bbe8_47de_a88d_96d759af819e","op":"gt","value":{"kind":"input_ref","path":["request","deprecated_since"]}}],"limit":200,"order_by_field_id":"3c0b720b_bbe8_47de_a88d_96d759af819e","order_direction":"asc","table_id":"7199"},"bind":"deprecated_versions","purpose":"Retrieve up to 200 deprecated package versions deprecated after the supplied timestamp, ordered earliest to latest"},{"kind":"call","tool":"workato_api_platform.return_response","arguments":{"http_status_code":"200","response":{"kind":"expression","op":"object","fields":{"deprecations":{"kind":"expression","op":"map","args":[{"kind":"output_ref","binding":"deprecated_versions","path":["records"]}],"item_bind":"version","value":{"kind":"expression","op":"object","fields":{"deprecated_at":{"kind":"loop_ref","binding":"version","path":["3c0b720b_bbe8_47de_a88d_96d759af819e"]},"id":{"kind":"loop_ref","binding":"version","path":["11fbe9a6_a16d_4d7e_86ea_afe42ec03005"]},"name":{"kind":"loop_ref","binding":"version","path":["cc31f2eb_b841_498c_bced_247d9dd78edb"]},"package_id":{"kind":"loop_ref","binding":"version","path":["622152c7_a09f_4d54_80f7_add539bee209"]},"package_name":{"kind":"loop_ref","binding":"version","path":["display_name"]}}}}}}},"purpose":"Return the 200 Success response with the bounded, chronologically ordered deprecations listing"}],"catch":[{"kind":"call","tool":"workato_api_platform.return_response","arguments":{"http_status_code":"400","response":{"kind":"expression","op":"object","fields":{"error":{"kind":"literal","value":"Unexpected Error"}}}},"purpose":"Return the handled 400 Failed response without retrying"}]}],"else":[{"kind":"call","tool":"workato_api_platform.return_response","arguments":{"http_status_code":"401","response":{"kind":"literal","value":null}},"purpose":"Return the 401 Unauthorized response with no body"}]},{"kind":"return","value":{"kind":"literal","value":null}}]}
```

## Complete Global View execution output

This is the complete per-instance `output` object, including the normalized
plan, grounded steps, trajectory, final state, and runtime diagnostics.

<details>
<summary>Complete Global View execution output</summary>

```json
{
  "failed_calls": 0,
  "final_answer": null,
  "final_snapshot": {
    "google_sheets": {
      "headers": [],
      "rows": [],
      "spreadsheet_id": "simulated-spreadsheet",
      "tab": "Sheet1",
      "values": [
        []
      ]
    },
    "lookup_table": {
      "tables": {}
    },
    "salesforce": {
      "records": []
    },
    "snowflake": {
      "tables": {}
    },
    "snowflake_live": {
      "physical_tables": {},
      "tables": {}
    },
    "workato_db_table": {
      "state_file": "<repo>/benchmark/outputs/full_eval/global-react-final-20260814/_state_root/rescore-claude-opus-5/_state/workato_db_tables/102467097/variant_00/tables.json",
      "tables": {
        "7199": [
          {
            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "rec_001",
            "3c0b720b_bbe8_47de_a88d_96d759af819e": "2026-01-01",
            "622152c7_a09f_4d54_80f7_add539bee209": {
              "display_name": "Bench display_name",
              "record_id": "Bench record_id"
            },
            "_created_by": "seed",
            "_row_id": 0,
            "cc31f2eb_b841_498c_bced_247d9dd78edb": "Acme Approval",
            "e3bdb7a7_3561_48c0_b600_c210f5d64bb7": true,
            "id": "0"
          }
        ],
        "7201": [
          {
            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "ws_000",
            "25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e": "Acme Workspace",
            "73fd1e82_f4d2_48a9_8ff2_96713f5acd63": true,
            "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2": "U12345678",
            "_created_by": "seed",
            "_row_id": 0,
            "e417aefa_9690_4edd_83c5_8e3f8749fc24": "10",
            "id": "0"
          }
        ]
      }
    }
  },
  "plan": [
    {
      "arguments": {
        "filters": {
          "items": [
            {
              "fields": {
                "field_id": {
                  "kind": "literal",
                  "value": "e417aefa_9690_4edd_83c5_8e3f8749fc24"
                },
                "op": {
                  "kind": "literal",
                  "value": "eq"
                },
                "value": {
                  "kind": "input_ref",
                  "path": [
                    "context",
                    "access_profile",
                    "id"
                  ]
                }
              },
              "kind": "expression",
              "op": "object"
            },
            {
              "fields": {
                "field_id": {
                  "kind": "literal",
                  "value": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2"
                },
                "op": {
                  "kind": "literal",
                  "value": "eq"
                },
                "value": {
                  "kind": "input_ref",
                  "path": [
                    "request",
                    "workspace_user_id"
                  ]
                }
              },
              "kind": "expression",
              "op": "object"
            },
            {
              "fields": {
                "field_id": {
                  "kind": "literal",
                  "value": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63"
                },
                "op": {
                  "kind": "literal",
                  "value": "eq"
                },
                "value": {
                  "kind": "literal",
                  "value": true
                }
              },
              "kind": "expression",
              "op": "object"
            }
          ],
          "kind": "expression",
          "op": "array"
        },
        "limit": {
          "kind": "literal",
          "value": 1
        },
        "table_id": {
          "kind": "literal",
          "value": "7201"
        }
      },
      "bind": "authorization_lookup",
      "id": "p1",
      "kind": "call",
      "purpose": "Find an enabled workspace authorization record linking the caller's access profile to the requested workspace user",
      "tool": "workato_db_table.get_records"
    },
    {
      "condition": {
        "args": [
          {
            "binding": "authorization_lookup",
            "kind": "output_ref",
            "path": [
              "records",
              0
            ]
          }
        ],
        "kind": "expression",
        "op": "is_present"
      },
      "else": [
        {
          "arguments": {
            "http_status_code": {
              "kind": "literal",
              "value": "401"
            },
            "response": {
              "kind": "literal",
              "value": null
            }
          },
          "id": "p7",
          "kind": "call",
          "purpose": "Return the 401 Unauthorized response with no body",
          "tool": "workato_api_platform.return_response"
        }
      ],
      "id": "p2",
      "kind": "if",
      "then": [
        {
          "body": [
            {
              "arguments": {
                "filters": {
                  "items": [
                    {
                      "fields": {
                        "field_id": {
                          "kind": "literal",
                          "value": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7"
                        },
                        "op": {
                          "kind": "literal",
                          "value": "eq"
                        },
                        "value": {
                          "kind": "literal",
                          "value": true
                        }
                      },
                      "kind": "expression",
                      "op": "object"
                    },
                    {
                      "fields": {
                        "field_id": {
                          "kind": "literal",
                          "value": "3c0b720b_bbe8_47de_a88d_96d759af819e"
                        },
                        "op": {
                          "kind": "literal",
                          "value": "gt"
                        },
                        "value": {
                          "kind": "input_ref",
                          "path": [
                            "request",
                            "deprecated_since"
                          ]
                        }
                      },
                      "kind": "expression",
                      "op": "object"
                    }
                  ],
                  "kind": "expression",
                  "op": "array"
                },
                "limit": {
                  "kind": "literal",
                  "value": 200
                },
                "order_by_field_id": {
                  "kind": "literal",
                  "value": "3c0b720b_bbe8_47de_a88d_96d759af819e"
                },
                "order_direction": {
                  "kind": "literal",
                  "value": "asc"
                },
                "table_id": {
                  "kind": "literal",
                  "value": "7199"
                }
              },
              "bind": "deprecated_versions",
              "id": "p4",
              "kind": "call",
              "purpose": "Retrieve up to 200 deprecated package versions deprecated after the supplied timestamp, ordered earliest to latest",
              "tool": "workato_db_table.get_records"
            },
            {
              "arguments": {
                "http_status_code": {
                  "kind": "literal",
                  "value": "200"
                },
                "response": {
                  "fields": {
                    "deprecations": {
                      "args": [
                        {
                          "binding": "deprecated_versions",
                          "kind": "output_ref",
                          "path": [
                            "records"
                          ]
                        }
                      ],
                      "item_bind": "version",
                      "kind": "expression",
                      "op": "map",
                      "value": {
                        "fields": {
                          "deprecated_at": {
                            "binding": "version",
                            "kind": "loop_ref",
                            "path": [
                              "3c0b720b_bbe8_47de_a88d_96d759af819e"
                            ]
                          },
                          "id": {
                            "binding": "version",
                            "kind": "loop_ref",
                            "path": [
                              "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
                            ]
                          },
                          "name": {
                            "binding": "version",
                            "kind": "loop_ref",
                            "path": [
                              "cc31f2eb_b841_498c_bced_247d9dd78edb"
                            ]
                          },
                          "package_id": {
                            "binding": "version",
                            "kind": "loop_ref",
                            "path": [
                              "622152c7_a09f_4d54_80f7_add539bee209"
                            ]
                          },
                          "package_name": {
                            "binding": "version",
                            "kind": "loop_ref",
                            "path": [
                              "display_name"
                            ]
                          }
                        },
                        "kind": "expression",
                        "op": "object"
                      }
                    }
                  },
                  "kind": "expression",
                  "op": "object"
                }
              },
              "id": "p5",
              "kind": "call",
              "purpose": "Return the 200 Success response with the bounded, chronologically ordered deprecations listing",
              "tool": "workato_api_platform.return_response"
            }
          ],
          "catch": [
            {
              "arguments": {
                "http_status_code": {
                  "kind": "literal",
                  "value": "400"
                },
                "response": {
                  "fields": {
                    "error": {
                      "kind": "literal",
                      "value": "Unexpected Error"
                    }
                  },
                  "kind": "expression",
                  "op": "object"
                }
              },
              "id": "p6",
              "kind": "call",
              "purpose": "Return the handled 400 Failed response without retrying",
              "tool": "workato_api_platform.return_response"
            }
          ],
          "error_bind": "caught_error",
          "id": "p3",
          "kind": "try"
        }
      ]
    },
    {
      "id": "p8",
      "kind": "return",
      "value": {
        "kind": "literal",
        "value": null
      }
    }
  ],
  "plan_fidelity": {
    "applicable": true,
    "condition_control_flow": {
      "actual_count": 11,
      "condition_bindings": {
        "actual_count": 1,
        "exact": false,
        "expected_count": 1,
        "f1": 0.0,
        "matched_count": 0,
        "precision": 0.0,
        "recall": 0.0
      },
      "exact": false,
      "expected_count": 10,
      "f1": 0.47619,
      "matched_count": 5,
      "node_structure": {
        "actual_count": 3,
        "exact": false,
        "expected_count": 2,
        "f1": 0.8,
        "matched_count": 2,
        "precision": 0.666667,
        "recall": 1.0
      },
      "placement_edges": {
        "actual_count": 7,
        "exact": false,
        "expected_count": 7,
        "f1": 0.428571,
        "matched_count": 3,
        "precision": 0.428571,
        "recall": 0.428571
      },
      "precision": 0.454545,
      "recall": 0.5
    },
    "partial_order": {
      "actual_count": 7,
      "exact": false,
      "expected_count": 10,
      "f1": 0.705882,
      "matched_count": 6,
      "precision": 0.857143,
      "recall": 0.6,
      "shared_call_count": 5
    },
    "plan_condition_control_flow_exact": false,
    "plan_condition_control_flow_f1": 0.47619,
    "plan_coverage": {
      "actual_count": 8,
      "exact": false,
      "expected_count": 7,
      "f1": 0.933333,
      "matched_count": 7,
      "precision": 0.875,
      "recall": 1.0
    },
    "plan_coverage_exact": false,
    "plan_coverage_recall": 1.0,
    "plan_fidelity_macro_f1": 0.730773,
    "plan_fidelity_pass": false,
    "plan_partial_order_exact": false,
    "plan_partial_order_f1": 0.705882,
    "plan_symbolic_arguments_exact": false,
    "plan_symbolic_arguments_f1": 0.538462,
    "plan_tool_selection_exact": true,
    "plan_tool_selection_f1": 1.0,
    "symbolic_arguments": {
      "actual_count": 13,
      "comparable_exact": false,
      "comparison_basis": "active_trace_public_adapter_keys_with_runtime_query_semantics",
      "exact": false,
      "excluded_uncomparable_bindings": [],
      "excluded_uncomparable_count": 0,
      "expected_count": 13,
      "f1": 0.538462,
      "matched_count": 7,
      "precision": 0.538462,
      "recall": 0.538462,
      "shared_call_count": 5
    },
    "tool_selection": {
      "actual_count": 5,
      "exact": true,
      "expected_count": 5,
      "extra_tools": [],
      "f1": 1.0,
      "matched_count": 5,
      "missing_tools": [],
      "precision": 1.0,
      "recall": 1.0
    }
  },
  "plan_versions": [
    [
      {
        "arguments": {
          "filters": {
            "items": [
              {
                "fields": {
                  "field_id": {
                    "kind": "literal",
                    "value": "e417aefa_9690_4edd_83c5_8e3f8749fc24"
                  },
                  "op": {
                    "kind": "literal",
                    "value": "eq"
                  },
                  "value": {
                    "kind": "input_ref",
                    "path": [
                      "context",
                      "access_profile",
                      "id"
                    ]
                  }
                },
                "kind": "expression",
                "op": "object"
              },
              {
                "fields": {
                  "field_id": {
                    "kind": "literal",
                    "value": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2"
                  },
                  "op": {
                    "kind": "literal",
                    "value": "eq"
                  },
                  "value": {
                    "kind": "input_ref",
                    "path": [
                      "request",
                      "workspace_user_id"
                    ]
                  }
                },
                "kind": "expression",
                "op": "object"
              },
              {
                "fields": {
                  "field_id": {
                    "kind": "literal",
                    "value": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63"
                  },
                  "op": {
                    "kind": "literal",
                    "value": "eq"
                  },
                  "value": {
                    "kind": "literal",
                    "value": true
                  }
                },
                "kind": "expression",
                "op": "object"
              }
            ],
            "kind": "expression",
            "op": "array"
          },
          "limit": {
            "kind": "literal",
            "value": 1
          },
          "table_id": {
            "kind": "literal",
            "value": "7201"
          }
        },
        "bind": "authorization_lookup",
        "id": "p1",
        "kind": "call",
        "purpose": "Find an enabled workspace authorization record linking the caller's access profile to the requested workspace user",
        "tool": "workato_db_table.get_records"
      },
      {
        "condition": {
          "args": [
            {
              "binding": "authorization_lookup",
              "kind": "output_ref",
              "path": [
                "records",
                0
              ]
            }
          ],
          "kind": "expression",
          "op": "is_present"
        },
        "else": [
          {
            "arguments": {
              "http_status_code": {
                "kind": "literal",
                "value": "401"
              },
              "response": {
                "kind": "literal",
                "value": null
              }
            },
            "id": "p7",
            "kind": "call",
            "purpose": "Return the 401 Unauthorized response with no body",
            "tool": "workato_api_platform.return_response"
          }
        ],
        "id": "p2",
        "kind": "if",
        "then": [
          {
            "body": [
              {
                "arguments": {
                  "filters": {
                    "items": [
                      {
                        "fields": {
                          "field_id": {
                            "kind": "literal",
                            "value": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7"
                          },
                          "op": {
                            "kind": "literal",
                            "value": "eq"
                          },
                          "value": {
                            "kind": "literal",
                            "value": true
                          }
                        },
                        "kind": "expression",
                        "op": "object"
                      },
                      {
                        "fields": {
                          "field_id": {
                            "kind": "literal",
                            "value": "3c0b720b_bbe8_47de_a88d_96d759af819e"
                          },
                          "op": {
                            "kind": "literal",
                            "value": "gt"
                          },
                          "value": {
                            "kind": "input_ref",
                            "path": [
                              "request",
                              "deprecated_since"
                            ]
                          }
                        },
                        "kind": "expression",
                        "op": "object"
                      }
                    ],
                    "kind": "expression",
                    "op": "array"
                  },
                  "limit": {
                    "kind": "literal",
                    "value": 200
                  },
                  "order_by_field_id": {
                    "kind": "literal",
                    "value": "3c0b720b_bbe8_47de_a88d_96d759af819e"
                  },
                  "order_direction": {
                    "kind": "literal",
                    "value": "asc"
                  },
                  "table_id": {
                    "kind": "literal",
                    "value": "7199"
                  }
                },
                "bind": "deprecated_versions",
                "id": "p4",
                "kind": "call",
                "purpose": "Retrieve up to 200 deprecated package versions deprecated after the supplied timestamp, ordered earliest to latest",
                "tool": "workato_db_table.get_records"
              },
              {
                "arguments": {
                  "http_status_code": {
                    "kind": "literal",
                    "value": "200"
                  },
                  "response": {
                    "fields": {
                      "deprecations": {
                        "args": [
                          {
                            "binding": "deprecated_versions",
                            "kind": "output_ref",
                            "path": [
                              "records"
                            ]
                          }
                        ],
                        "item_bind": "version",
                        "kind": "expression",
                        "op": "map",
                        "value": {
                          "fields": {
                            "deprecated_at": {
                              "binding": "version",
                              "kind": "loop_ref",
                              "path": [
                                "3c0b720b_bbe8_47de_a88d_96d759af819e"
                              ]
                            },
                            "id": {
                              "binding": "version",
                              "kind": "loop_ref",
                              "path": [
                                "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
                              ]
                            },
                            "name": {
                              "binding": "version",
                              "kind": "loop_ref",
                              "path": [
                                "cc31f2eb_b841_498c_bced_247d9dd78edb"
                              ]
                            },
                            "package_id": {
                              "binding": "version",
                              "kind": "loop_ref",
                              "path": [
                                "622152c7_a09f_4d54_80f7_add539bee209"
                              ]
                            },
                            "package_name": {
                              "binding": "version",
                              "kind": "loop_ref",
                              "path": [
                                "display_name"
                              ]
                            }
                          },
                          "kind": "expression",
                          "op": "object"
                        }
                      }
                    },
                    "kind": "expression",
                    "op": "object"
                  }
                },
                "id": "p5",
                "kind": "call",
                "purpose": "Return the 200 Success response with the bounded, chronologically ordered deprecations listing",
                "tool": "workato_api_platform.return_response"
              }
            ],
            "catch": [
              {
                "arguments": {
                  "http_status_code": {
                    "kind": "literal",
                    "value": "400"
                  },
                  "response": {
                    "fields": {
                      "error": {
                        "kind": "literal",
                        "value": "Unexpected Error"
                      }
                    },
                    "kind": "expression",
                    "op": "object"
                  }
                },
                "id": "p6",
                "kind": "call",
                "purpose": "Return the handled 400 Failed response without retrying",
                "tool": "workato_api_platform.return_response"
              }
            ],
            "error_bind": "caught_error",
            "id": "p3",
            "kind": "try"
          }
        ]
      },
      {
        "id": "p8",
        "kind": "return",
        "value": {
          "kind": "literal",
          "value": null
        }
      }
    ]
  ],
  "protocol_violations": 0,
  "replan_count": 0,
  "replan_events": [],
  "runtime_orchestration": {
    "condition_path_check_count": 1,
    "condition_path_checked": true,
    "condition_path_pass": true,
    "condition_path_passed_check_count": 1,
    "failed_read_attempt_count": 0,
    "failed_tool_attempt_count": 0,
    "orchestration_action_count_ratio": 1.0,
    "orchestration_efficiency_within_2x": true,
    "tool_argument_full_check_count": 3,
    "tool_argument_full_checked": true,
    "tool_argument_full_details": [
      {
        "agent_index": 0,
        "declared_execution_semantic_slots": [],
        "declared_result_semantic_slots": [],
        "declared_statement_semantic_slots": [],
        "gold_index": 0,
        "index": 0,
        "mode": "mismatch",
        "ok": false,
        "query_semantic_ok": false,
        "raw_ok": false,
        "required_mode": "raw_subset",
        "required_ok": true,
        "required_raw_ok": true,
        "semantic_mode": "raw_subset+mismatch",
        "semantic_ok": false,
        "semantic_required_mode": "raw_subset",
        "semantic_required_ok": true,
        "tool": "workato_db_table.get_records"
      },
      {
        "agent_index": 1,
        "declared_execution_semantic_slots": [],
        "declared_result_semantic_slots": [],
        "declared_statement_semantic_slots": [],
        "gold_index": 1,
        "index": 1,
        "mode": "canonical_exact",
        "ok": true,
        "query_semantic_ok": false,
        "raw_ok": true,
        "required_mode": "raw_subset",
        "required_ok": true,
        "required_raw_ok": true,
        "semantic_mode": "raw_exact",
        "semantic_ok": true,
        "semantic_required_mode": "raw_subset",
        "semantic_required_ok": true,
        "tool": "workato_db_table.get_records"
      },
      {
        "agent_index": 2,
        "declared_execution_semantic_slots": [],
        "declared_result_semantic_slots": [],
        "declared_statement_semantic_slots": [],
        "gold_index": 2,
        "index": 2,
        "mode": "mismatch",
        "ok": false,
        "query_semantic_ok": false,
        "raw_ok": false,
        "required_mode": "mismatch",
        "required_ok": false,
        "required_raw_ok": false,
        "semantic_mode": "mismatch+mismatch",
        "semantic_ok": false,
        "semantic_required_mode": "mismatch",
        "semantic_required_ok": false,
        "tool": "workato_api_platform.return_response"
      }
    ],
    "tool_argument_full_pass": false,
    "tool_argument_full_passed_check_count": 1,
    "tool_argument_full_raw_check_count": 3,
    "tool_argument_full_raw_checked": true,
    "tool_argument_full_raw_pass": false,
    "tool_argument_full_raw_passed_check_count": 1,
    "tool_argument_full_semantic_pass": false,
    "tool_argument_required_check_count": 3,
    "tool_argument_required_checked": true,
    "tool_argument_required_pass": false,
    "tool_argument_required_passed_check_count": 2,
    "tool_argument_required_raw_check_count": 3,
    "tool_argument_required_raw_checked": true,
    "tool_argument_required_raw_pass": false,
    "tool_argument_required_raw_passed_check_count": 2,
    "tool_argument_required_semantic_pass": false,
    "tool_execution_success_check_count": 3,
    "tool_execution_success_checked": true,
    "tool_execution_success_pass": true,
    "tool_execution_success_passed_check_count": 3,
    "tool_order_check_count": 1,
    "tool_order_checked": true,
    "tool_order_dependency_edge_count": 3,
    "tool_order_dependency_mode": "dependency_dag",
    "tool_order_dependency_pass": true,
    "tool_order_dependency_spec_hash": "0fb1a534e557aea4b0bf6e3bb97d7809ecbe38574947bc629cf8cb20fa13bee6",
    "tool_order_exact_pass": true,
    "tool_order_mapped_gold_call_count": 3,
    "tool_order_mode": "canonical_exact",
    "tool_order_multiple_topological_orders": false,
    "tool_order_pass": true,
    "tool_order_passed_check_count": 1,
    "tool_order_public_temporal_requirement_count": 0,
    "tool_order_violations": [],
    "tool_selection_check_count": 1,
    "tool_selection_checked": true,
    "tool_selection_exact_pass": true,
    "tool_selection_extra_read_count": 0,
    "tool_selection_extra_read_tools": [],
    "tool_selection_extra_write_count": 0,
    "tool_selection_extra_write_tools": [],
    "tool_selection_pass": true,
    "tool_selection_passed_check_count": 1,
    "tool_selection_required_multiset_pass": true,
    "tool_selection_semantic_pass": true,
    "tool_trace_exact_pass": true,
    "unexpected_failed_tool_attempt_count": 0,
    "unexpected_failed_tool_attempt_exact_count": 0
  },
  "steps": [
    {
      "action": {
        "args": {
          "filters": [
            {
              "field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
              "op": "eq",
              "value": "10"
            },
            {
              "field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
              "op": "eq",
              "value": "U12345678"
            },
            {
              "field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
              "op": "eq",
              "value": true
            }
          ],
          "limit": 1,
          "table_id": "7201"
        },
        "tool": "workato_db_table.get_records"
      },
      "observation": "{\"ok\": true, \"records\": [{\"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\": \"ws_000\", \"25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e\": \"Acme Workspace\", \"73fd1e82_f4d2_48a9_8ff2_96713f5acd63\": true, \"9d00233f_dc89_4f40_b0f4_c2b6ee765ed2\": \"U12345678\", \"_row_id\": 0, \"e417aefa_9690_4edd_83c5_8e3f8749fc24\": \"10\", \"id\": \"0\", \"_created_by\": \"seed\", \"record_id\": \"ws_000\"}]}",
      "plan_node_id": "p1"
    },
    {
      "branch": "then",
      "plan_node_id": "p2"
    },
    {
      "action": {
        "args": {
          "filters": [
            {
              "field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
              "op": "eq",
              "value": true
            },
            {
              "field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
              "op": "gt",
              "value": "2025-01-01"
            }
          ],
          "limit": 200,
          "order_by_field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
          "order_direction": "asc",
          "table_id": "7199"
        },
        "tool": "workato_db_table.get_records"
      },
      "observation": "{\"ok\": true, \"records\": [{\"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\": \"rec_001\", \"3c0b720b_bbe8_47de_a88d_96d759af819e\": \"2026-01-01\", \"622152c7_a09f_4d54_80f7_add539bee209\": {\"display_name\": \"Bench display_name\", \"record_id\": \"Bench record_id\"}, \"_row_id\": 0, \"cc31f2eb_b841_498c_bced_247d9dd78edb\": \"Acme Approval\", \"e3bdb7a7_3561_48c0_b600_c210f5d64bb7\": true, \"id\": \"0\", \"_created_by\": \"seed\", \"record_id\": \"rec_001\"}]}",
      "plan_node_id": "p4"
    },
    {
      "action": {
        "args": {
          "http_status_code": "200",
          "response": {
            "deprecations": [
              {
                "deprecated_at": "2026-01-01",
                "id": "rec_001",
                "name": "Acme Approval",
                "package_id": {
                  "display_name": "Bench display_name",
                  "record_id": "Bench record_id"
                },
                "package_name": null
              }
            ]
          }
        },
        "tool": "workato_api_platform.return_response"
      },
      "observation": "{\"ok\": true, \"http_status_code\": \"200\", \"response\": {\"deprecations\": [{\"deprecated_at\": \"2026-01-01\", \"id\": \"rec_001\", \"name\": \"Acme Approval\", \"package_id\": {\"display_name\": \"Bench display_name\", \"record_id\": \"Bench record_id\"}, \"package_name\": null}]}}",
      "plan_node_id": "p5"
    }
  ],
  "stop_reason": "terminal_tool",
  "trajectory": [
    {
      "args": {
        "filters": [
          {
            "field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
            "op": "eq",
            "value": "10"
          },
          {
            "field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
            "op": "eq",
            "value": "U12345678"
          },
          {
            "field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
            "op": "eq",
            "value": true
          }
        ],
        "limit": 1,
        "table_id": "7201"
      },
      "result": {
        "ok": true,
        "records": [
          {
            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "ws_000",
            "25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e": "Acme Workspace",
            "73fd1e82_f4d2_48a9_8ff2_96713f5acd63": true,
            "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2": "U12345678",
            "_created_by": "seed",
            "_row_id": 0,
            "e417aefa_9690_4edd_83c5_8e3f8749fc24": "10",
            "id": "0",
            "record_id": "ws_000"
          }
        ]
      },
      "tool": "workato_db_table.get_records"
    },
    {
      "args": {
        "filters": [
          {
            "field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
            "op": "eq",
            "value": true
          },
          {
            "field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
            "op": "gt",
            "value": "2025-01-01"
          }
        ],
        "limit": 200,
        "order_by_field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
        "order_direction": "asc",
        "table_id": "7199"
      },
      "result": {
        "ok": true,
        "records": [
          {
            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "rec_001",
            "3c0b720b_bbe8_47de_a88d_96d759af819e": "2026-01-01",
            "622152c7_a09f_4d54_80f7_add539bee209": {
              "display_name": "Bench display_name",
              "record_id": "Bench record_id"
            },
            "_created_by": "seed",
            "_row_id": 0,
            "cc31f2eb_b841_498c_bced_247d9dd78edb": "Acme Approval",
            "e3bdb7a7_3561_48c0_b600_c210f5d64bb7": true,
            "id": "0",
            "record_id": "rec_001"
          }
        ]
      },
      "tool": "workato_db_table.get_records"
    },
    {
      "args": {
        "http_status_code": "200",
        "response": {
          "deprecations": [
            {
              "deprecated_at": "2026-01-01",
              "id": "rec_001",
              "name": "Acme Approval",
              "package_id": {
                "display_name": "Bench display_name",
                "record_id": "Bench record_id"
              },
              "package_name": null
            }
          ]
        }
      },
      "result": {
        "http_status_code": "200",
        "ok": true,
        "response": {
          "deprecations": [
            {
              "deprecated_at": "2026-01-01",
              "id": "rec_001",
              "name": "Acme Approval",
              "package_id": {
                "display_name": "Bench display_name",
                "record_id": "Bench record_id"
              },
              "package_name": null
            }
          ]
        }
      },
      "tool": "workato_api_platform.return_response"
    }
  ]
}
```

</details>

## Complete ReAct input

### System message

<details>
<summary>Complete ReAct system message</summary>

```text
You are an automation agent. Complete the task using ONLY the tools below.

OBJECTIVE:
"The requirements below describe the desired behavior. Do not treat their\npresentation order as the execution order; determine the workflow from the\nrequirements, dependencies, and conditions.\n\nObjective\nProvide authorized callers with a bounded, chronologically ordered listing of package versions deprecated after a supplied timestamp.\n\nRequirements\n- For an authorized caller, return a 200 Success response containing up to 200 deprecated package versions, ordered from earliest to latest deprecation. Each deprecations item must contain the version ID, version name, associated package ID, associated package name, and deprecation timestamp.\n- A package version qualifies only when it is marked deprecated and its deprecation timestamp is strictly later than request.deprecated_since.\n- If protected deprecation retrieval or construction of the success response fails, do not retry; return a 400 Failed response whose error is exactly \"Unexpected Error\".\n- Create one deprecations item for every retrieved qualifying package-version record, preserving its version ID, version name, associated package ID, associated package name, and deprecation timestamp.\n- The 401 Unauthorized response, 200 Success response, and handled 400 Failed response each terminate processing.\n- If no enabled workspace authorization record links the caller's access profile to request.workspace_user_id, return a 401 Unauthorized response with no body; otherwise, provide the protected deprecation-listing response path."

INPUT CONTRACT:
[
 "The TRIGGER EVENT is the complete caller/event payload available for this run.",
 "The ENVIRONMENT and SCHEMA cards describe available state without revealing hidden row values."
]

COMPLETION CRITERIA:
[
 "Achieve every business effect and caller-visible response stated in the task description.",
 "Stop after the required final state or terminal response is complete."
]

CONSTRAINTS:
[
 "Choose tools from the broad workspace catalog; many are distractors.",
 "Ground every identifier and value in the task, trigger, schema, or a prior tool observation.",
 "Avoid speculative reads, unrelated mutations, and duplicate messages."
]

OUTPUT CONTRACT (interface documentation):
- Declared 200 body schema; delivery: explicit_tool_call: [{"label": "Deprecations", "name": "deprecations", "of": "object", "optional": false, "properties": [{"control_type": "text", "label": "ID", "name": "id", "optional": false, "type": "string"}, {"control_type": "text", "label": "Name", "name": "name", "optional": false, "type": "string"}, {"control_type": "text", "label": "Package ID", "name": "package_id", "optional": false, "type": "string"}, {"control_type": "text", "label": "Package name", "name": "package_name", "optional": false, "type": "string"}, {"control_type": "date_time", "label": "Deprecated at", "name": "deprecated_at", "optional": false, "parse_output": "date_time_conversion", "render_input": "date_time_conversion", "type": "date_time"}], "type": "array"}]
- Declared 400 body schema; delivery: explicit_tool_call: [{"control_type": "text", "label": "Error", "name": "error", "optional": false, "type": "string"}]
- Declared 401 body schema; delivery: explicit_tool_call: []

TOOLS:
[
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Replay a Workato clock wait interval without sleeping during benchmark execution. Advance the simulated clock only when the task explicitly requires waiting. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "interval": {
     "type": "string"
    }
   },
   "required": [
    "interval"
   ],
   "type": "object"
  },
  "name": "clock.wait_for_interval",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "clock",
   "operation": "operation",
   "side_effect": true,
   "when_to_use": "Advance the simulated clock only when the task explicitly requires waiting."
  }
 },
 {
  "canonical_argument_rules": {
   "argument_shape": {
    "always": [
     "parent_id",
     "name"
    ]
   },
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "parent_encoding": "Use parent_id only. folderId is connector-authoring input and is not a canonical benchmark argument alias.",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Create a folder in the in-process Google Drive simulator. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "folderId": {
     "type": "string"
    },
    "name": {
     "type": "string"
    },
    "parent_id": {
     "type": "string"
    }
   },
   "required": [
    "parent_id",
    "name"
   ],
   "type": "object"
  },
  "name": "google_drive.create_folder",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "google_drive",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Append one row to the simulated Google Sheet. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "data": {
     "type": "object"
    },
    "headers": {
     "type": "array"
    },
    "sheet": {
     "type": "string"
    },
    "spreadsheet": {
     "type": "string"
    }
   },
   "required": [
    "data"
   ],
   "type": "object"
  },
  "name": "google_sheets.add_spreadsheet_row_v4",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "google_sheets",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Retrieve rows from the simulated Google Sheet. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "range": {
     "type": "string"
    },
    "sheet": {
     "type": "string"
    },
    "spreadsheet": {
     "type": "string"
    }
   },
   "type": "object"
  },
  "name": "google_sheets.get_spreadsheet_rows_v4",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "read",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "google_sheets",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 },
 {
  "canonical_argument_rules": {
   "argument_shape": {
    "always": [
     "spreadsheet",
     "sheet",
     "data",
     "count"
    ]
   },
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "count_encoding": "count is a non-negative JSON integer when present and null when absent. Numeric strings are not canonical.",
   "filter_encoding": "data is the exact object of column-name equality filters; do not move a filter into a query string.",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Search rows in the simulated Google Sheet using exact column filters. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "count": {
     "minimum": 0,
     "type": [
      "integer",
      "null"
     ]
    },
    "data": {
     "type": "object"
    },
    "sheet": {
     "type": "string"
    },
    "spreadsheet": {
     "type": "string"
    }
   },
   "type": "object"
  },
  "name": "google_sheets.search_spreadsheet_rows_v4_new",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "read",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "google_sheets",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Update one row in the simulated Google Sheet. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "data": {
     "type": "object"
    },
    "row_number": {
     "type": "integer"
    },
    "sheet": {
     "type": "string"
    },
    "spreadsheet": {
     "type": "string"
    }
   },
   "required": [
    "row_number",
    "data"
   ],
   "type": "object"
  },
  "name": "google_sheets.update_row_v4_new",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "google_sheets",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
  }
 },
 {
  "canonical_argument_rules": {
   "argument_shape": {
    "always": [
     "project_issuetype",
     "summary",
     "description",
     "priority",
     "labels"
    ]
   },
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "optional_value_encoding": "All five canonical keys are present. Unconfigured optional text fields are empty strings and unconfigured labels is null.",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Create an issue in the in-process Jira simulator. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "required": [
    "project_issuetype",
    "summary"
   ],
   "type": "object"
  },
  "name": "jira.create_issue",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "jira",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Add a batch of entries to a controlled Workato lookup table. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "entries": {
     "items": {
      "type": "object"
     },
     "type": "array"
    },
    "lookup_table_id": {
     "type": "string"
    }
   },
   "required": [
    "lookup_table_id",
    "entries"
   ],
   "type": "object"
  },
  "name": "lookup_table.add_batch_of_entries",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "lookup_table",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Add an entry to a controlled Workato lookup table. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "lookup_table_id": {
     "type": "string"
    },
    "parameters": {
     "type": "object"
    }
   },
   "required": [
    "lookup_table_id",
    "parameters"
   ],
   "type": "object"
  },
  "name": "lookup_table.add_entry",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "lookup_table",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Delete an entry from a controlled Workato lookup table. Destructive operation. Use only when deletion is explicitly required and the target is unambiguous. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "id": {},
    "ignore_not_found": {},
    "lookup_table_id": {
     "type": "string"
    }
   },
   "required": [
    "lookup_table_id",
    "id"
   ],
   "type": "object"
  },
  "name": "lookup_table.delete_entry",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "lookup_table",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Destructive operation. Use only when deletion is explicitly required and the target is unambiguous."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Read entries from a controlled Workato lookup table. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "lookup_table_id": {
     "type": "string"
    }
   },
   "required": [
    "lookup_table_id"
   ],
   "type": "object"
  },
  "name": "lookup_table.get_entries",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "read",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "lookup_table",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Read one entry from a controlled Workato lookup table. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "id": {},
    "lookup_table_id": {
     "type": "string"
    },
    "parameters": {
     "type": "object"
    }
   },
   "required": [
    "lookup_table_id"
   ],
   "type": "object"
  },
  "name": "lookup_table.get_entry",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "read",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "lookup_table",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Search entries in a controlled Workato lookup table. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "lookup_table_id": {
     "type": "string"
    },
    "parameters": {
     "type": "object"
    }
   },
   "required": [
    "lookup_table_id",
    "parameters"
   ],
   "type": "object"
  },
  "name": "lookup_table.search_entries",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "read",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "lookup_table",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Delete all entries from a controlled Workato lookup table. Destructive operation. Use only when deletion is explicitly required and the target is unambiguous. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "lookup_table_id": {
     "type": "string"
    }
   },
   "required": [
    "lookup_table_id"
   ],
   "type": "object"
  },
  "name": "lookup_table.truncate",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "lookup_table",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Destructive operation. Use only when deletion is explicitly required and the target is unambiguous."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Update an entry in a controlled Workato lookup table. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "id": {},
    "lookup_table_id": {
     "type": "string"
    },
    "parameters": {
     "type": "object"
    }
   },
   "required": [
    "lookup_table_id",
    "id",
    "parameters"
   ],
   "type": "object"
  },
  "name": "lookup_table.update_entry",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "lookup_table",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Create a simulated Salesforce record. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. Connector selection concepts cross-checked against workato-recipe-skills/skills/salesforce-recipes; the simulator schema below is the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "fields": {
     "type": "object"
    },
    "sobject": {
     "type": "string"
    }
   },
   "required": [
    "sobject",
    "fields"
   ],
   "type": "object"
  },
  "name": "salesforce.create_record",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "salesforce",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
  }
 },
 {
  "canonical_argument_rules": {
   "argument_shape": {
    "always": [
     "sobject",
     "query"
    ],
    "optional": [
     "filters",
     "limit"
    ]
   },
   "boolean_encoding": "Equality-filter values use JSON booleans for boolean fields. Boolean tokens inside query remain query syntax.",
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_non_query_arguments_plus_query_semantics",
   "limit_encoding": "Limit placement is part of query semantics. If supplied as a connector field, its transport type is a non-negative JSON integer. Do not encode it as a numeric string.",
   "object_key_order": "canonical_json_sorted_keys",
   "query_comparison": "runtime_result_or_state_equivalence",
   "query_encoding": "SOQL spelling and structure are not compared directly. The Salesforce object stays exact and the executed selection must return the same business records on every variant.",
   "query_normalization": "No syntax normalization defines correctness; execute the connector and compare the selected row multiset.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "selection_mode": "SOQL text, equality filters, and a separate limit are one query surface. Alternative encodings are accepted only when the executed connector returns the same row multiset.",
   "semantic_rewrites": "query_surface_only"
  },
  "description": "Search simulated Salesforce records. Use exactly one mode: either a non-empty SOQL-style query with filters omitted, or query='' with simple equality filters containing only field and value. Never send both. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. Connector selection concepts cross-checked against workato-recipe-skills/skills/salesforce-recipes; the simulator schema below is the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "oneOf": [
    {
     "properties": {
      "filters": {
       "maxItems": 0,
       "type": "array"
      },
      "query": {
       "minLength": 1,
       "type": "string"
      }
     }
    },
    {
     "properties": {
      "filters": {
       "minItems": 1,
       "type": "array"
      },
      "query": {
       "const": ""
      }
     },
     "required": [
      "filters"
     ]
    }
   ],
   "properties": {
    "filters": {
     "items": {
      "additionalProperties": false,
      "properties": {
       "field": {
        "type": "string"
       },
       "value": {}
      },
      "required": [
       "field",
       "value"
      ],
      "type": "object"
     },
     "type": "array"
    },
    "limit": {
     "minimum": 0,
     "type": "integer"
    },
    "query": {
     "type": "string"
    },
    "sobject": {
     "type": "string"
    }
   },
   "required": [
    "sobject",
    "query"
   ],
   "type": "object"
  },
  "name": "salesforce.search_records",
  "output_schema": {
   "properties": {
    "count": {
     "type": "integer"
    },
    "ok": {
     "type": "boolean"
    },
    "records": {
     "items": {
      "type": "object"
     },
     "type": "array"
    }
   },
   "required": [
    "ok",
    "records",
    "count"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "read",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "salesforce",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 },
 {
  "canonical_argument_rules": {
   "argument_shape": {
    "batch": [
     "sobject",
     "records"
    ],
    "scalar": [
     "sobject",
     "id",
     "fields"
    ]
   },
   "batch_encoding": "A scalar record update uses exactly {sobject, id, fields}. An imported composite/batch update uses exactly {sobject, records}, where every records item is {sobject, id, fields}. Batch form is retained even when runtime expansion yields one item; cardinality never changes the argument shape.",
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "field_encoding": "fields contains only mapped Salesforce fields. Connector authoring metadata is omitted, and an absent optional value is omitted rather than encoded as null.",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Update a simulated Salesforce record. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. Connector selection concepts cross-checked against workato-recipe-skills/skills/salesforce-recipes; the simulator schema below is the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "oneOf": [
    {
     "required": [
      "sobject",
      "id",
      "fields"
     ]
    },
    {
     "required": [
      "sobject",
      "records"
     ]
    }
   ],
   "properties": {
    "fields": {
     "type": "object"
    },
    "id": {
     "type": "string"
    },
    "records": {
     "items": {
      "additionalProperties": false,
      "properties": {
       "fields": {
        "type": "object"
       },
       "id": {
        "type": "string"
       },
       "sobject": {
        "type": "string"
       }
      },
      "required": [
       "sobject",
       "id",
       "fields"
      ],
      "type": "object"
     },
     "type": "array"
    },
    "sobject": {
     "type": "string"
    }
   },
   "type": "object"
  },
  "name": "salesforce.update_record",
  "output_schema": {
   "properties": {
    "id": {
     "type": "string"
    },
    "ok": {
     "type": "boolean"
    }
   },
   "required": [
    "ok"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "salesforce",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Upsert a simulated Salesforce record by a primary key field. Use when the task requires create-or-update behavior keyed by the match fields in the schema. Supply only grounded identifiers and values. Connector selection concepts cross-checked against workato-recipe-skills/skills/salesforce-recipes; the simulator schema below is the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "fields": {
     "type": "object"
    },
    "key_field": {
     "type": "string"
    },
    "sobject": {
     "type": "string"
    }
   },
   "required": [
    "sobject",
    "key_field",
    "fields"
   ],
   "type": "object"
  },
  "name": "salesforce.upsert_record",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "salesforce",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use when the task requires create-or-update behavior keyed by the match fields in the schema. Supply only grounded identifiers and values."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Delete a simulated Slack message by channel and timestamp. Destructive operation. Use only when deletion is explicitly required and the target is unambiguous. Native Slack versus interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "channel": {
     "type": "string"
    },
    "ts": {
     "type": "string"
    }
   },
   "required": [
    "channel",
    "ts"
   ],
   "type": "object"
  },
  "name": "slack.delete_message",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "slack",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Destructive operation. Use only when deletion is explicitly required and the target is unambiguous."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Post a message to the in-process Slack simulator. Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends. Native Slack versus interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "attachments": {
     "items": {
      "additionalProperties": false,
      "properties": {
       "actions": {
        "type": "array"
       },
       "color": {
        "type": "string"
       },
       "fields": {
        "items": {
         "additionalProperties": false,
         "properties": {
          "short": {
           "type": "boolean"
          },
          "title": {
           "type": "string"
          },
          "value": {
           "type": "string"
          }
         },
         "required": [
          "title",
          "value"
         ],
         "type": "object"
        },
        "type": "array"
       },
       "footer": {
        "type": "string"
       },
       "footer_icon": {
        "type": "string"
       },
       "pretext": {
        "type": "string"
       },
       "text": {
        "type": "string"
       },
       "title": {
        "type": "string"
       },
       "title_link": {
        "type": "string"
       }
      },
      "type": "object"
     },
     "type": "array"
    },
    "blocks": {
     "type": "array"
    },
    "channel": {
     "type": "string"
    },
    "text": {
     "type": "string"
    },
    "thread_ts": {
     "type": "string"
    },
    "ts": {
     "type": "string"
    }
   },
   "required": [
    "channel",
    "text"
   ],
   "type": "object"
  },
  "name": "slack.post_message",
  "output_schema": {
   "properties": {
    "channel": {
     "type": "string"
    },
    "message": {
     "type": "object"
    },
    "ok": {
     "type": "boolean"
    },
    "thread_ts": {
     "type": "string"
    },
    "ts": {
     "type": "string"
    }
   },
   "required": [
    "ok"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "communication",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "slack",
   "operation": "communication",
   "side_effect": true,
   "when_to_use": "Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "invoking_context_encoding": "The invoking channel, thread timestamp, user, and original timestamp are connector-injected transport context and are omitted from the canonical request. Omit false optional mode flags; include ephemeral, replace_original, or delete_original only when true. Destination correctness is still checked from the resulting Slack side effect.",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Reply to the invoking Slack bot-command conversation, or to an explicit channel/thread when supplied. Omitting channel uses the invoking conversation routed through benchmark isolation. The reply may contain text, Block Kit blocks, or both; it may be requester-only, replace the original command response, or delete the original while posting the reply when those modes are set. Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends. Native Slack versus interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "blocks": {
     "items": {
      "type": "object"
     },
     "type": "array"
    },
    "channel": {
     "type": "string"
    },
    "delete_original": {
     "type": "boolean"
    },
    "ephemeral": {
     "type": "boolean"
    },
    "original_ts": {
     "type": "string"
    },
    "replace_original": {
     "type": "boolean"
    },
    "text": {
     "type": "string"
    },
    "thread_ts": {
     "type": "string"
    },
    "user": {
     "type": "string"
    }
   },
   "type": "object"
  },
  "name": "slack.post_reply",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "communication",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "slack",
   "operation": "communication",
   "side_effect": true,
   "when_to_use": "Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Update a simulated Slack message by replacing or removing Block Kit blocks with matching block IDs. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. Native Slack versus interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "blocks_to_update": {
     "type": "array"
    },
    "message_json": {}
   },
   "required": [
    "message_json",
    "blocks_to_update"
   ],
   "type": "object"
  },
  "name": "slack.update_blocks_by_block_id",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "slack",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Open a Slack modal in the simulator. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. Interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "trigger_id": {
     "type": "string"
    },
    "view": {
     "type": "object"
    }
   },
   "required": [
    "trigger_id",
    "view"
   ],
   "type": "object"
  },
  "name": "slack_bot.block_kit_modals",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "slack_bot",
   "operation": "transform",
   "side_effect": false,
   "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Return dynamic menu options for a Slack trigger payload. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. Interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "options": {
     "items": {
      "additionalProperties": false,
      "properties": {
       "label": {
        "type": "string"
       },
       "value": {
        "type": "string"
       }
      },
      "required": [
       "label",
       "value"
      ],
      "type": "object"
     },
     "type": "array"
    }
   },
   "required": [
    "options"
   ],
   "type": "object"
  },
  "name": "slack_bot.generate_menu_options",
  "output_schema": {
   "properties": {
    "ok": {
     "type": "boolean"
    },
    "options": {
     "type": "array"
    }
   },
   "required": [
    "ok",
    "options"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "slack_bot",
   "operation": "transform",
   "side_effect": false,
   "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Look up a deterministic simulated Slack user by email or id. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. Interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "email": {
     "type": "string"
    },
    "id": {
     "type": "string"
    }
   },
   "type": "object"
  },
  "name": "slack_bot.get_user_by_email",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "read",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "slack_bot",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Publish a Slack App Home view in the simulator. Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends. Interactive Workbot usage cross-checked against workato-recipe-skills/skills/slack-recipes; the simulator schema below is the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "user_id": {
     "type": "string"
    },
    "view": {
     "type": "object"
    }
   },
   "required": [
    "user_id",
    "view"
   ],
   "type": "object"
  },
  "name": "slack_bot.open_bot_app_home",
  "output_schema": {
   "properties": {
    "ok": {
     "type": "boolean"
    }
   },
   "required": [
    "ok"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "slack_bot",
   "operation": "communication",
   "side_effect": true,
   "when_to_use": "Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends."
  }
 },
 {
  "canonical_argument_rules": {
   "argument_shape": {
    "always": [
     "sql",
     "parameters"
    ]
   },
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_non_query_arguments_plus_query_semantics",
   "object_key_order": "canonical_json_sorted_keys",
   "parameter_encoding": "parameters is exactly the configured parameters.data object, or {} when absent.",
   "query_comparison": "runtime_result_or_state_equivalence",
   "query_encoding": "SQL spelling and structure are not compared directly. Reads must return the same row multiset; mutating statements must leave the same Snowflake table state on every variant.",
   "query_normalization": "No syntax normalization defines correctness; execute reads and compare row multisets, or execute writes and compare the final Snowflake table state.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "query_surface_only"
  },
  "description": "Run constrained Snowflake SQL against isolated benchmark state. Supports SELECT, INSERT INTO ... SELECT, ALTER TABLE ... ADD, COPY INTO from a declared stage, retention DELETE, TRUNCATE TABLE, and CREATE OR REPLACE TABLE AS SELECT within the documented simulator SQL subset. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "limit": {},
    "offset": {},
    "parameters": {
     "type": "object"
    },
    "sql": {
     "type": "string"
    }
   },
   "required": [
    "sql"
   ],
   "type": "object"
  },
  "name": "snowflake.run_custom_sql",
  "output_schema": {
   "properties": {
    "ok": {
     "type": "boolean"
    },
    "row_count": {
     "type": "integer"
    },
    "rows": {
     "items": {
      "type": "object"
     },
     "type": "array"
    },
    "rows_affected": {
     "type": "integer"
    }
   },
   "required": [
    "ok",
    "rows",
    "rows_affected"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "snowflake",
   "operation": "transform",
   "side_effect": false,
   "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
  }
 },
 {
  "canonical_argument_rules": {
   "argument_shape": {
    "always": [
     "table",
     "where",
     "parameters",
     "limit",
     "offset",
     "orderby",
     "output_columns"
    ]
   },
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "pagination_encoding": "limit and offset are JSON integers when present and null when absent. Numeric strings are not canonical.",
   "parameter_encoding": "parameters is exactly the configured parameters.data object, or {} when absent.",
   "query_encoding": "where, orderby, and output_columns remain separate fields; do not replace this structured call with SQL text.",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Search rows in an isolated benchmark Snowflake table state. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "limit": {
     "minimum": 0,
     "type": [
      "integer",
      "null"
     ]
    },
    "offset": {
     "minimum": 0,
     "type": [
      "integer",
      "null"
     ]
    },
    "orderby": {
     "type": "string"
    },
    "output_columns": {
     "description": "Optional projection of returned fields. Accepts a newline- or comma-separated field list.",
     "type": "string"
    },
    "parameters": {
     "type": "object"
    },
    "table": {
     "type": "string"
    },
    "where": {
     "type": "string"
    }
   },
   "required": [
    "table"
   ],
   "type": "object"
  },
  "name": "snowflake.search_rows",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "read",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "snowflake",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 },
 {
  "canonical_argument_rules": {
   "argument_shape": {
    "always": [
     "sql",
     "parameters",
     "limit",
     "offset"
    ]
   },
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_non_query_arguments_plus_query_semantics",
   "object_key_order": "canonical_json_sorted_keys",
   "pagination_encoding": "limit and offset are JSON integers when present and null when absent. Numeric strings are not canonical.",
   "parameter_encoding": "parameters is exactly the configured parameters.data object, or {} when absent.",
   "query_comparison": "runtime_result_or_state_equivalence",
   "query_encoding": "SQL spelling and structure are not compared directly. The executed read must return the same row multiset on every variant; parameters and pagination participate in that query result semantics.",
   "query_normalization": "No syntax normalization defines correctness; execute the connector and compare the selected row multiset.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "query_surface_only"
  },
  "description": "Run a constrained SELECT query against isolated benchmark Snowflake table state. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "limit": {
     "minimum": 0,
     "type": [
      "integer",
      "null"
     ]
    },
    "offset": {
     "minimum": 0,
     "type": [
      "integer",
      "null"
     ]
    },
    "parameters": {
     "type": "object"
    },
    "sql": {
     "type": "string"
    }
   },
   "required": [
    "sql"
   ],
   "type": "object"
  },
  "name": "snowflake.search_rows_sql",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "read",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "snowflake",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Update rows in an isolated benchmark Snowflake target table. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "columns": {
     "type": "object"
    },
    "table": {
     "type": "string"
    },
    "where": {
     "type": "string"
    }
   },
   "required": [
    "table",
    "where",
    "columns"
   ],
   "type": "object"
  },
  "name": "snowflake.update_rows",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "snowflake",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Upsert rows into an isolated benchmark Snowflake target table. Use when the task requires create-or-update behavior keyed by the match fields in the schema. Supply only grounded identifiers and values. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "key_columns": {},
    "rows": {
     "type": "array"
    },
    "table": {
     "type": "string"
    }
   },
   "required": [
    "table",
    "key_columns",
    "rows"
   ],
   "type": "object"
  },
  "name": "snowflake.upsert_rows_batch",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "snowflake",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use when the task requires create-or-update behavior keyed by the match fields in the schema. Supply only grounded identifiers and values."
  }
 },
 {
  "canonical_argument_rules": {
   "argument_shape": {
    "always": [
     "http_status_code",
     "response"
    ],
    "optional": [
     "response_headers"
    ]
   },
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden",
   "status_encoding": "http_status_code is a JSON string; use '200' only when the recipe declares no other status."
  },
  "description": "Controlled Workato API Platform return_response action. Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "http_status_code": {
     "type": "string"
    },
    "response": {},
    "response_headers": {
     "additionalProperties": {
      "type": "string"
     },
     "type": "object"
    }
   },
   "required": [
    "http_status_code"
   ],
   "type": "object"
  },
  "name": "workato_api_platform.return_response",
  "output_schema": {
   "properties": {
    "http_status_code": {
     "type": "string"
    },
    "ok": {
     "type": "boolean"
    },
    "response": {},
    "response_headers": {
     "additionalProperties": {
      "type": "string"
     },
     "type": "object"
    }
   },
   "required": [
    "ok",
    "http_status_code"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "behavior_notes": [
    "A successful return_response is inherently recipe-terminal regardless of HTTP status."
   ],
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "terminal_response",
   "mutates_external_state": false,
   "terminal_on_success": true
  },
  "usage": {
   "connector_family": "workato_api_platform",
   "operation": "terminal",
   "side_effect": true,
   "when_to_use": "Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Get a controlled Workato app recipe's details (deterministic seeded state). Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "recipe_id": {
     "type": "string"
    }
   },
   "required": [
    "recipe_id"
   ],
   "type": "object"
  },
  "name": "workato_app.get_recipe",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "read",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_app",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "List controlled Workato app jobs (deterministic seeded state). Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "recipe_id": {
     "type": "string"
    },
    "status": {
     "type": "string"
    }
   },
   "type": "object"
  },
  "name": "workato_app.list_jobs",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "read",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_app",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Controlled Workato app recipe-lifecycle rerun_jobs action. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "job_ids": {
     "items": {
      "type": "string"
     },
     "type": "array"
    },
    "recipe_id": {
     "type": "string"
    }
   },
   "required": [
    "job_ids"
   ],
   "type": "object"
  },
  "name": "workato_app.rerun_jobs",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "lifecycle_transition",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_app",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Controlled Workato app recipe-lifecycle start_recipe action. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "recipe_id": {
     "type": "string"
    }
   },
   "required": [
    "recipe_id"
   ],
   "type": "object"
  },
  "name": "workato_app.start_recipe",
  "output_schema": {
   "properties": {
    "ok": {
     "type": "boolean"
    },
    "recipe_id": {
     "type": "string"
    }
   },
   "required": [
    "ok",
    "recipe_id"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "lifecycle_transition",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_app",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Controlled Workato app recipe-lifecycle stop_recipe action. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "recipe_id": {
     "type": "string"
    }
   },
   "required": [
    "recipe_id"
   ],
   "type": "object"
  },
  "name": "workato_app.stop_recipe",
  "output_schema": {
   "properties": {
    "ok": {
     "type": "boolean"
    },
    "recipe_id": {
     "type": "string"
    }
   },
   "required": [
    "ok",
    "recipe_id"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "lifecycle_transition",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_app",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Add a record to a controlled Workato data table. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "record": {
     "type": "object"
    },
    "record_id_field": {
     "type": "string"
    },
    "table_id": {
     "type": "string"
    }
   },
   "required": [
    "table_id",
    "record"
   ],
   "type": "object"
  },
  "name": "workato_db_table.add_record",
  "output_schema": {
   "properties": {
    "ok": {
     "type": "boolean"
    },
    "record": {
     "type": "object"
    }
   },
   "required": [
    "ok"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_db_table",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Delete a record from a controlled Workato data table. Destructive operation. Use only when deletion is explicitly required and the target is unambiguous. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "record_id": {},
    "table_id": {
     "type": "string"
    }
   },
   "required": [
    "table_id",
    "record_id"
   ],
   "type": "object"
  },
  "name": "workato_db_table.delete_record",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_db_table",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Destructive operation. Use only when deletion is explicitly required and the target is unambiguous."
  }
 },
 {
  "canonical_argument_rules": {
   "argument_shape": {
    "always": [
     "table_id",
     "filters"
    ],
    "optional": [
     "continuation_token",
     "limit",
     "order_by_field_id",
     "order_direction"
    ]
   },
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "filter_encoding": "Each filter is exactly {field_id, op, value}. Replace '-' with '_' in field_id. Lowercase op and canonicalize equals to eq. Encode istrue/isfalse as op='eq' with JSON boolean true/false. Preserve an explicitly configured value for isnull/isnotnull; use null only when no value was configured.",
   "modifier_encoding": "Omit editor defaults limit=100 and order_direction='asc' when order_by_field_id is absent. Retain a non-default limit as a JSON integer. When order_by_field_id is present, replace '-' with '_', include order_direction (default 'asc'), and retain an explicitly configured limit.",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Read records from a controlled Workato data table. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "continuation_token": {
     "type": "string"
    },
    "filters": {
     "items": {
      "properties": {
       "field_id": {
        "type": "string"
       },
       "op": {
        "enum": [
         "eq",
         "ne",
         "gte",
         "gt",
         "lte",
         "lt",
         "starts_with",
         "isnull",
         "isnotnull"
        ],
        "type": "string"
       },
       "value": {}
      },
      "required": [
       "field_id",
       "op"
      ],
      "type": "object"
     },
     "type": "array"
    },
    "limit": {
     "type": "integer"
    },
    "order_by_field_id": {
     "type": "string"
    },
    "order_direction": {
     "enum": [
      "asc",
      "desc"
     ],
     "type": "string"
    },
    "table_id": {
     "type": "string"
    }
   },
   "required": [
    "table_id"
   ],
   "type": "object"
  },
  "name": "workato_db_table.get_records",
  "output_schema": {
   "properties": {
    "continuation_token": {
     "type": [
      "string",
      "number",
      "null"
     ]
    },
    "ok": {
     "type": "boolean"
    },
    "records": {
     "items": {
      "type": "object"
     },
     "type": "array"
    }
   },
   "required": [
    "ok",
    "records"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation",
   "filter_operator_semantics": {
    "eq": "Field value equals the supplied value.",
    "gt": "Field value is greater than the supplied value.",
    "gte": "Field value is greater than or equal to the supplied value.",
    "isnotnull": "Field is neither null nor empty. Any supplied value is retained in the call but ignored by this presence test.",
    "isnull": "Field is null or empty. Any supplied value is retained in the call but ignored by this presence test.",
    "lt": "Field value is less than the supplied value.",
    "lte": "Field value is less than or equal to the supplied value.",
    "ne": "Field value does not equal the supplied value.",
    "starts_with": "Field text starts with the supplied value."
   }
  },
  "side_effects": {
   "class": "read",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_db_table",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Search records in a controlled Workato data table. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "query": {
     "type": "string"
    },
    "table_id": {
     "type": "string"
    }
   },
   "required": [
    "table_id",
    "query"
   ],
   "type": "object"
  },
  "name": "workato_db_table.search_records",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "read",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_db_table",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Delete all records from a controlled Workato data table. Destructive operation. Use only when deletion is explicitly required and the target is unambiguous. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "table_id": {
     "type": "string"
    }
   },
   "required": [
    "table_id"
   ],
   "type": "object"
  },
  "name": "workato_db_table.truncate_table",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_db_table",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Destructive operation. Use only when deletion is explicitly required and the target is unambiguous."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Update a record in a controlled Workato data table. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "record": {
     "type": "object"
    },
    "record_id": {},
    "record_id_field": {
     "type": "string"
    },
    "table_id": {
     "type": "string"
    }
   },
   "required": [
    "table_id",
    "record_id",
    "record"
   ],
   "type": "object"
  },
  "name": "workato_db_table.update_record",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_db_table",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
  }
 },
 {
  "canonical_argument_rules": {
   "argument_shape": {
    "always": [
     "table_id",
     "primary_field_id",
     "record"
    ]
   },
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "field_encoding": "Replace '-' with '_' in primary_field_id and record keys.",
   "identity_encoding": "Use primary_field_id only. record_id and record_id_field are not aliases in the canonical upsert call.",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Create or update a record in a controlled Workato data table. Use when the task requires create-or-update behavior keyed by the match fields in the schema. Supply only grounded identifiers and values. Data-table read/write concepts cross-checked against workato-recipe-skills/skills/datatable-recipes; table and column identifiers must follow the simulator schema/environment cards.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "primary_field_id": {
     "type": "string"
    },
    "record": {
     "type": "object"
    },
    "record_id": {},
    "record_id_field": {
     "type": "string"
    },
    "table_id": {
     "type": "string"
    }
   },
   "required": [
    "table_id",
    "record"
   ],
   "type": "object"
  },
  "name": "workato_db_table.upsert_record",
  "output_schema": {
   "properties": {
    "ok": {
     "type": "boolean"
    },
    "record": {
     "type": "object"
    }
   },
   "required": [
    "ok"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_db_table",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use when the task requires create-or-update behavior keyed by the match fields in the schema. Supply only grounded identifiers and values."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Controlled Workato Genie workflow_return_result action. Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "result": {}
   },
   "type": "object"
  },
  "name": "workato_genie.workflow_return_result",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_genie",
   "operation": "terminal",
   "side_effect": true,
   "when_to_use": "Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Controlled Workato pub/sub publish action. Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "message": {},
    "topic_id": {
     "type": "string"
    }
   },
   "required": [
    "topic_id",
    "message"
   ],
   "type": "object"
  },
  "name": "workato_pub_sub.publish_to_topic",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_pub_sub",
   "operation": "communication",
   "side_effect": true,
   "when_to_use": "Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Controlled Workato pub/sub batch publish action. Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "messages": {
     "type": "array"
    },
    "topic_id": {
     "type": "string"
    }
   },
   "required": [
    "topic_id",
    "messages"
   ],
   "type": "object"
  },
  "name": "workato_pub_sub.publish_to_topic_batch",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_pub_sub",
   "operation": "communication",
   "side_effect": true,
   "when_to_use": "Produces a user-visible message, publication, view, or dialog. Resolve the destination and content first; avoid duplicate sends."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Controlled Workato recipe-function return_result action. Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "result": {
     "type": "object"
    }
   },
   "required": [
    "result"
   ],
   "type": "object"
  },
  "name": "workato_recipe_function.return_result",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_recipe_function",
   "operation": "terminal",
   "side_effect": true,
   "when_to_use": "Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Append one item to the current accumulator and return the accumulated list. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "list_item": {}
   },
   "required": [
    "list_item"
   ],
   "type": "object"
  },
  "name": "workato_runtime.accumulate_list_items",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "recipe_local_state",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_runtime",
   "operation": "transform",
   "side_effect": false,
   "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
  }
 },
 {
  "canonical_argument_rules": {
   "argument_shape": {
    "always": [
     "name",
     "size"
    ]
   },
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden",
   "size_encoding": "size is one non-negative JSON integer. Numeric strings are not canonical; when the recipe creates a list from a source, size is the resolved source length."
  },
  "description": "Create an indexed list of the configured non-negative size. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "name": {
     "type": "string"
    },
    "size": {
     "minimum": 0,
     "type": "integer"
    }
   },
   "required": [
    "name",
    "size"
   ],
   "type": "object"
  },
  "name": "workato_runtime.create_list",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "recipe_local_state",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_runtime",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Declare a recipe list with an optional initial list_items array. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "list_item_schema_json": {
     "type": "string"
    },
    "list_items": {
     "type": "array"
    },
    "name": {
     "type": "string"
    }
   },
   "required": [
    "name"
   ],
   "type": "object"
  },
  "name": "workato_runtime.declare_list",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "recipe_local_state",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_runtime",
   "operation": "transform",
   "side_effect": false,
   "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Declare recipe variables and return their initial values. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "name": {
     "type": "string"
    },
    "value": {},
    "variables": {
     "type": "object"
    }
   },
   "type": "object"
  },
  "name": "workato_runtime.declare_variable",
  "output_schema": {
   "additionalProperties": true,
   "description": "An object containing each declared variable and its resolved value.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "recipe_local_state",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_runtime",
   "operation": "transform",
   "side_effect": false,
   "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Insert one item at the start or end of a recipe list. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "list_item": {},
    "location": {
     "type": "string"
    },
    "name": {
     "type": "string"
    }
   },
   "required": [
    "name",
    "list_item"
   ],
   "type": "object"
  },
  "name": "workato_runtime.insert_to_list",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "recipe_local_state",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_runtime",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Insert an array of items at the start or end of a recipe list. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "list_items": {
     "type": "array"
    },
    "location": {
     "type": "string"
    },
    "name": {
     "type": "string"
    }
   },
   "required": [
    "name",
    "list_items"
   ],
   "type": "object"
  },
  "name": "workato_runtime.insert_to_list_batch",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "recipe_local_state",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_runtime",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Write one deterministic runtime log message with an optional INFO, WARN, or ERROR severity and centralized-log visibility. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "log_level": {
     "enum": [
      "INFO",
      "WARN",
      "ERROR"
     ],
     "type": "string"
    },
    "message": {
     "type": "string"
    },
    "user_logs_enabled": {
     "type": "boolean"
    }
   },
   "required": [
    "message"
   ],
   "type": "object"
  },
  "name": "workato_runtime.log_message",
  "output_schema": {
   "properties": {
    "log_level": {
     "type": "string"
    },
    "message": {
     "type": "string"
    },
    "ok": {
     "type": "boolean"
    },
    "user_logs_enabled": {
     "type": "boolean"
    }
   },
   "required": [
    "ok",
    "message"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "recipe_local_state",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_runtime",
   "operation": "transform",
   "side_effect": false,
   "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Parse a JSON document into a structured value. Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "document": {
     "type": [
      "string",
      "object",
      "array"
     ]
    }
   },
   "required": [
    "document"
   ],
   "type": "object"
  },
  "name": "workato_runtime.parse_json",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "recipe_local_state",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_runtime",
   "operation": "transform",
   "side_effect": false,
   "when_to_use": "Use for the named deterministic transformation or workflow-runtime operation when its output is needed by a later step."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Update recipe variables; pass variable fields alongside the configured name metadata. Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "additionalProperties": true,
   "properties": {
    "input_mode": {
     "type": "string"
    },
    "name": {
     "type": "string"
    }
   },
   "type": "object"
  },
  "name": "workato_runtime.update_variables",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "recipe_local_state",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_runtime",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to change an existing target after its identifier and new values are known. This is a side effect; do not use it as a read."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Invoke a controlled callable recipe. The simulator returns the exact deterministic seeded reply for the supplied flow and request. Invoke a configured child service only when its result or side effect is required. The synchronous form returns a seeded reply; the asynchronous form returns only an acknowledgement. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "flow_id": {
     "type": "string"
    },
    "request": {}
   },
   "required": [
    "flow_id"
   ],
   "type": "object"
  },
  "name": "workato_service.call_service",
  "output_schema": {
   "properties": {
    "ok": {
     "type": "boolean"
    },
    "reply": {}
   },
   "required": [
    "ok"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_service",
   "operation": "operation",
   "side_effect": true,
   "when_to_use": "Invoke a configured child service only when its result or side effect is required. The synchronous form returns a seeded reply; the asynchronous form returns only an acknowledgement."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Controlled Workato async callable-recipe invocation; returns an ack only (no reply). Invoke a configured child service only when its result or side effect is required. The synchronous form returns a seeded reply; the asynchronous form returns only an acknowledgement. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "flow_id": {
     "type": "string"
    },
    "request": {}
   },
   "required": [
    "flow_id"
   ],
   "type": "object"
  },
  "name": "workato_service.call_service_async",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_service",
   "operation": "operation",
   "side_effect": true,
   "when_to_use": "Invoke a configured child service only when its result or side effect is required. The synchronous form returns a seeded reply; the asynchronous form returns only an acknowledgement."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Controlled Workato service (callable recipe) send_reply action. Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "message": {},
    "reply": {},
    "reply_type": {
     "type": "string"
    }
   },
   "required": [
    "reply_type"
   ],
   "type": "object"
  },
  "name": "workato_service.send_reply",
  "output_schema": {
   "properties": {
    "message": {},
    "ok": {
     "type": "boolean"
    },
    "reply": {},
    "reply_type": {
     "type": "string"
    }
   },
   "required": [
    "ok",
    "reply_type"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "external_write",
   "mutates_external_state": true,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_service",
   "operation": "terminal",
   "side_effect": true,
   "when_to_use": "Use only when the caller or parent workflow must receive its final response. Complete prerequisite reads and mutations first; a successful terminal call can end the run."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Create the configured in-memory smart list and return its rows and columns. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "list_name": {
     "type": "string"
    }
   },
   "required": [
    "list_name"
   ],
   "type": "object"
  },
  "name": "workato_smart_list.create_list",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "recipe_local_state",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_smart_list",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Create the configured in-memory smart list from CSV columns. Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "columns": {
     "items": {
      "type": "string"
     },
     "type": "array"
    },
    "list_name": {
     "type": "string"
    }
   },
   "required": [
    "list_name",
    "columns"
   ],
   "type": "object"
  },
  "name": "workato_smart_list.create_list_from_csv",
  "output_schema": {
   "additionalProperties": true,
   "description": "A successful call returns a JSON object. Tool-specific fields are documented when the adapter has a stable, narrower result contract.",
   "type": "object"
  },
  "semantic_constraints": {
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "recipe_local_state",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_smart_list",
   "operation": "mutation",
   "side_effect": true,
   "when_to_use": "Use to create new state only when the task requires it and after checking for duplicates when the task or schema calls for that."
  }
 },
 {
  "canonical_argument_rules": {
   "caught_error_binding": "A caught error's message field is the underlying exception text without the interactive tool-observation 'ERROR:' transport prefix. Preserve that message exactly in any downstream field bound to it.",
   "comparison": "exact_canonical_arguments",
   "object_key_order": "canonical_json_sorted_keys",
   "query_normalization": "For query/sql/where/order arguments, exact scoring discards insignificant whitespace, line endings, one trailing semicolon, and SQL/SOQL keyword case. Quoted literals/identifiers, comments, token order, projections, sources, joins, predicates, grouping, ordering, limits, and bindings remain exact.",
   "scalar_types": "Use the JSON type declared by the canonical input schema. Do not interchange strings, numbers, booleans, or null unless a tool-specific normalization below explicitly requires it.",
   "schema_version": "agentorch-canonical-argument-rules-v1",
   "semantic_rewrites": "forbidden"
  },
  "description": "Run the configured SQL statement over in-memory smart lists. Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt. The simulator registry description and JSON schema are the executable contract.",
  "error_schema": {
   "description": "A failed call is returned to the model as a text observation prefixed with 'ERROR:'; it is not a successful tool result.",
   "pattern": "^ERROR:",
   "type": "string"
  },
  "input_schema": {
   "properties": {
    "sql": {
     "type": "string"
    }
   },
   "required": [
    "sql"
   ],
   "type": "object"
  },
  "name": "workato_smart_list.query_list",
  "output_schema": {
   "properties": {
    "columns": {
     "type": "object"
    },
    "count": {
     "type": "integer"
    },
    "ok": {
     "type": "boolean"
    },
    "row_count": {
     "type": "integer"
    },
    "rows": {
     "items": {
      "type": "object"
     },
     "type": "array"
    }
   },
   "required": [
    "ok",
    "rows",
    "row_count",
    "count"
   ],
   "type": "object"
  },
  "semantic_constraints": {
   "behavior_notes": [
    "SQL doubled apostrophes inside quoted string literals are decoded to a single apostrophe when values are stored and returned."
   ],
   "error_delivery": "error_observation"
  },
  "side_effects": {
   "class": "recipe_local_state",
   "mutates_external_state": false,
   "terminal_on_success": false
  },
  "usage": {
   "connector_family": "workato_smart_list",
   "operation": "read",
   "side_effect": false,
   "when_to_use": "Use for a targeted read when an identifier, existing value, or current state is needed by a later decision or mutation. Avoid speculative reads whose result is already in the prompt."
  }
 }
]

Control tools (always available, not part of the environment):
- {"tool": "finish", "args": {}} — declare the task complete.
- {"tool": "submit_answer", "args": {"answer": ...}} — return a final answer
  when the task asks for one, then stop.
- {"tool": "stop", "args": {"stop_reason": "...", "stop_with_error": true}}
  — execute an explicit workflow stop branch, preserving its reason and error flag.

Action budget: you have a limited number of tool calls. First infer the
intended business outcome from the goal, trigger event, environment cards,
and tool schemas. Use read-only tools only when they are necessary to
identify an existing record, resolve an ID, inspect current state, or avoid
an unsafe mutation. Prefer targeted reads over broad searches. Do not spend
actions verifying information already provided in the prompt or schema
cards. Once you have enough information to perform the required business
effect, execute the minimal set of actions in the dependency and control-flow
order implied by the requirements. Canonical tool choice and action order are
evaluated in addition to final state and terminal outputs.

Response format: reply with exactly ONE JSON object per turn:
{"thought": "...", "tool": "<tool name>", "args": { ... }}
No prose outside the JSON. Tool errors come back as observations — read them
and recover. Do not repeat identical calls.

Work step by step: think, emit exactly one JSON action, observe the result, repeat. Do not announce a full plan up front.
```

</details>

### Initial user message

<details>
<summary>Complete ReAct initial user message</summary>

```text
TRIGGER EVENT:
{
 "context": {
  "access_profile": {
   "id": "10"
  }
 },
 "request": {
  "deprecated_since": "2025-01-01",
  "workspace_user_id": "U12345678"
 }
}

ENVIRONMENT:
- Data table 7199: columns ['11fbe9a6_a16d_4d7e_86ea_afe42ec03005', '3c0b720b_bbe8_47de_a88d_96d759af819e', '622152c7_a09f_4d54_80f7_add539bee209', 'cc31f2eb_b841_498c_bced_247d9dd78edb', 'e3bdb7a7_3561_48c0_b600_c210f5d64bb7', 'id']
- Data table 7201: columns ['11fbe9a6_a16d_4d7e_86ea_afe42ec03005', '25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e', '73fd1e82_f4d2_48a9_8ff2_96713f5acd63', '9d00233f_dc89_4f40_b0f4_c2b6ee765ed2', 'e417aefa_9690_4edd_83c5_8e3f8749fc24', 'id']

PUBLIC WORKFLOW CONTEXT:
{
 "communication_templates": [],
 "control_actions": [
  {
   "name": "finish",
   "purpose": "Declare non-error processing complete."
  },
  {
   "name": "stop",
   "purpose": "Terminate explicit workflow stop branches with stop_reason and stop_with_error."
  }
 ],
 "execution_context_schema": {
  "properties": {},
  "type": "object"
 },
 "input_schema": {
  "properties": {
   "context": {
    "properties": {
     "access_profile": {
      "properties": {
       "id": {
        "title": "Id",
        "type": "string"
       }
      },
      "title": "Access Profile",
      "type": "object"
     }
    },
    "title": "Context",
    "type": "object"
   },
   "request": {
    "properties": {
     "deprecated_since": {
      "format": "date-time",
      "title": "Deprecated since",
      "type": "string"
     },
     "workspace_user_id": {
      "minLength": 1,
      "title": "Workspace user ID",
      "type": [
       "integer",
       "string"
      ]
     }
    },
    "required": [
     "workspace_user_id"
    ],
    "title": "Request",
    "type": "object"
   }
  },
  "required": [
   "request"
  ],
  "type": "object"
 },
 "workspace_resources": [
  {
   "fields": [
    {
     "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "label": "Record ID",
     "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "type": "string"
    },
    {
     "argument_field_id": "50dd1528_57bf_4ed5_a678_03e9c709b140",
     "field_id": "50dd1528_57bf_4ed5_a678_03e9c709b140",
     "label": "api_client_id",
     "output_field_id": "50dd1528_57bf_4ed5_a678_03e9c709b140",
     "type": "string"
    },
    {
     "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "label": "Updated at",
     "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "type": "date_time"
    },
    {
     "argument_field_id": "8016f9ed_ec17_40fd_a45b_4511efa3daf9",
     "field_id": "8016f9ed_ec17_40fd_a45b_4511efa3daf9",
     "label": "name",
     "output_field_id": "8016f9ed_ec17_40fd_a45b_4511efa3daf9",
     "type": "string"
    },
    {
     "argument_field_id": "856d93af_9a6e_4091_af46_051211c25a75",
     "field_id": "856d93af_9a6e_4091_af46_051211c25a75",
     "label": "access_profile_id",
     "output_field_id": "856d93af_9a6e_4091_af46_051211c25a75",
     "type": "string"
    },
    {
     "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "label": "Created at",
     "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "type": "date_time"
    },
    {
     "argument_field_id": "c3f5a247_f6d7_498f_a5fa_6b469edb74d9",
     "field_id": "c3f5a247_f6d7_498f_a5fa_6b469edb74d9",
     "label": "enabled",
     "output_field_id": "c3f5a247_f6d7_498f_a5fa_6b469edb74d9",
     "type": "boolean"
    },
    {
     "argument_field_id": "continuation_token",
     "field_id": "continuation_token",
     "label": "Next Page Token",
     "output_field_id": "continuation_token",
     "type": "string"
    },
    {
     "argument_field_id": "faf6d561_0a7e_42d1_8f8c_ec11f9f86c31",
     "field_id": "faf6d561_0a7e_42d1_8f8c_ec11f9f86c31",
     "label": "workspace_id",
     "output_field_id": "faf6d561_0a7e_42d1_8f8c_ec11f9f86c31",
     "type": "string"
    }
   ],
   "name": "OpenAI Proxy Workspaces",
   "public_id": "11026",
   "resource_kind": "data_table",
   "resource_ref": "resource_5638644dcaf2"
  },
  {
   "fields": [
    {
     "argument_field_id": "01124e6e_cc78_4ef8_be38_cc6d23617b6b",
     "field_id": "01124e6e_cc78_4ef8_be38_cc6d23617b6b",
     "label": "Cancellation Processed",
     "output_field_id": "01124e6e_cc78_4ef8_be38_cc6d23617b6b",
     "type": "boolean"
    },
    {
     "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "label": "Record ID",
     "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "type": "string"
    },
    {
     "argument_field_id": "167199db_4b09_4eee_856d_de4da13762a4",
     "field_id": "167199db_4b09_4eee_856d_de4da13762a4",
     "label": "Date of 4th Event",
     "output_field_id": "167199db_4b09_4eee_856d_de4da13762a4",
     "type": "date"
    },
    {
     "argument_field_id": "167f2a3b_ae11_46eb_85c2_8b9eb0fdcd58",
     "field_id": "167f2a3b_ae11_46eb_85c2_8b9eb0fdcd58",
     "label": "Last Name",
     "output_field_id": "167f2a3b_ae11_46eb_85c2_8b9eb0fdcd58",
     "type": "string"
    },
    {
     "argument_field_id": "18c0d693_fada_4736_8c14_ff92031785cb",
     "field_id": "18c0d693_fada_4736_8c14_ff92031785cb",
     "label": "Hours Event 5",
     "output_field_id": "18c0d693_fada_4736_8c14_ff92031785cb",
     "type": "number"
    },
    {
     "argument_field_id": "1cfaf695_ab64_48c9_87fa_17e809c68169",
     "field_id": "1cfaf695_ab64_48c9_87fa_17e809c68169",
     "label": "First Name",
     "output_field_id": "1cfaf695_ab64_48c9_87fa_17e809c68169",
     "type": "string"
    },
    {
     "argument_field_id": "20e3ee39_1689_48cb_8bc0_8239c4d124d0",
     "field_id": "20e3ee39_1689_48cb_8bc0_8239c4d124d0",
     "label": "Activity Country Record ID",
     "output_field_id": "20e3ee39_1689_48cb_8bc0_8239c4d124d0",
     "type": "string"
    },
    {
     "argument_field_id": "25953fff_bdef_42bd_8e66_d205465e97a1",
     "field_id": "25953fff_bdef_42bd_8e66_d205465e97a1",
     "label": "Approved by",
     "output_field_id": "25953fff_bdef_42bd_8e66_d205465e97a1",
     "type": "string"
    },
    {
     "argument_field_id": "2f960f40_2f77_4619_bd23_dadae6bd3ec2",
     "field_id": "2f960f40_2f77_4619_bd23_dadae6bd3ec2",
     "label": "Numbers Helped",
     "output_field_id": "2f960f40_2f77_4619_bd23_dadae6bd3ec2",
     "type": "integer"
    },
    {
     "argument_field_id": "3dc4d7e4_9803_4033_b92e_b437afeb72c2",
     "field_id": "3dc4d7e4_9803_4033_b92e_b437afeb72c2",
     "label": "Date of 7th Event",
     "output_field_id": "3dc4d7e4_9803_4033_b92e_b437afeb72c2",
     "type": "date"
    },
    {
     "argument_field_id": "404b52eb_8549_49a4_bccb_f9bc987dd849",
     "field_id": "404b52eb_8549_49a4_bccb_f9bc987dd849",
     "label": "Hours Event 3",
     "output_field_id": "404b52eb_8549_49a4_bccb_f9bc987dd849",
     "type": "number"
    },
    {
     "argument_field_id": "40d6f8f4_505a_46fb_b8ec_cdfe56ba806f",
     "field_id": "40d6f8f4_505a_46fb_b8ec_cdfe56ba806f",
     "label": "Activity City",
     "output_field_id": "40d6f8f4_505a_46fb_b8ec_cdfe56ba806f",
     "type": "string"
    },
    {
     "argument_field_id": "410f1576_4a3b_4f90_993f_369ca6208e70",
     "field_id": "410f1576_4a3b_4f90_993f_369ca6208e70",
     "label": "Hours Event 7",
     "output_field_id": "410f1576_4a3b_4f90_993f_369ca6208e70",
     "type": "number"
    },
    {
     "argument_field_id": "4689ede5_c4d0_4cc8_88ba_abdeac672762",
     "field_id": "4689ede5_c4d0_4cc8_88ba_abdeac672762",
     "label": "Activity Contact Email",
     "output_field_id": "4689ede5_c4d0_4cc8_88ba_abdeac672762",
     "type": "string"
    },
    {
     "argument_field_id": "4727fb54_1245_444e_b9a0_5ef1d9ba8165",
     "field_id": "4727fb54_1245_444e_b9a0_5ef1d9ba8165",
     "label": "Remarks",
     "output_field_id": "4727fb54_1245_444e_b9a0_5ef1d9ba8165",
     "type": "string"
    },
    {
     "argument_field_id": "52bc22f6_e74d_4852_a071_2d37cf0f02b2",
     "field_id": "52bc22f6_e74d_4852_a071_2d37cf0f02b2",
     "label": "Cancellation Approved by",
     "output_field_id": "52bc22f6_e74d_4852_a071_2d37cf0f02b2",
     "type": "string"
    },
    {
     "argument_field_id": "554d3e32_a9e4_492a_915c_8fc5eee4551d",
     "field_id": "554d3e32_a9e4_492a_915c_8fc5eee4551d",
     "label": "Email Record ID",
     "output_field_id": "554d3e32_a9e4_492a_915c_8fc5eee4551d",
     "type": "string"
    },
    {
     "argument_field_id": "5e209040_8b16_48a3_9007_c03cd76dde16",
     "field_id": "5e209040_8b16_48a3_9007_c03cd76dde16",
     "label": "Date of 1st Event",
     "output_field_id": "5e209040_8b16_48a3_9007_c03cd76dde16",
     "type": "date"
    },
    {
     "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "label": "Updated at",
     "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "type": "date_time"
    },
    {
     "argument_field_id": "69246342_8538_4ac7_a570_bd69df6e6eb4",
     "field_id": "69246342_8538_4ac7_a570_bd69df6e6eb4",
     "label": "Hours Event 9",
     "output_field_id": "69246342_8538_4ac7_a570_bd69df6e6eb4",
     "type": "number"
    },
    {
     "argument_field_id": "69849ff0_cdb7_40b3_a977_b01b258fef6b",
     "field_id": "69849ff0_cdb7_40b3_a977_b01b258fef6b",
     "label": "Cancellation Reason",
     "output_field_id": "69849ff0_cdb7_40b3_a977_b01b258fef6b",
     "type": "string"
    },
    {
     "argument_field_id": "69934d20_5a3a_421b_973a_d48c324013d0",
     "field_id": "69934d20_5a3a_421b_973a_d48c324013d0",
     "label": "Error",
     "output_field_id": "69934d20_5a3a_421b_973a_d48c324013d0",
     "type": "boolean"
    },
    {
     "argument_field_id": "6c944059_f21e_43a7_b935_19166b5432fa",
     "field_id": "6c944059_f21e_43a7_b935_19166b5432fa",
     "label": "Date of 10th Event",
     "output_field_id": "6c944059_f21e_43a7_b935_19166b5432fa",
     "type": "date"
    },
    {
     "argument_field_id": "7102349b_0e89_49a3_bd7d_19682607f1d9",
     "field_id": "7102349b_0e89_49a3_bd7d_19682607f1d9",
     "label": "Date of 3rd Event",
     "output_field_id": "7102349b_0e89_49a3_bd7d_19682607f1d9",
     "type": "date"
    },
    {
     "argument_field_id": "7253ca9f_cada_49d3_99ba_129962c45e97",
     "field_id": "7253ca9f_cada_49d3_99ba_129962c45e97",
     "label": "Employee Country Record ID",
     "output_field_id": "7253ca9f_cada_49d3_99ba_129962c45e97",
     "type": "string"
    },
    {
     "argument_field_id": "74abc251_e97c_462f_bad0_2a4be1ad65d8",
     "field_id": "74abc251_e97c_462f_bad0_2a4be1ad65d8",
     "label": "Edit Type",
     "output_field_id": "74abc251_e97c_462f_bad0_2a4be1ad65d8",
     "type": "string"
    },
    {
     "argument_field_id": "760bbef6_46ee_40a3_9aa3_430452dead2f",
     "field_id": "760bbef6_46ee_40a3_9aa3_430452dead2f",
     "label": "$internal_value_760bbef6-46ee-40a3-9aa3-430452dead2f",
     "output_field_id": "760bbef6_46ee_40a3_9aa3_430452dead2f",
     "type": "string"
    },
    {
     "argument_field_id": "7928fb21_5d0c_40ea_b486_ef56cdddf941",
     "field_id": "7928fb21_5d0c_40ea_b486_ef56cdddf941",
     "label": "Activity Description",
     "output_field_id": "7928fb21_5d0c_40ea_b486_ef56cdddf941",
     "type": "string"
    },
    {
     "argument_field_id": "7afbd433_45b2_49c7_b826_782e80a49010",
     "field_id": "7afbd433_45b2_49c7_b826_782e80a49010",
     "label": "Hours Event 10",
     "output_field_id": "7afbd433_45b2_49c7_b826_782e80a49010",
     "type": "number"
    },
    {
     "argument_field_id": "7ef9ec80_c50c_4c89_9c82_7d059c9f083f",
     "field_id": "7ef9ec80_c50c_4c89_9c82_7d059c9f083f",
     "label": "Sequence Number",
     "output_field_id": "7ef9ec80_c50c_4c89_9c82_7d059c9f083f",
     "type": "integer"
    },
    {
     "argument_field_id": "7fee37e0_2499_4b16_848a_9571d68407c7",
     "field_id": "7fee37e0_2499_4b16_848a_9571d68407c7",
     "label": "Date of 9th Event",
     "output_field_id": "7fee37e0_2499_4b16_848a_9571d68407c7",
     "type": "date"
    },
    {
     "argument_field_id": "802fd7fe_8871_4620_bf45_22f6e8ba5fc2",
     "field_id": "802fd7fe_8871_4620_bf45_22f6e8ba5fc2",
     "label": "Organization Supported",
     "output_field_id": "802fd7fe_8871_4620_bf45_22f6e8ba5fc2",
     "type": "string"
    },
    {
     "argument_field_id": "876153d1_7763_4c4a_8dab_b901b5bcc007",
     "field_id": "876153d1_7763_4c4a_8dab_b901b5bcc007",
     "label": "Date of 2nd Event",
     "output_field_id": "876153d1_7763_4c4a_8dab_b901b5bcc007",
     "type": "date"
    },
    {
     "argument_field_id": "877856ae_d57b_479c_90b7_cd25cf04cf09",
     "field_id": "877856ae_d57b_479c_90b7_cd25cf04cf09",
     "label": "Number of Repeats",
     "output_field_id": "877856ae_d57b_479c_90b7_cd25cf04cf09",
     "type": "integer"
    },
    {
     "argument_field_id": "8a711850_6e92_4ab7_90a7_4ad66539f306",
     "field_id": "8a711850_6e92_4ab7_90a7_4ad66539f306",
     "label": "Employee City",
     "output_field_id": "8a711850_6e92_4ab7_90a7_4ad66539f306",
     "type": "string"
    },
    {
     "argument_field_id": "9e9bd915_2a6e_4a73_812d_bb2c5baec4f0",
     "field_id": "9e9bd915_2a6e_4a73_812d_bb2c5baec4f0",
     "label": "Approval Date",
     "output_field_id": "9e9bd915_2a6e_4a73_812d_bb2c5baec4f0",
     "type": "date"
    },
    {
     "argument_field_id": "a2335e02_cdaf_435d_b842_e18b69dcce29",
     "field_id": "a2335e02_cdaf_435d_b842_e18b69dcce29",
     "label": "Date of 5th Event",
     "output_field_id": "a2335e02_cdaf_435d_b842_e18b69dcce29",
     "type": "date"
    },
    {
     "argument_field_id": "a51e7a67_fa77_4d54_9423_6475b28cb091",
     "field_id": "a51e7a67_fa77_4d54_9423_6475b28cb091",
     "label": "Hours Event 6",
     "output_field_id": "a51e7a67_fa77_4d54_9423_6475b28cb091",
     "type": "number"
    },
    {
     "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "label": "Created at",
     "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "type": "date_time"
    },
    {
     "argument_field_id": "ad2a9320_2230_45ed_b689_9caef4dae5e9",
     "field_id": "ad2a9320_2230_45ed_b689_9caef4dae5e9",
     "label": "Cancellation Date",
     "output_field_id": "ad2a9320_2230_45ed_b689_9caef4dae5e9",
     "type": "date"
    },
    {
     "argument_field_id": "aece0ef4_7b3b_4621_9073_687670fc14a6",
     "field_id": "aece0ef4_7b3b_4621_9073_687670fc14a6",
     "label": "Team Name",
     "output_field_id": "aece0ef4_7b3b_4621_9073_687670fc14a6",
     "type": "string"
    },
    {
     "argument_field_id": "b36957f0_00e4_44e6_a465_ab063e6ac998",
     "field_id": "b36957f0_00e4_44e6_a465_ab063e6ac998",
     "label": "Activity Contact Name",
     "output_field_id": "b36957f0_00e4_44e6_a465_ab063e6ac998",
     "type": "string"
    },
    {
     "argument_field_id": "b3914c90_f85d_40db_a152_bc83fdcff759",
     "field_id": "b3914c90_f85d_40db_a152_bc83fdcff759",
     "label": "Donation Amount in USD",
     "output_field_id": "b3914c90_f85d_40db_a152_bc83fdcff759",
     "type": "number"
    },
    {
     "argument_field_id": "b6240623_a906_419f_8482_e8c87a553c16",
     "field_id": "b6240623_a906_419f_8482_e8c87a553c16",
     "label": "Employee Region",
     "output_field_id": "b6240623_a906_419f_8482_e8c87a553c16",
     "type": "string"
    },
    {
     "argument_field_id": "b7b769ad_f990_412e_9875_0bb7b7f856e8",
     "field_id": "b7b769ad_f990_412e_9875_0bb7b7f856e8",
     "label": "Confirm Action",
     "output_field_id": "b7b769ad_f990_412e_9875_0bb7b7f856e8",
     "type": "boolean"
    },
    {
     "argument_field_id": "b864a786_6329_46fb_a72a_c8e79f78c02b",
     "field_id": "b864a786_6329_46fb_a72a_c8e79f78c02b",
     "label": "Activity State Record ID",
     "output_field_id": "b864a786_6329_46fb_a72a_c8e79f78c02b",
     "type": "string"
    },
    {
     "argument_field_id": "b94dbd14_5a98_42ca_872b_00e804a5833f",
     "field_id": "b94dbd14_5a98_42ca_872b_00e804a5833f",
     "label": "Currency Record ID",
     "output_field_id": "b94dbd14_5a98_42ca_872b_00e804a5833f",
     "type": "string"
    },
    {
     "argument_field_id": "bc37fa3a_9da2_4763_938c_3aaa8afc3a01",
     "field_id": "bc37fa3a_9da2_4763_938c_3aaa8afc3a01",
     "label": "Cancellation in Progress",
     "output_field_id": "bc37fa3a_9da2_4763_938c_3aaa8afc3a01",
     "type": "boolean"
    },
    {
     "argument_field_id": "bd58f2c4_b532_485d_985d_bbca305b7b0f",
     "field_id": "bd58f2c4_b532_485d_985d_bbca305b7b0f",
     "label": "Repeating Event",
     "output_field_id": "bd58f2c4_b532_485d_985d_bbca305b7b0f",
     "type": "string"
    },
    {
     "argument_field_id": "c19f32dd_7a33_43af_9371_a733764e2680",
     "field_id": "c19f32dd_7a33_43af_9371_a733764e2680",
     "label": "Date of 6th Event",
     "output_field_id": "c19f32dd_7a33_43af_9371_a733764e2680",
     "type": "date"
    },
    {
     "argument_field_id": "c4ef3a4a_5dcd_4aa0_958c_e41d270bcc0a",
     "field_id": "c4ef3a4a_5dcd_4aa0_958c_e41d270bcc0a",
     "label": "Hours Event 4",
     "output_field_id": "c4ef3a4a_5dcd_4aa0_958c_e41d270bcc0a",
     "type": "number"
    },
    {
     "argument_field_id": "cb7bb8c4_ff9c_45b6_a3f1_de847e8ceb9c",
     "field_id": "cb7bb8c4_ff9c_45b6_a3f1_de847e8ceb9c",
     "label": "Donation Amount",
     "output_field_id": "cb7bb8c4_ff9c_45b6_a3f1_de847e8ceb9c",
     "type": "number"
    },
    {
     "argument_field_id": "continuation_token",
     "field_id": "continuation_token",
     "label": "Next Page Token",
     "output_field_id": "continuation_token",
     "type": "string"
    },
    {
     "argument_field_id": "d4d22a2e_f94f_4c44_844d_fd997d55ebe6",
     "field_id": "d4d22a2e_f94f_4c44_844d_fd997d55ebe6",
     "label": "Hours Event 8",
     "output_field_id": "d4d22a2e_f94f_4c44_844d_fd997d55ebe6",
     "type": "number"
    },
    {
     "argument_field_id": "dab764eb_dff8_4547_b8bb_67aae5df53c3",
     "field_id": "dab764eb_dff8_4547_b8bb_67aae5df53c3",
     "label": "Type",
     "output_field_id": "dab764eb_dff8_4547_b8bb_67aae5df53c3",
     "type": "string"
    },
    {
     "argument_field_id": "display_name",
     "field_id": "display_name",
     "label": "Employee ID",
     "output_field_id": "display_name",
     "type": "string"
    },
    {
     "argument_field_id": "e2bfdbe9_ccb2_4bfb_9c71_6d64d938d575",
     "field_id": "e2bfdbe9_ccb2_4bfb_9c71_6d64d938d575",
     "label": "Job Title",
     "output_field_id": "e2bfdbe9_ccb2_4bfb_9c71_6d64d938d575",
     "type": "string"
    },
    {
     "argument_field_id": "e39035d7_23cc_4fc5_b5f4_49a3c5be5932",
     "field_id": "e39035d7_23cc_4fc5_b5f4_49a3c5be5932",
     "label": "Date of 8th Event",
     "output_field_id": "e39035d7_23cc_4fc5_b5f4_49a3c5be5932",
     "type": "date"
    },
    {
     "argument_field_id": "e6d6384f_8eb2_4dd2_8ff6_1f0bdaa3d298",
     "field_id": "e6d6384f_8eb2_4dd2_8ff6_1f0bdaa3d298",
     "label": "Status",
     "output_field_id": "e6d6384f_8eb2_4dd2_8ff6_1f0bdaa3d298",
     "type": "string"
    },
    {
     "argument_field_id": "e8a8c5cb_6101_46bf_8573_1e1c3d26e5f9",
     "field_id": "e8a8c5cb_6101_46bf_8573_1e1c3d26e5f9",
     "label": "Employee ID Record ID",
     "output_field_id": "e8a8c5cb_6101_46bf_8573_1e1c3d26e5f9",
     "type": "string"
    },
    {
     "argument_field_id": "ec745f6d_2207_40c6_a674_5e8b6539f5eb",
     "field_id": "ec745f6d_2207_40c6_a674_5e8b6539f5eb",
     "label": "WC Record ID",
     "output_field_id": "ec745f6d_2207_40c6_a674_5e8b6539f5eb",
     "type": "string"
    },
    {
     "argument_field_id": "eff58340_4fde_41e0_963d_fb218d22f75d",
     "field_id": "eff58340_4fde_41e0_963d_fb218d22f75d",
     "label": "Department Name",
     "output_field_id": "eff58340_4fde_41e0_963d_fb218d22f75d",
     "type": "string"
    },
    {
     "argument_field_id": "f405f394_4ccf_499f_9673_c23875c72a4e",
     "field_id": "f405f394_4ccf_499f_9673_c23875c72a4e",
     "label": "Board Member",
     "output_field_id": "f405f394_4ccf_499f_9673_c23875c72a4e",
     "type": "boolean"
    },
    {
     "argument_field_id": "f56cd8f8_9d3a_4879_8864_ea652f4acb05",
     "field_id": "f56cd8f8_9d3a_4879_8864_ea652f4acb05",
     "label": "Hours Event 1",
     "output_field_id": "f56cd8f8_9d3a_4879_8864_ea652f4acb05",
     "type": "number"
    },
    {
     "argument_field_id": "fabd425b_634d_49f8_8726_76ba9d3ae9bf",
     "field_id": "fabd425b_634d_49f8_8726_76ba9d3ae9bf",
     "label": "Hours Event 2",
     "output_field_id": "fabd425b_634d_49f8_8726_76ba9d3ae9bf",
     "type": "number"
    },
    {
     "argument_field_id": "file_content",
     "field_id": "file_content",
     "label": "File contents",
     "output_field_id": "file_content",
     "type": "string"
    },
    {
     "argument_field_id": "filename",
     "field_id": "filename",
     "label": "File name",
     "output_field_id": "filename",
     "type": "string"
    },
    {
     "argument_field_id": "record_id",
     "field_id": "record_id",
     "label": "Record ID",
     "output_field_id": "record_id",
     "type": "string"
    }
   ],
   "name": "[SUB] Workato Cares Submission Raw Data",
   "public_id": "13821",
   "resource_kind": "data_table",
   "resource_ref": "resource_f6ecaffe74c8"
  },
  {
   "fields": [
    {
     "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "label": "Record ID",
     "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "type": "string"
    },
    {
     "argument_field_id": "24313710_ea71_43c5_9694_b5f55c56a5b7",
     "field_id": "24313710_ea71_43c5_9694_b5f55c56a5b7",
     "label": "Examples",
     "output_field_id": "24313710_ea71_43c5_9694_b5f55c56a5b7",
     "type": "string"
    },
    {
     "argument_field_id": "595299b9_812f_497c_b041_d43e6172fa67",
     "field_id": "595299b9_812f_497c_b041_d43e6172fa67",
     "label": "Name",
     "output_field_id": "595299b9_812f_497c_b041_d43e6172fa67",
     "type": "string"
    },
    {
     "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "label": "Updated at",
     "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "type": "date_time"
    },
    {
     "argument_field_id": "8389efac_4a35_447b_a378_8152c43250c4",
     "field_id": "8389efac_4a35_447b_a378_8152c43250c4",
     "label": "Level",
     "output_field_id": "8389efac_4a35_447b_a378_8152c43250c4",
     "type": "string"
    },
    {
     "argument_field_id": "<anon>aaaaaaaa_bbbb_cccc_dddd_eeeeeeeeeeee</anon>",
     "field_id": "<anon>aaaaaaaa_bbbb_cccc_dddd_eeeeeeeeeeee</anon>",
     "label": "Primary key",
     "output_field_id": "<anon>aaaaaaaa_bbbb_cccc_dddd_eeeeeeeeeeee</anon>",
     "resource_role": "primary_key"
    },
    {
     "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "label": "Created at",
     "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "type": "date_time"
    },
    {
     "argument_field_id": "a65c1011_c527_429b_ad1d_ad3ed4a485b8",
     "field_id": "a65c1011_c527_429b_ad1d_ad3ed4a485b8",
     "label": "Description",
     "output_field_id": "a65c1011_c527_429b_ad1d_ad3ed4a485b8",
     "type": "string"
    }
   ],
   "name": "[AC] WORKATO_INTEGRATION_LEVEL",
   "public_id": "20686",
   "resource_kind": "data_table",
   "resource_ref": "resource_f27e54a7c867"
  },
  {
   "fields": [
    {
     "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "label": "Record ID",
     "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "type": "string"
    },
    {
     "argument_field_id": "13b82b43_2f7a_4d98_a50d_1a5af68bc4c3",
     "field_id": "13b82b43_2f7a_4d98_a50d_1a5af68bc4c3",
     "label": "Quest Name",
     "output_field_id": "13b82b43_2f7a_4d98_a50d_1a5af68bc4c3",
     "type": "string"
    },
    {
     "argument_field_id": "3c779a6b_a7ca_44fc_acb8_69ce179d9584",
     "field_id": "3c779a6b_a7ca_44fc_acb8_69ce179d9584",
     "label": "Credited Date",
     "output_field_id": "3c779a6b_a7ca_44fc_acb8_69ce179d9584",
     "type": "string"
    },
    {
     "argument_field_id": "614e8425_fe37_4acd_b67b_1ed72fc8568a",
     "field_id": "614e8425_fe37_4acd_b67b_1ed72fc8568a",
     "label": "User ID",
     "output_field_id": "614e8425_fe37_4acd_b67b_1ed72fc8568a",
     "type": "string"
    },
    {
     "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "label": "Updated at",
     "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "type": "date_time"
    },
    {
     "argument_field_id": "68240f61_d77a_49f4_8252_24fc373a730d",
     "field_id": "68240f61_d77a_49f4_8252_24fc373a730d",
     "label": "Status",
     "output_field_id": "68240f61_d77a_49f4_8252_24fc373a730d",
     "type": "string"
    },
    {
     "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "label": "Created at",
     "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "type": "date_time"
    },
    {
     "argument_field_id": "acc76697_ddd7_4d13_87fc_5a6e0b5d6860",
     "field_id": "acc76697_ddd7_4d13_87fc_5a6e0b5d6860",
     "label": "Quest Code",
     "output_field_id": "acc76697_ddd7_4d13_87fc_5a6e0b5d6860",
     "type": "string"
    },
    {
     "argument_field_id": "continuation_token",
     "field_id": "continuation_token",
     "label": "Next Page Token",
     "output_field_id": "continuation_token",
     "type": "string"
    },
    {
     "argument_field_id": "d98a88e6_2320_492f_bd4b_eb600a86e0a1",
     "field_id": "d98a88e6_2320_492f_bd4b_eb600a86e0a1",
     "label": "Points Earned",
     "output_field_id": "d98a88e6_2320_492f_bd4b_eb600a86e0a1",
     "type": "integer"
    },
    {
     "argument_field_id": "ddd2fcd3_e629_4d80_9e78_fe3fb5c9f88b",
     "field_id": "ddd2fcd3_e629_4d80_9e78_fe3fb5c9f88b",
     "label": "$internal_value_ddd2fcd3-e629-4d80-9e78-fe3fb5c9f88b",
     "output_field_id": "ddd2fcd3_e629_4d80_9e78_fe3fb5c9f88b",
     "type": "string"
    },
    {
     "argument_field_id": "file_content",
     "field_id": "file_content",
     "label": "File contents",
     "output_field_id": "file_content",
     "type": "string"
    },
    {
     "argument_field_id": "filename",
     "field_id": "filename",
     "label": "File name",
     "output_field_id": "filename",
     "type": "string"
    }
   ],
   "name": "[WWW] Quest Activity",
   "public_id": "28115",
   "resource_kind": "data_table",
   "resource_ref": "resource_68aa4a601ed9"
  },
  {
   "fields": [
    {
     "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "label": "Record ID",
     "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "type": "string"
    },
    {
     "argument_field_id": "3ac3e90c_8e9b_4b58_b019_715ecd63b3d4",
     "field_id": "3ac3e90c_8e9b_4b58_b019_715ecd63b3d4",
     "label": "Application ID",
     "output_field_id": "3ac3e90c_8e9b_4b58_b019_715ecd63b3d4",
     "resource_role": "primary_key",
     "type": "string"
    },
    {
     "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "label": "Updated at",
     "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "type": "date_time"
    },
    {
     "argument_field_id": "7b20b969_f842_4eaa_8f35_753fe911fbee",
     "field_id": "7b20b969_f842_4eaa_8f35_753fe911fbee",
     "label": "Resume URL",
     "output_field_id": "7b20b969_f842_4eaa_8f35_753fe911fbee",
     "type": "string"
    },
    {
     "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "label": "Created at",
     "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "type": "date_time"
    },
    {
     "argument_field_id": "a7ba4bb3_7e03_4298_8f2e_f302d17fff39",
     "field_id": "a7ba4bb3_7e03_4298_8f2e_f302d17fff39",
     "label": "Job ID",
     "output_field_id": "a7ba4bb3_7e03_4298_8f2e_f302d17fff39",
     "type": "string"
    },
    {
     "argument_field_id": "c90c7596_43bf_466c_8a8f_b6d9819e2169",
     "field_id": "c90c7596_43bf_466c_8a8f_b6d9819e2169",
     "label": "Status",
     "output_field_id": "c90c7596_43bf_466c_8a8f_b6d9819e2169",
     "type": "string"
    },
    {
     "argument_field_id": "d32edade_33fa_4613_b8f7_976915faf727",
     "field_id": "d32edade_33fa_4613_b8f7_976915faf727",
     "label": "Log",
     "output_field_id": "d32edade_33fa_4613_b8f7_976915faf727",
     "type": "string"
    },
    {
     "argument_field_id": "fe5cbb7e_f1ba_4cc2_8cd3_509e81f6b4d1",
     "field_id": "fe5cbb7e_f1ba_4cc2_8cd3_509e81f6b4d1",
     "label": "Role",
     "output_field_id": "fe5cbb7e_f1ba_4cc2_8cd3_509e81f6b4d1",
     "type": "string"
    }
   ],
   "name": "30554",
   "public_id": "30554",
   "resource_kind": "data_table",
   "resource_ref": "resource_9888316085dd"
  },
  {
   "fields": [
    {
     "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "label": "Record ID",
     "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "type": "string"
    },
    {
     "argument_field_id": "1b9473c2_54ae_47f3_9576_c3ec76f3bd6d",
     "field_id": "1b9473c2_54ae_47f3_9576_c3ec76f3bd6d",
     "label": "target_project",
     "output_field_id": "1b9473c2_54ae_47f3_9576_c3ec76f3bd6d",
     "type": "string"
    },
    {
     "argument_field_id": "347bdaaf_5194_4363_a3e0_2a1e04f8aca2",
     "field_id": "347bdaaf_5194_4363_a3e0_2a1e04f8aca2",
     "label": "product_area",
     "output_field_id": "347bdaaf_5194_4363_a3e0_2a1e04f8aca2",
     "type": "string"
    },
    {
     "argument_field_id": "45e4add0_f5a6_4d3d_bcd0_2ed9e0cc15a8",
     "field_id": "45e4add0_f5a6_4d3d_bcd0_2ed9e0cc15a8",
     "label": "ticket_url",
     "output_field_id": "45e4add0_f5a6_4d3d_bcd0_2ed9e0cc15a8",
     "type": "string"
    },
    {
     "argument_field_id": "4fd3d64a_5fa4_4a8f_b5db_22a214b39b9f",
     "field_id": "4fd3d64a_5fa4_4a8f_b5db_22a214b39b9f",
     "label": "key",
     "output_field_id": "4fd3d64a_5fa4_4a8f_b5db_22a214b39b9f",
     "resource_role": "primary_key",
     "type": "string"
    },
    {
     "argument_field_id": "5a7eb53b_e407_41fd_a227_8f93e6a9c023",
     "field_id": "5a7eb53b_e407_41fd_a227_8f93e6a9c023",
     "label": "customer_company",
     "output_field_id": "5a7eb53b_e407_41fd_a227_8f93e6a9c023",
     "type": "string"
    },
    {
     "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "label": "Updated at",
     "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "type": "date_time"
    },
    {
     "argument_field_id": "68cbd891_51dd_4e33_92fa_8651d7e09441",
     "field_id": "68cbd891_51dd_4e33_92fa_8651d7e09441",
     "label": "updated",
     "output_field_id": "68cbd891_51dd_4e33_92fa_8651d7e09441",
     "type": "date_time"
    },
    {
     "argument_field_id": "75551508_f290_41de_88fd_d77306bebea5",
     "field_id": "75551508_f290_41de_88fd_d77306bebea5",
     "label": "summary",
     "output_field_id": "75551508_f290_41de_88fd_d77306bebea5",
     "type": "string"
    },
    {
     "argument_field_id": "a08c09e7_53d4_46dc_9bc7_a308696dc6c1",
     "field_id": "a08c09e7_53d4_46dc_9bc7_a308696dc6c1",
     "label": "status",
     "output_field_id": "a08c09e7_53d4_46dc_9bc7_a308696dc6c1",
     "type": "string"
    },
    {
     "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "label": "Created at",
     "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "type": "date_time"
    },
    {
     "argument_field_id": "b2ae037d_640f_4c56_aeee_17d61b531080",
     "field_id": "b2ae037d_640f_4c56_aeee_17d61b531080",
     "label": "pm_triage_breach_time",
     "output_field_id": "b2ae037d_640f_4c56_aeee_17d61b531080",
     "type": "date_time"
    },
    {
     "argument_field_id": "b57087c4_57c9_4d82_a27e_af9969896e53",
     "field_id": "b57087c4_57c9_4d82_a27e_af9969896e53",
     "label": "source_of_enhancement_request",
     "output_field_id": "b57087c4_57c9_4d82_a27e_af9969896e53",
     "type": "string"
    },
    {
     "argument_field_id": "d3779dbf_043c_4826_8c8e_d83c2e46b8fb",
     "field_id": "d3779dbf_043c_4826_8c8e_d83c2e46b8fb",
     "label": "description",
     "output_field_id": "d3779dbf_043c_4826_8c8e_d83c2e46b8fb",
     "type": "string"
    },
    {
     "argument_field_id": "d71da57a_cf54_48ca_89a5_51e4ea1bd675",
     "field_id": "d71da57a_cf54_48ca_89a5_51e4ea1bd675",
     "label": "product_manager",
     "output_field_id": "d71da57a_cf54_48ca_89a5_51e4ea1bd675",
     "type": "string"
    },
    {
     "argument_field_id": "e267c871_7ff1_4b0b_a7bc_b1e39a5ed39b",
     "field_id": "e267c871_7ff1_4b0b_a7bc_b1e39a5ed39b",
     "label": "created",
     "output_field_id": "e267c871_7ff1_4b0b_a7bc_b1e39a5ed39b",
     "type": "date_time"
    },
    {
     "argument_field_id": "e8bf2d92_807a_477b_9c2a_de56a876b993",
     "field_id": "e8bf2d92_807a_477b_9c2a_de56a876b993",
     "label": "pe_team",
     "output_field_id": "e8bf2d92_807a_477b_9c2a_de56a876b993",
     "type": "string"
    },
    {
     "argument_field_id": "f7651665_4dd2_413d_a704_f81972a4c1d4",
     "field_id": "f7651665_4dd2_413d_a704_f81972a4c1d4",
     "label": "pm_triage_breach",
     "output_field_id": "f7651665_4dd2_413d_a704_f81972a4c1d4",
     "type": "string"
    }
   ],
   "name": "PSM Enhancements Data",
   "public_id": "33563",
   "resource_kind": "data_table",
   "resource_ref": "resource_d5e66c9a88f3"
  },
  {
   "fields": [
    {
     "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "label": "Record ID",
     "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "type": "string"
    },
    {
     "argument_field_id": "1398de92_647f_4c1a_b1b3_77c53af0ed78",
     "field_id": "1398de92_647f_4c1a_b1b3_77c53af0ed78",
     "label": "assets_and_dependencies",
     "output_field_id": "1398de92_647f_4c1a_b1b3_77c53af0ed78",
     "type": "string"
    },
    {
     "argument_field_id": "13f19e63_dd47_4682_81c0_47c4bcaeeae3",
     "field_id": "13f19e63_dd47_4682_81c0_47c4bcaeeae3",
     "label": "released_at",
     "output_field_id": "13f19e63_dd47_4682_81c0_47c4bcaeeae3",
     "type": "date_time"
    },
    {
     "argument_field_id": "205f0633_0893_447e_a24f_146797dd3dfe",
     "field_id": "205f0633_0893_447e_a24f_146797dd3dfe",
     "label": "release_notes",
     "output_field_id": "205f0633_0893_447e_a24f_146797dd3dfe",
     "type": "string"
    },
    {
     "argument_field_id": "2069a23e_4fcc_4674_9f81_094ac5e8c95d",
     "field_id": "2069a23e_4fcc_4674_9f81_094ac5e8c95d",
     "label": "$internal_value_2069a23e-4fcc-4674-9f81-094ac5e8c95d",
     "output_field_id": "2069a23e_4fcc_4674_9f81_094ac5e8c95d",
     "type": "string"
    },
    {
     "argument_field_id": "225a1c1a_9719_4d19_bb71_8d5762009d49",
     "field_id": "225a1c1a_9719_4d19_bb71_8d5762009d49",
     "label": "expires_at",
     "output_field_id": "225a1c1a_9719_4d19_bb71_8d5762009d49",
     "type": "date_time"
    },
    {
     "argument_field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
     "field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
     "label": "deprecated_at",
     "output_field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
     "type": "date_time"
    },
    {
     "argument_field_id": "4612b15c_300f_4120_870b_1884489c3736",
     "field_id": "4612b15c_300f_4120_870b_1884489c3736",
     "label": "version_number",
     "output_field_id": "4612b15c_300f_4120_870b_1884489c3736",
     "type": "integer"
    },
    {
     "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "label": "Updated at",
     "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "type": "date_time"
    },
    {
     "argument_field_id": "622152c7_a09f_4d54_80f7_add539bee209",
     "field_id": "622152c7_a09f_4d54_80f7_add539bee209",
     "label": "$internal_value_622152c7-a09f-4d54-80f7-add539bee209",
     "output_field_id": "622152c7_a09f_4d54_80f7_add539bee209",
     "type": "string"
    },
    {
     "argument_field_id": "6e0f65d3_4376_4264_a472_c705bd4d41b4",
     "field_id": "6e0f65d3_4376_4264_a472_c705bd4d41b4",
     "label": "directory",
     "output_field_id": "6e0f65d3_4376_4264_a472_c705bd4d41b4",
     "type": "string"
    },
    {
     "argument_field_id": "7b0540a6_7322_42dd_b6cf_89cf8759fb73",
     "field_id": "7b0540a6_7322_42dd_b6cf_89cf8759fb73",
     "label": "installed_from_package_version_id",
     "output_field_id": "7b0540a6_7322_42dd_b6cf_89cf8759fb73",
     "type": "string"
    },
    {
     "argument_field_id": "891c88dd_6aa1_46a3_80ef_92fbb6c21f53",
     "field_id": "891c88dd_6aa1_46a3_80ef_92fbb6c21f53",
     "label": "$internal_value_891c88dd-6aa1-46a3-80ef-92fbb6c21f53",
     "output_field_id": "891c88dd_6aa1_46a3_80ef_92fbb6c21f53",
     "type": "string"
    },
    {
     "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "label": "Created at",
     "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "type": "date_time"
    },
    {
     "argument_field_id": "cc31f2eb_b841_498c_bced_247d9dd78edb",
     "field_id": "cc31f2eb_b841_498c_bced_247d9dd78edb",
     "label": "name",
     "output_field_id": "cc31f2eb_b841_498c_bced_247d9dd78edb",
     "type": "string"
    },
    {
     "argument_field_id": "continuation_token",
     "field_id": "continuation_token",
     "label": "Next Page Token",
     "output_field_id": "continuation_token",
     "type": "string"
    },
    {
     "argument_field_id": "d1a07df5_2696_436d_930b_9a3ba82e0f26",
     "field_id": "d1a07df5_2696_436d_930b_9a3ba82e0f26",
     "label": "job_id",
     "output_field_id": "d1a07df5_2696_436d_930b_9a3ba82e0f26",
     "type": "string"
    },
    {
     "argument_field_id": "dfdac2d4_7384_4916_8416_0bc42c29d36f",
     "field_id": "dfdac2d4_7384_4916_8416_0bc42c29d36f",
     "label": "jira_issue_key",
     "output_field_id": "dfdac2d4_7384_4916_8416_0bc42c29d36f",
     "type": "string"
    },
    {
     "argument_field_id": "display_name",
     "field_id": "display_name",
     "label": "name",
     "output_field_id": "display_name",
     "type": "string"
    },
    {
     "argument_field_id": "e2bf4aa4_a19c_4cbe_92b3_0ff50bcbbfbc",
     "field_id": "e2bf4aa4_a19c_4cbe_92b3_0ff50bcbbfbc",
     "label": "manifest",
     "output_field_id": "e2bf4aa4_a19c_4cbe_92b3_0ff50bcbbfbc",
     "type": "string"
    },
    {
     "argument_field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
     "field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
     "label": "deprecated",
     "output_field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
     "type": "boolean"
    },
    {
     "argument_field_id": "e6395bdd_5e77_4ce7_8dbc_256c798486f9",
     "field_id": "e6395bdd_5e77_4ce7_8dbc_256c798486f9",
     "label": "resume_token",
     "output_field_id": "e6395bdd_5e77_4ce7_8dbc_256c798486f9",
     "type": "string"
    },
    {
     "argument_field_id": "fc7aac95_0564_472c_a07f_9b20ba8e5a7b",
     "field_id": "fc7aac95_0564_472c_a07f_9b20ba8e5a7b",
     "label": "released",
     "output_field_id": "fc7aac95_0564_472c_a07f_9b20ba8e5a7b",
     "type": "boolean"
    },
    {
     "argument_field_id": "record_id",
     "field_id": "record_id",
     "label": "Record ID",
     "output_field_id": "record_id",
     "type": "string"
    }
   ],
   "name": "Package Versions",
   "public_id": "7199",
   "resource_kind": "data_table",
   "resource_ref": "resource_f360808d806b"
  },
  {
   "fields": [
    {
     "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "label": "Record ID",
     "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "type": "string"
    },
    {
     "argument_field_id": "25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e",
     "field_id": "25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e",
     "label": "name",
     "output_field_id": "25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e",
     "type": "string"
    },
    {
     "argument_field_id": "27bdf527_6657_412d_a106_293c28940a44",
     "field_id": "27bdf527_6657_412d_a106_293c28940a44",
     "label": "include_packaging_assets_for_installations",
     "output_field_id": "27bdf527_6657_412d_a106_293c28940a44",
     "type": "boolean"
    },
    {
     "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "label": "Updated at",
     "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "type": "date_time"
    },
    {
     "argument_field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
     "field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
     "label": "enabled",
     "output_field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
     "type": "boolean"
    },
    {
     "argument_field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
     "field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
     "label": "user_id",
     "output_field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
     "type": "string"
    },
    {
     "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "label": "Created at",
     "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "type": "date_time"
    },
    {
     "argument_field_id": "continuation_token",
     "field_id": "continuation_token",
     "label": "Next Page Token",
     "output_field_id": "continuation_token",
     "type": "string"
    },
    {
     "argument_field_id": "e12c33da_6a37_4ecd_86e1_9cb2dafd0787",
     "field_id": "e12c33da_6a37_4ecd_86e1_9cb2dafd0787",
     "label": "collection",
     "output_field_id": "e12c33da_6a37_4ecd_86e1_9cb2dafd0787",
     "type": "string"
    },
    {
     "argument_field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
     "field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
     "label": "access_profile_id",
     "output_field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
     "type": "string"
    }
   ],
   "name": "Workspaces",
   "public_id": "7201",
   "resource_kind": "data_table",
   "resource_ref": "resource_0f7c5bb6a482"
  },
  {
   "fields": [
    {
     "argument_field_id": "0f34f995_2a34_4fcf_b5c3_0270f8f718d0",
     "field_id": "0f34f995_2a34_4fcf_b5c3_0270f8f718d0",
     "label": "workspace",
     "output_field_id": "0f34f995_2a34_4fcf_b5c3_0270f8f718d0",
     "type": "string"
    },
    {
     "argument_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "label": "Record ID",
     "output_field_id": "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
     "type": "string"
    },
    {
     "argument_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "label": "Updated at",
     "output_field_id": "61aae604_a95e_4519_9091_bb0bf754a67f",
     "type": "date_time"
    },
    {
     "argument_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "label": "Created at",
     "output_field_id": "a5612739_5401_4ae7_bd07_782c1a6fb2d1",
     "type": "date_time"
    },
    {
     "argument_field_id": "continuation_token",
     "field_id": "continuation_token",
     "label": "Next Page Token",
     "output_field_id": "continuation_token",
     "type": "string"
    },
    {
     "argument_field_id": "db77c09c_5f9c_4681_8135_50f0c39af67a",
     "field_id": "db77c09c_5f9c_4681_8135_50f0c39af67a",
     "label": "package",
     "output_field_id": "db77c09c_5f9c_4681_8135_50f0c39af67a",
     "type": "string"
    },
    {
     "argument_field_id": "display_name",
     "field_id": "display_name",
     "label": "name",
     "output_field_id": "display_name",
     "type": "string"
    },
    {
     "argument_field_id": "fc952b5a_bf20_4985_a1bd_5cfa657e8c74",
     "field_id": "fc952b5a_bf20_4985_a1bd_5cfa657e8c74",
     "label": "$internal_value_fc952b5a-bf20-4985-a1bd-5cfa657e8c74",
     "output_field_id": "fc952b5a_bf20_4985_a1bd_5cfa657e8c74",
     "type": "string"
    },
    {
     "argument_field_id": "record_id",
     "field_id": "record_id",
     "label": "Record ID",
     "output_field_id": "record_id",
     "type": "string"
    }
   ],
   "name": "Workspace Package Installations",
   "public_id": "9008",
   "resource_kind": "data_table",
   "resource_ref": "resource_d9c99396091b"
  }
 ]
}

Begin. Emit your next action as JSON.
```

</details>

Subsequent ReAct inputs consist exactly of the preceding model action and
connector observation. Both are preserved turn by turn in the complete output
object below.

## Complete ReAct model and execution output

This is the complete per-instance `output` object. Its `steps` array preserves
each model thought/action and the exact observation supplied on the next turn;
its `trajectory` array preserves the corresponding structured connector calls
and results.

<details>
<summary>Complete ReAct output and interaction transcript</summary>

```json
{
  "failed_calls": 0,
  "final_answer": null,
  "final_snapshot": {
    "google_sheets": {
      "headers": [],
      "rows": [],
      "spreadsheet_id": "simulated-spreadsheet",
      "tab": "Sheet1",
      "values": [
        []
      ]
    },
    "lookup_table": {
      "tables": {}
    },
    "salesforce": {
      "records": []
    },
    "snowflake": {
      "tables": {}
    },
    "snowflake_live": {
      "physical_tables": {},
      "tables": {}
    },
    "workato_db_table": {
      "state_file": "<repo>/benchmark/outputs/full_eval/api-3models-clean-sim-global-react-20260814/_state_root/api-model-2/_state/workato_db_tables/102467097/variant_00/tables.json",
      "tables": {
        "7199": [
          {
            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "rec_001",
            "3c0b720b_bbe8_47de_a88d_96d759af819e": "2026-01-01",
            "622152c7_a09f_4d54_80f7_add539bee209": {
              "display_name": "Bench display_name",
              "record_id": "Bench record_id"
            },
            "_created_by": "seed",
            "_row_id": 0,
            "cc31f2eb_b841_498c_bced_247d9dd78edb": "Acme Approval",
            "e3bdb7a7_3561_48c0_b600_c210f5d64bb7": true,
            "id": "0"
          }
        ],
        "7201": [
          {
            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "ws_000",
            "25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e": "Acme Workspace",
            "73fd1e82_f4d2_48a9_8ff2_96713f5acd63": true,
            "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2": "U12345678",
            "_created_by": "seed",
            "_row_id": 0,
            "e417aefa_9690_4edd_83c5_8e3f8749fc24": "10",
            "id": "0"
          }
        ]
      }
    }
  },
  "plan": null,
  "plan_fidelity": {
    "applicable": false,
    "plan_condition_control_flow_exact": null,
    "plan_condition_control_flow_f1": null,
    "plan_coverage_exact": null,
    "plan_coverage_recall": null,
    "plan_fidelity_macro_f1": null,
    "plan_fidelity_pass": null,
    "plan_partial_order_exact": null,
    "plan_partial_order_f1": null,
    "plan_symbolic_arguments_exact": null,
    "plan_symbolic_arguments_f1": null,
    "plan_tool_selection_exact": null,
    "plan_tool_selection_f1": null
  },
  "plan_versions": [],
  "protocol_violations": 0,
  "replan_count": 0,
  "replan_events": [],
  "runtime_orchestration": {
    "condition_path_check_count": 1,
    "condition_path_checked": true,
    "condition_path_pass": true,
    "condition_path_passed_check_count": 1,
    "failed_read_attempt_count": 0,
    "failed_tool_attempt_count": 0,
    "orchestration_action_count_ratio": 1.0,
    "orchestration_efficiency_within_2x": true,
    "tool_argument_full_check_count": 3,
    "tool_argument_full_checked": true,
    "tool_argument_full_details": [
      {
        "agent_index": 0,
        "declared_execution_semantic_slots": [],
        "declared_result_semantic_slots": [],
        "declared_statement_semantic_slots": [],
        "gold_index": 0,
        "index": 0,
        "mode": "canonical_exact",
        "ok": true,
        "query_semantic_ok": false,
        "raw_ok": true,
        "required_mode": "raw_subset",
        "required_ok": true,
        "required_raw_ok": true,
        "semantic_mode": "raw_exact",
        "semantic_ok": true,
        "semantic_required_mode": "raw_subset",
        "semantic_required_ok": true,
        "tool": "workato_db_table.get_records"
      },
      {
        "agent_index": 1,
        "declared_execution_semantic_slots": [],
        "declared_result_semantic_slots": [],
        "declared_statement_semantic_slots": [],
        "gold_index": 1,
        "index": 1,
        "mode": "canonical_exact",
        "ok": true,
        "query_semantic_ok": false,
        "raw_ok": true,
        "required_mode": "raw_subset",
        "required_ok": true,
        "required_raw_ok": true,
        "semantic_mode": "raw_exact",
        "semantic_ok": true,
        "semantic_required_mode": "raw_subset",
        "semantic_required_ok": true,
        "tool": "workato_db_table.get_records"
      },
      {
        "agent_index": 2,
        "declared_execution_semantic_slots": [],
        "declared_result_semantic_slots": [],
        "declared_statement_semantic_slots": [],
        "gold_index": 2,
        "index": 2,
        "mode": "canonical_exact",
        "ok": true,
        "query_semantic_ok": false,
        "raw_ok": true,
        "required_mode": "raw_subset",
        "required_ok": true,
        "required_raw_ok": true,
        "semantic_mode": "raw_exact",
        "semantic_ok": true,
        "semantic_required_mode": "raw_subset",
        "semantic_required_ok": true,
        "tool": "workato_api_platform.return_response"
      }
    ],
    "tool_argument_full_pass": true,
    "tool_argument_full_passed_check_count": 3,
    "tool_argument_full_raw_check_count": 3,
    "tool_argument_full_raw_checked": true,
    "tool_argument_full_raw_pass": true,
    "tool_argument_full_raw_passed_check_count": 3,
    "tool_argument_full_semantic_pass": true,
    "tool_argument_required_check_count": 3,
    "tool_argument_required_checked": true,
    "tool_argument_required_pass": true,
    "tool_argument_required_passed_check_count": 3,
    "tool_argument_required_raw_check_count": 3,
    "tool_argument_required_raw_checked": true,
    "tool_argument_required_raw_pass": true,
    "tool_argument_required_raw_passed_check_count": 3,
    "tool_argument_required_semantic_pass": true,
    "tool_execution_success_check_count": 3,
    "tool_execution_success_checked": true,
    "tool_execution_success_pass": true,
    "tool_execution_success_passed_check_count": 3,
    "tool_order_check_count": 1,
    "tool_order_checked": true,
    "tool_order_dependency_edge_count": 3,
    "tool_order_dependency_mode": "dependency_dag",
    "tool_order_dependency_pass": true,
    "tool_order_dependency_spec_hash": "0fb1a534e557aea4b0bf6e3bb97d7809ecbe38574947bc629cf8cb20fa13bee6",
    "tool_order_exact_pass": true,
    "tool_order_mapped_gold_call_count": 3,
    "tool_order_mode": "canonical_exact",
    "tool_order_multiple_topological_orders": false,
    "tool_order_pass": true,
    "tool_order_passed_check_count": 1,
    "tool_order_public_temporal_requirement_count": 0,
    "tool_order_violations": [],
    "tool_selection_check_count": 1,
    "tool_selection_checked": true,
    "tool_selection_exact_pass": true,
    "tool_selection_extra_read_count": 0,
    "tool_selection_extra_read_tools": [],
    "tool_selection_extra_write_count": 0,
    "tool_selection_extra_write_tools": [],
    "tool_selection_pass": true,
    "tool_selection_passed_check_count": 1,
    "tool_selection_required_multiset_pass": true,
    "tool_selection_semantic_pass": true,
    "tool_trace_exact_pass": true,
    "unexpected_failed_tool_attempt_count": 0,
    "unexpected_failed_tool_attempt_exact_count": 0
  },
  "steps": [
    {
      "action": {
        "args": {
          "filters": [
            {
              "field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
              "op": "eq",
              "value": "10"
            },
            {
              "field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
              "op": "eq",
              "value": "U12345678"
            },
            {
              "field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
              "op": "eq",
              "value": true
            }
          ],
          "table_id": "7201"
        },
        "tool": "workato_db_table.get_records"
      },
      "observation": "{\"ok\": true, \"records\": [{\"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\": \"ws_000\", \"25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e\": \"Acme Workspace\", \"73fd1e82_f4d2_48a9_8ff2_96713f5acd63\": true, \"9d00233f_dc89_4f40_b0f4_c2b6ee765ed2\": \"U12345678\", \"_row_id\": 0, \"e417aefa_9690_4edd_83c5_8e3f8749fc24\": \"10\", \"id\": \"0\", \"_created_by\": \"seed\", \"record_id\": \"ws_000\"}]}",
      "thought": "First check authorization: table 7201 (Workspaces) with access_profile_id=10, user_id=U12345678, enabled=true."
    },
    {
      "action": {
        "args": {
          "filters": [
            {
              "field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
              "op": "eq",
              "value": true
            },
            {
              "field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
              "op": "gt",
              "value": "2025-01-01"
            }
          ],
          "limit": 200,
          "order_by_field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
          "order_direction": "asc",
          "table_id": "7199"
        },
        "tool": "workato_db_table.get_records"
      },
      "observation": "{\"ok\": true, \"records\": [{\"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\": \"rec_001\", \"3c0b720b_bbe8_47de_a88d_96d759af819e\": \"2026-01-01\", \"622152c7_a09f_4d54_80f7_add539bee209\": {\"display_name\": \"Bench display_name\", \"record_id\": \"Bench record_id\"}, \"_row_id\": 0, \"cc31f2eb_b841_498c_bced_247d9dd78edb\": \"Acme Approval\", \"e3bdb7a7_3561_48c0_b600_c210f5d64bb7\": true, \"id\": \"0\", \"_created_by\": \"seed\", \"record_id\": \"rec_001\"}]}",
      "thought": "Authorized. Now retrieve deprecated package versions from 7199 with deprecated=true and deprecated_at > 2025-01-01, ordered ascending, limit 200."
    },
    {
      "action": {
        "args": {
          "http_status_code": "200",
          "response": {
            "deprecations": [
              {
                "deprecated_at": "2026-01-01",
                "id": "rec_001",
                "name": "Acme Approval",
                "package_id": "Bench record_id",
                "package_name": "Bench display_name"
              }
            ]
          }
        },
        "tool": "workato_api_platform.return_response"
      },
      "observation": "{\"ok\": true, \"http_status_code\": \"200\", \"response\": {\"deprecations\": [{\"deprecated_at\": \"2026-01-01\", \"id\": \"rec_001\", \"name\": \"Acme Approval\", \"package_id\": \"Bench record_id\", \"package_name\": \"Bench display_name\"}]}}",
      "thought": "The actual observation shows one qualifying record. Field 622152c7 holds the linked package object with record_id and display_name (package id and name). Return 200 with that item."
    }
  ],
  "stop_reason": "terminal_tool",
  "trajectory": [
    {
      "args": {
        "filters": [
          {
            "field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
            "op": "eq",
            "value": "10"
          },
          {
            "field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
            "op": "eq",
            "value": "U12345678"
          },
          {
            "field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
            "op": "eq",
            "value": true
          }
        ],
        "table_id": "7201"
      },
      "result": {
        "ok": true,
        "records": [
          {
            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "ws_000",
            "25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e": "Acme Workspace",
            "73fd1e82_f4d2_48a9_8ff2_96713f5acd63": true,
            "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2": "U12345678",
            "_created_by": "seed",
            "_row_id": 0,
            "e417aefa_9690_4edd_83c5_8e3f8749fc24": "10",
            "id": "0",
            "record_id": "ws_000"
          }
        ]
      },
      "tool": "workato_db_table.get_records"
    },
    {
      "args": {
        "filters": [
          {
            "field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
            "op": "eq",
            "value": true
          },
          {
            "field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
            "op": "gt",
            "value": "2025-01-01"
          }
        ],
        "limit": 200,
        "order_by_field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
        "order_direction": "asc",
        "table_id": "7199"
      },
      "result": {
        "ok": true,
        "records": [
          {
            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "rec_001",
            "3c0b720b_bbe8_47de_a88d_96d759af819e": "2026-01-01",
            "622152c7_a09f_4d54_80f7_add539bee209": {
              "display_name": "Bench display_name",
              "record_id": "Bench record_id"
            },
            "_created_by": "seed",
            "_row_id": 0,
            "cc31f2eb_b841_498c_bced_247d9dd78edb": "Acme Approval",
            "e3bdb7a7_3561_48c0_b600_c210f5d64bb7": true,
            "id": "0",
            "record_id": "rec_001"
          }
        ]
      },
      "tool": "workato_db_table.get_records"
    },
    {
      "args": {
        "http_status_code": "200",
        "response": {
          "deprecations": [
            {
              "deprecated_at": "2026-01-01",
              "id": "rec_001",
              "name": "Acme Approval",
              "package_id": "Bench record_id",
              "package_name": "Bench display_name"
            }
          ]
        }
      },
      "result": {
        "http_status_code": "200",
        "ok": true,
        "response": {
          "deprecations": [
            {
              "deprecated_at": "2026-01-01",
              "id": "rec_001",
              "name": "Acme Approval",
              "package_id": "Bench record_id",
              "package_name": "Bench display_name"
            }
          ]
        }
      },
      "tool": "workato_api_platform.return_response"
    }
  ]
}
```

</details>

## Complete evaluator-only ground truth

The following is the complete `variant_00.json` file. Unlike the preceding
input blocks, this object is never shown to either model. It contains the
canonical workflow, active trace, grounded expected calls, expected connector
state, terminal contract and result, and private simulator seed.

<details>
<summary>Complete ground truth for recipe 102467097, variant 00</summary>

```json
{
  "active_trace": {
    "active_trace_hash": "22c013d46ce22455731d3690aa99bd9b4920f224cc2cfa0a8e2a7f5101b5388a",
    "events": [
      {
        "arguments": {
          "filters": [
            {
              "field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
              "op": "eq",
              "value": "10"
            },
            {
              "field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
              "op": "eq",
              "value": "U12345678"
            },
            {
              "field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
              "op": "eq",
              "value": true
            }
          ],
          "table_id": "7201"
        },
        "condition_output_observations": [
          {
            "path": [
              "records",
              "<size>"
            ],
            "value": 1
          }
        ],
        "event_type": "tool_call",
        "expected_status": "success",
        "plan_node_ref": "n1",
        "result_cardinality": "one",
        "tool": "workato_db_table.get_records"
      },
      {
        "branch": "try_success",
        "controller_source_ref": "step_5",
        "event_type": "branch_decision"
      },
      {
        "arguments": {
          "filters": [
            {
              "field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
              "op": "eq",
              "value": true
            },
            {
              "field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
              "op": "gt",
              "value": "2025-01-01"
            }
          ],
          "limit": 200,
          "order_by_field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
          "order_direction": "asc",
          "table_id": "7199"
        },
        "event_type": "tool_call",
        "expected_status": "success",
        "plan_node_ref": "n5",
        "result_cardinality": "one",
        "tool": "workato_db_table.get_records"
      },
      {
        "arguments": {
          "http_status_code": "200",
          "response": {
            "deprecations": [
              {
                "deprecated_at": "2026-01-01",
                "id": "rec_001",
                "name": "Acme Approval",
                "package_id": "Bench record_id",
                "package_name": "Bench display_name"
              }
            ]
          }
        },
        "event_type": "tool_call",
        "expected_status": "success",
        "plan_node_ref": "n6",
        "result_cardinality": null,
        "tool": "workato_api_platform.return_response"
      },
      {
        "condition_output_observations": [
          {
            "path": [
              "records",
              "<size>"
            ],
            "value": 1
          }
        ],
        "event_type": "condition_observation",
        "evidence": "executed_source_payload",
        "plan_node_ref": "n1"
      },
      {
        "branch": "condition_false",
        "controller_source_ref": "step_3",
        "event_type": "branch_decision"
      },
      {
        "event_type": "terminal",
        "terminal_type": "return"
      }
    ],
    "recipe_id": "102467097",
    "schema_version": "agentorch-active-trace-result-history",
    "variant_id": "00",
    "workflow_plan_hash": "560cbcaab0d05645d2003c9a5a1a5ea9de40cf74387a97329fea105f44651176"
  },
  "final_snapshot": {
    "ok": true,
    "workato_db_table": {
      "state_file": "output/_state/workato_db_tables/102467097/variant_00/tables.json",
      "tables": {
        "7199": [
          {
            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "rec_001",
            "3c0b720b_bbe8_47de_a88d_96d759af819e": "2026-01-01",
            "622152c7_a09f_4d54_80f7_add539bee209": {
              "display_name": "Bench display_name",
              "record_id": "Bench record_id"
            },
            "_created_by": "seed",
            "_row_id": 0,
            "cc31f2eb_b841_498c_bced_247d9dd78edb": "Acme Approval",
            "e3bdb7a7_3561_48c0_b600_c210f5d64bb7": true,
            "id": "0"
          }
        ],
        "7201": [
          {
            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "ws_000",
            "25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e": "Acme Workspace",
            "73fd1e82_f4d2_48a9_8ff2_96713f5acd63": true,
            "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2": "U12345678",
            "_created_by": "seed",
            "_row_id": 0,
            "e417aefa_9690_4edd_83c5_8e3f8749fc24": "10",
            "id": "0"
          }
        ]
      }
    }
  },
  "hidden_target_hash": "9decf66fd9da70106b4e1aec7c62db2ad1f526459000dee1ae685953d128d84f",
  "hidden_variant_state": {
    "expect": {
      "executed_action_count": 3,
      "tool_expectations": [
        {
          "args_contains": {
            "filters": [
              {
                "field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
                "op": "eq",
                "value": "10"
              },
              {
                "field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
                "op": "eq",
                "value": "U12345678"
              },
              {
                "field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
                "op": "eq",
                "value": true
              }
            ],
            "table_id": "7201"
          },
          "result_count": 1,
          "tool": "workato_db_table.get_records"
        },
        {
          "args_contains": {
            "filters": [
              {
                "field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
                "op": "eq",
                "value": true
              },
              {
                "field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
                "op": "gt",
                "value": "2025-01-01"
              }
            ],
            "table_id": "7199"
          },
          "result_count": 1,
          "tool": "workato_db_table.get_records"
        },
        {
          "args_contains": {
            "http_status_code": "200",
            "response": {
              "deprecations": [
                {
                  "deprecated_at": "2026-01-01",
                  "id": "rec_001",
                  "name": "Acme Approval",
                  "package_id": "Bench record_id",
                  "package_name": "Bench display_name"
                }
              ]
            }
          },
          "http_status_code": "200",
          "tool": "workato_api_platform.return_response"
        }
      ],
      "tools": [
        "workato_db_table.get_records",
        "workato_db_table.get_records",
        "workato_api_platform.return_response"
      ]
    },
    "private_evaluation_context": {},
    "recipe_id": "102467097",
    "seed": {
      "workato_db_table": {
        "tables": {
          "7199": [
            {
              "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "rec_001",
              "3c0b720b_bbe8_47de_a88d_96d759af819e": "2026-01-01",
              "622152c7_a09f_4d54_80f7_add539bee209": {
                "display_name": "Bench display_name",
                "record_id": "Bench record_id"
              },
              "_row_id": 0,
              "cc31f2eb_b841_498c_bced_247d9dd78edb": "Acme Approval",
              "e3bdb7a7_3561_48c0_b600_c210f5d64bb7": true,
              "id": "0"
            }
          ],
          "7201": [
            {
              "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "ws_000",
              "25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e": "Acme Workspace",
              "73fd1e82_f4d2_48a9_8ff2_96713f5acd63": true,
              "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2": "U12345678",
              "_row_id": 0,
              "e417aefa_9690_4edd_83c5_8e3f8749fc24": "10",
              "id": "0"
            }
          ]
        }
      }
    },
    "seed_sections": [
      "workato_db_table"
    ],
    "track": "answer",
    "variant": 0
  },
  "outcome_gold_calls": [
    {
      "args": {
        "filters": [
          {
            "field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
            "op": "eq",
            "value": "10"
          },
          {
            "field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
            "op": "eq",
            "value": "U12345678"
          },
          {
            "field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
            "op": "eq",
            "value": true
          }
        ],
        "table_id": "7201"
      },
      "result": {
        "ok": true,
        "records": [
          {
            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "ws_000",
            "25f333bd_9f2c_483e_a4d3_d9ee9f7fca8e": "Acme Workspace",
            "73fd1e82_f4d2_48a9_8ff2_96713f5acd63": true,
            "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2": "U12345678",
            "_created_by": "seed",
            "_row_id": 0,
            "e417aefa_9690_4edd_83c5_8e3f8749fc24": "10",
            "id": "0",
            "record_id": "ws_000"
          }
        ]
      },
      "tool": "workato_db_table.get_records"
    },
    {
      "args": {
        "filters": [
          {
            "field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
            "op": "eq",
            "value": true
          },
          {
            "field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
            "op": "gt",
            "value": "2025-01-01"
          }
        ],
        "limit": 200,
        "order_by_field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
        "order_direction": "asc",
        "table_id": "7199"
      },
      "result": {
        "ok": true,
        "records": [
          {
            "11fbe9a6_a16d_4d7e_86ea_afe42ec03005": "rec_001",
            "3c0b720b_bbe8_47de_a88d_96d759af819e": "2026-01-01",
            "622152c7_a09f_4d54_80f7_add539bee209": {
              "display_name": "Bench display_name",
              "record_id": "Bench record_id"
            },
            "_created_by": "seed",
            "_row_id": 0,
            "cc31f2eb_b841_498c_bced_247d9dd78edb": "Acme Approval",
            "e3bdb7a7_3561_48c0_b600_c210f5d64bb7": true,
            "id": "0",
            "record_id": "rec_001"
          }
        ]
      },
      "tool": "workato_db_table.get_records"
    },
    {
      "args": {
        "http_status_code": "200",
        "response": {
          "deprecations": [
            {
              "deprecated_at": "2026-01-01",
              "id": "rec_001",
              "name": "Acme Approval",
              "package_id": "Bench record_id",
              "package_name": "Bench display_name"
            }
          ]
        }
      },
      "result": {
        "http_status_code": "200",
        "ok": true,
        "response": {
          "deprecations": [
            {
              "deprecated_at": "2026-01-01",
              "id": "rec_001",
              "name": "Acme Approval",
              "package_id": "Bench record_id",
              "package_name": "Bench display_name"
            }
          ]
        }
      },
      "tool": "workato_api_platform.return_response"
    }
  ],
  "public_package_hash": "cc8b2f194d565934284d8d8338134870067233aebbb28ce9f0580be16b2698d4",
  "recipe_id": "102467097",
  "reference_tool_calls": [
    {
      "args": {
        "filters": [
          {
            "field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
            "op": "eq",
            "value": "10"
          },
          {
            "field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
            "op": "eq",
            "value": "U12345678"
          },
          {
            "field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
            "op": "eq",
            "value": true
          }
        ],
        "table_id": "7201"
      },
      "expected_status": "success",
      "plan_node_ref": "n1",
      "result": {
        "ok": true,
        "result_cardinality": "one"
      },
      "tool": "workato_db_table.get_records"
    },
    {
      "args": {
        "filters": [
          {
            "field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
            "op": "eq",
            "value": true
          },
          {
            "field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
            "op": "gt",
            "value": "2025-01-01"
          }
        ],
        "limit": 200,
        "order_by_field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
        "order_direction": "asc",
        "table_id": "7199"
      },
      "expected_status": "success",
      "plan_node_ref": "n5",
      "result": {
        "ok": true,
        "result_cardinality": "one"
      },
      "tool": "workato_db_table.get_records"
    },
    {
      "args": {
        "http_status_code": "200",
        "response": {
          "deprecations": [
            {
              "deprecated_at": "2026-01-01",
              "id": "rec_001",
              "name": "Acme Approval",
              "package_id": "Bench record_id",
              "package_name": "Bench display_name"
            }
          ]
        }
      },
      "expected_status": "success",
      "plan_node_ref": "n6",
      "result": {
        "http_status_code": "200",
        "ok": true,
        "response": {
          "deprecations": [
            {
              "deprecated_at": "2026-01-01",
              "id": "rec_001",
              "name": "Acme Approval",
              "package_id": "Bench record_id",
              "package_name": "Bench display_name"
            }
          ]
        }
      },
      "tool": "workato_api_platform.return_response"
    }
  ],
  "schema": "agentorch-private-ground-truth",
  "structural_return": {
    "present": false,
    "value": null
  },
  "terminal_contract": {
    "declared_responses": [
      {
        "body_schema": [
          {
            "label": "Deprecations",
            "name": "deprecations",
            "of": "object",
            "optional": false,
            "properties": [
              {
                "control_type": "text",
                "label": "ID",
                "name": "id",
                "optional": false,
                "type": "string"
              },
              {
                "control_type": "text",
                "label": "Name",
                "name": "name",
                "optional": false,
                "type": "string"
              },
              {
                "control_type": "text",
                "label": "Package ID",
                "name": "package_id",
                "optional": false,
                "type": "string"
              },
              {
                "control_type": "text",
                "label": "Package name",
                "name": "package_name",
                "optional": false,
                "type": "string"
              },
              {
                "control_type": "date_time",
                "label": "Deprecated at",
                "name": "deprecated_at",
                "optional": false,
                "parse_output": "date_time_conversion",
                "render_input": "date_time_conversion",
                "type": "date_time"
              }
            ],
            "type": "array"
          }
        ],
        "content_type": "json",
        "delivery": "explicit_tool_call",
        "http_status_code": "200",
        "name": "Success"
      },
      {
        "body_schema": [
          {
            "control_type": "text",
            "label": "Error",
            "name": "error",
            "optional": false,
            "type": "string"
          }
        ],
        "content_type": "json",
        "delivery": "explicit_tool_call",
        "http_status_code": "400",
        "name": "Failed"
      },
      {
        "body_schema": [],
        "content_type": "json",
        "delivery": "explicit_tool_call",
        "http_status_code": "401",
        "name": "Unauthorized"
      }
    ],
    "scalar_encoding_semantics": {
      "workato_checkbox_control": "Boolean-declared checkbox controls accept JSON booleans or the authoring strings true and false.",
      "workato_numeric_control": "Integer and number response controls accept mathematically compatible numeric expressions; numeric strings are coerced by controls that declare numeric output conversion.",
      "workato_text_control": "String-declared text controls accept string, integer, number, or boolean scalar expressions and apply Workato's text coercion."
    },
    "schema_version": "public-output-interface"
  },
  "terminal_result": {
    "deprecations": [
      {
        "deprecated_at": "2026-01-01",
        "id": "rec_001",
        "name": "Acme Approval",
        "package_id": "Bench record_id",
        "package_name": "Bench display_name"
      }
    ]
  },
  "terminal_result_known": true,
  "tool_expectations": [
    {
      "args_contains": {
        "filters": [
          {
            "field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
            "op": "eq",
            "value": "10"
          },
          {
            "field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
            "op": "eq",
            "value": "U12345678"
          },
          {
            "field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
            "op": "eq",
            "value": true
          }
        ],
        "table_id": "7201"
      },
      "expected_status": "success",
      "result_cardinality": "one",
      "tool": "workato_db_table.get_records"
    },
    {
      "args_contains": {
        "filters": [
          {
            "field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7",
            "op": "eq",
            "value": true
          },
          {
            "field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
            "op": "gt",
            "value": "2025-01-01"
          }
        ],
        "limit": 200,
        "order_by_field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
        "order_direction": "asc",
        "table_id": "7199"
      },
      "expected_status": "success",
      "result_cardinality": "one",
      "tool": "workato_db_table.get_records"
    },
    {
      "args_contains": {
        "http_status_code": "200",
        "response": {
          "deprecations": [
            {
              "deprecated_at": "2026-01-01",
              "id": "rec_001",
              "name": "Acme Approval",
              "package_id": "Bench record_id",
              "package_name": "Bench display_name"
            }
          ]
        }
      },
      "expected_status": "success",
      "tool": "workato_api_platform.return_response"
    }
  ],
  "variant_id": "00",
  "workflow_plan": {
    "compiler_version": "workflow-a-compiler-v2",
    "recipe_id": "102467097",
    "schema_version": "agentorch-workflow-plan-v1",
    "workflow": [
      {
        "arguments": {
          "filters": {
            "expression": {
              "items": [
                {
                  "expression": {
                    "fields": {
                      "field_id": {
                        "literal": "e417aefa_9690_4edd_83c5_8e3f8749fc24"
                      },
                      "op": {
                        "literal": "eq"
                      },
                      "value": {
                        "input_ref": "context.access_profile.id"
                      }
                    },
                    "op": "object"
                  }
                },
                {
                  "expression": {
                    "fields": {
                      "field_id": {
                        "literal": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2"
                      },
                      "op": {
                        "literal": "eq"
                      },
                      "value": {
                        "input_ref": "request.workspace_user_id"
                      }
                    },
                    "op": "object"
                  }
                },
                {
                  "expression": {
                    "fields": {
                      "field_id": {
                        "literal": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63"
                      },
                      "op": {
                        "literal": "eq"
                      },
                      "value": {
                        "literal": true
                      }
                    },
                    "op": "object"
                  }
                }
              ],
              "op": "array"
            }
          },
          "table_id": {
            "literal": "7201"
          }
        },
        "id": "n1",
        "kind": "call",
        "tool": "workato_db_table.get_records"
      },
      {
        "condition": {
          "expression": {
            "fields": {
              "conditions": {
                "expression": {
                  "items": [
                    {
                      "expression": {
                        "fields": {
                          "lhs": {
                            "output_ref": {
                              "node": "n1",
                              "path": [
                                "records",
                                "<size>"
                              ]
                            }
                          },
                          "operand": {
                            "literal": "equals_to"
                          },
                          "rhs": {
                            "literal": "0"
                          }
                        },
                        "op": "object"
                      }
                    }
                  ],
                  "op": "array"
                }
              },
              "operand": {
                "literal": "and"
              },
              "type": {
                "literal": "compound"
              }
            },
            "op": "object"
          }
        },
        "else": [],
        "id": "n2",
        "kind": "if",
        "then": [
          {
            "arguments": {
              "http_status_code": {
                "literal": "401"
              },
              "response": {
                "expression": {
                  "fields": {},
                  "op": "object"
                }
              }
            },
            "id": "n3",
            "kind": "call",
            "tool": "workato_api_platform.return_response"
          }
        ]
      },
      {
        "body": [
          {
            "arguments": {
              "filters": {
                "expression": {
                  "items": [
                    {
                      "expression": {
                        "fields": {
                          "field_id": {
                            "literal": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7"
                          },
                          "op": {
                            "literal": "eq"
                          },
                          "value": {
                            "literal": true
                          }
                        },
                        "op": "object"
                      }
                    },
                    {
                      "expression": {
                        "fields": {
                          "field_id": {
                            "literal": "3c0b720b_bbe8_47de_a88d_96d759af819e"
                          },
                          "op": {
                            "literal": "gt"
                          },
                          "value": {
                            "input_ref": "request.deprecated_since"
                          }
                        },
                        "op": "object"
                      }
                    }
                  ],
                  "op": "array"
                }
              },
              "limit": {
                "literal": 200
              },
              "order_by_field_id": {
                "literal": "3c0b720b_bbe8_47de_a88d_96d759af819e"
              },
              "order_direction": {
                "literal": "asc"
              },
              "table_id": {
                "literal": "7199"
              }
            },
            "id": "n5",
            "kind": "call",
            "tool": "workato_db_table.get_records"
          },
          {
            "arguments": {
              "http_status_code": {
                "literal": "200"
              },
              "response": {
                "expression": {
                  "fields": {
                    "deprecations": {
                      "expression": {
                        "args": [
                          {
                            "output_ref": {
                              "node": "n5",
                              "path": [
                                "records"
                              ]
                            }
                          }
                        ],
                        "item_bind": "map_41fe5346_item_1",
                        "op": "map",
                        "value": {
                          "expression": {
                            "fields": {
                              "deprecated_at": {
                                "loop_ref": {
                                  "path": [
                                    "3c0b720b_bbe8_47de_a88d_96d759af819e"
                                  ],
                                  "source_node": "map_41fe5346_item_1"
                                }
                              },
                              "id": {
                                "loop_ref": {
                                  "path": [
                                    "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
                                  ],
                                  "source_node": "map_41fe5346_item_1"
                                }
                              },
                              "name": {
                                "loop_ref": {
                                  "path": [
                                    "cc31f2eb_b841_498c_bced_247d9dd78edb"
                                  ],
                                  "source_node": "map_41fe5346_item_1"
                                }
                              },
                              "package_id": {
                                "loop_ref": {
                                  "path": [
                                    "622152c7_a09f_4d54_80f7_add539bee209",
                                    "record_id"
                                  ],
                                  "source_node": "map_41fe5346_item_1"
                                }
                              },
                              "package_name": {
                                "loop_ref": {
                                  "path": [
                                    "622152c7_a09f_4d54_80f7_add539bee209",
                                    "display_name"
                                  ],
                                  "source_node": "map_41fe5346_item_1"
                                }
                              }
                            },
                            "op": "object"
                          }
                        }
                      }
                    }
                  },
                  "op": "object"
                }
              }
            },
            "id": "n6",
            "kind": "call",
            "tool": "workato_api_platform.return_response"
          }
        ],
        "catch": [
          {
            "arguments": {
              "http_status_code": {
                "literal": "400"
              },
              "response": {
                "expression": {
                  "fields": {
                    "error": {
                      "literal": "Unexpected Error"
                    }
                  },
                  "op": "object"
                }
              }
            },
            "id": "n7",
            "kind": "call",
            "tool": "workato_api_platform.return_response"
          }
        ],
        "id": "n4",
        "kind": "try"
      }
    ],
    "workflow_a_hash": "6d23918fcd37990edb7ed85c1f550122ccc907e6391eb8e664dda2303f4ff9f8",
    "workflow_plan_hash": "560cbcaab0d05645d2003c9a5a1a5ea9de40cf74387a97329fea105f44651176"
  },
  "workflow_plan_hash": "560cbcaab0d05645d2003c9a5a1a5ea9de40cf74387a97329fea105f44651176"
}
```

</details>

## Interpretation

Both settings identify the correct authorization check, protected data query,
and terminal response tool. The Global View failure is narrower than a wrong
tool choice: it is a value-projection error caused by committing to a symbolic
path before the runtime representation is visible. The package field
`622152c7_a09f_4d54_80f7_add539bee209` resolves to an object, but the frozen
plan assigns that entire object to the scalar `package_id` and seeks
`display_name` outside the object. The resulting response has an object-valued
`package_id` and a null `package_name`.

ReAct uses the same three business calls in the same order. After the second
call, however, it sees that the package reference is nested and projects
`record_id` and `display_name` from the observed object. This case therefore
isolates the benefit of runtime observation: interaction fixes a concrete
data-shape ambiguity without changing tool selection, tool order, or state
effects.
