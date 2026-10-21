from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_88707332


RECIPE_ID = "88707332"
SEED_TYPE = "workato_service_get_accountid_variant"
TRACK = "live_salesforce_get_accountid_service"
TRIGGER_PROVIDER = "workato_service"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "receive_request"
# Callable service "Get AccountID" (GET /getacct; request {Customer string};
# reply {AccountID[]{accountId,accountName}, Found bool, Multiple bool}).
#
#   TRY (step 2):
#     IF (3) Customer blank -> send_reply__16 error "No search term provided..."
#       + graceful STOP (5).
#     IF (6) Customer present (PROVABLY always true when reached: the blank
#       branch stops first and blank/present are exact complements -> the false
#       side is dead code, no variant):
#       logger.log_message (7) multi-line if/elsif classifier ->
#         "Email" (matches /.+@.+\..+/) / "Domain" (contains '.') / "Name".
#       IF (8) message == Email OR message == Domain:
#         salesforce.search_sobjects_soql__1 (9): Contact SOQL built by string
#           concat: "AccountId != null AND (Email LIKE '%<dom>' OR
#           User_Email__c LIKE '%@<dom>')" where <dom> = Customer.split("@").last.
#         lookup_table.search_entries (10): table 1492777 'Freemail providers',
#           parameters.col1 = <dom>.
#         IF (11) message==Domain OR Contact size==0 OR =(Contact ____Size>0
#           and entries ____Size==0):
#           salesforce.search_sobjects (12): Domain__c by Domain__c=<dom>.
#           IF (13) Domain__c size>0 -> send_reply__15 (14) from
#             Domain__c Account__c / Account__r.Name + STOP (15).
#         IF (16) Contact==1 AND lookup<1 -> accumulate 'Accounts' (17) +
#           send_reply__2 (18) from that list + STOP (19).
#         IF (20) Contact==1 AND lookup>0 -> logger '=' (21) + accumulate__3
#           (22) + send_reply__8 (23; raw-recipe quirk: pills reference the
#           step-17 list which never ran in this branch -> AccountID []) +
#           STOP (24).
#         IF (25) Contact>1:
#           IF (26) Email -> FOREACH (27) accumulate__1 'Contacts';
#             smart_list create 'Contacts' (29); query_list (30) exact
#             Email/User_Email match; IF (31)==1 reply (32)+STOP / IF (34)>1
#             reply__4 (35)+STOP / IF (37)==0 -> query__2 (38) SELECT DISTINCT
#             + reply__3 (39)+STOP.
#           IF (41) Domain AND lookup<1 -> FOREACH (42) accumulate__6
#             'Accounts'; create__1 (44); query__1 (45) SELECT DISTINCT;
#             IF (46)==1 reply__9 (47)+STOP / IF (49)>1 reply__11 (50)+STOP.
#             (rows==0 is PROVABLY dead: the DISTINCT of >=2 accumulated rows
#             is >=1, so the fall-through no-reply edge cannot fire.)
#           IF (52) Domain AND lookup>0 -> send_reply__13 (53) Found=false +
#             STOP (54).
#       IF (55) message==Name OR =(Contact ____Size==0 and Domain__c
#         ____Size==0):
#         logger d8cbbff7 (56) Customer.gsub(/\'/, "%");
#         salesforce.search_sobjects_soql (57): "Name LIKE '%" + (message ==
#           "Domain" ? Customer.split(".")[0] : d8cbbff7.message) + "%'".
#         IF (58)==0 reply__5 (59)+STOP / IF (61)>1 reply__6 (62)+STOP /
#         IF (64)==1 reply__7 (65)+STOP.
#   CATCH (67, as=catch, max_retry_count=0) -> send_reply__14 (68) error with
#     the catch message pill.
#
# Live backend: Salesforce (Account / Contact / Domain__c custom object /
# Contact.User_Email__c custom field; benchmark-owned, deleted in cleanup).
# Workato-internal (deterministic mock): workato_service reply, lookup_table
# 1492777, workato_list accumulate, workato_smart_list, logger.
#
# Live-faithfulness notes:
# - Every Salesforce variant sets seed.salesforce.strict_soql_conditions: the
#   step-9 SOQL "AccountId != null AND (Email LIKE '%<dom>' OR User_Email__c
#   LIKE '%@<dom>')" needs the recursive paren-aware strict evaluator (landed
#   2026-07-07); unsupported leaves still raise instead of silently matching.
# - Contact/Domain__c variants set seed.salesforce.relationship_expansion so
#   the Contact.Account.{Id,Name} and Domain__c Account__r.Name pills resolve
#   against live parent read-backs.
# - Steps 17/22 reference the Contact list's current_item OUTSIDE a foreach;
#   the engine resolves that to the first row, and both owning branches
#   require Contact size == 1, so first == only (probed).
# - send_reply__8 (IF 20) sources AccountID from the step-17 list that never
#   ran in that branch (raw-recipe quirk): the faithful reply carries
#   AccountID [] (probed: a never-run ____source mapping resolves to []).
# - send_reply__15 (IF 13) maps AccountID fields WITHOUT a ____source binding
#   (unlike every other reply), so the faithful reply carries a single OBJECT
#   {accountId, accountName} resolved from the Domain__c list's first row,
#   not an array (probed).
# - Seeds keep harness LIKE chunk-matching and real SOQL LIKE semantics
#   aligned (no domain-suffix lookalikes such as "x@acme.io.org").

EXPECTED_ACTIONS: list[tuple[int, str, str, str]] = [
    (4, 'send_reply__16', 'workato_service', 'send_reply'),
    (7, 'log_message', 'logger', 'log_message'),
    (9, 'search_sobjects_soql__1', 'salesforce', 'search_sobjects_soql'),
    (10, 'search_entries', 'lookup_table', 'search_entries'),
    (12, 'search_sobjects', 'salesforce', 'search_sobjects'),
    (14, 'send_reply__15', 'workato_service', 'send_reply'),
    (17, 'accumulate_list_items', 'workato_list', 'accumulate_list_items'),
    (18, 'send_reply__2', 'workato_service', 'send_reply'),
    (21, 'log_message__2', 'logger', 'log_message'),
    (22, 'accumulate_list_items__3', 'workato_list', 'accumulate_list_items'),
    (23, 'send_reply__8', 'workato_service', 'send_reply'),
    (28, 'accumulate_list_items__1', 'workato_list', 'accumulate_list_items'),
    (29, 'create_list', 'workato_smart_list', 'create_list'),
    (30, 'query_list', 'workato_smart_list', 'query_list'),
    (32, 'send_reply', 'workato_service', 'send_reply'),
    (35, 'send_reply__4', 'workato_service', 'send_reply'),
    (38, 'query_list__2', 'workato_smart_list', 'query_list'),
    (39, 'send_reply__3', 'workato_service', 'send_reply'),
    (43, 'accumulate_list_items__6', 'workato_list', 'accumulate_list_items'),
    (44, 'create_list__1', 'workato_smart_list', 'create_list'),
    (45, 'query_list__1', 'workato_smart_list', 'query_list'),
    (47, 'send_reply__9', 'workato_service', 'send_reply'),
    (50, 'send_reply__11', 'workato_service', 'send_reply'),
    (53, 'send_reply__13', 'workato_service', 'send_reply'),
    (56, 'd8cbbff7', 'logger', 'log_message'),
    (57, 'search_sobjects_soql', 'salesforce', 'search_sobjects_soql'),
    (59, 'send_reply__5', 'workato_service', 'send_reply'),
    (62, 'send_reply__6', 'workato_service', 'send_reply'),
    (65, 'send_reply__7', 'workato_service', 'send_reply'),
    (68, 'send_reply__14', 'workato_service', 'send_reply'),
]
ACTION_INPUTS: dict[str, dict[str, Any]] = {
    'send_reply__16': {'message': 'No search term provided. Please enter a search term.', 'reply_type': 'error'},
    'log_message': {'message': '=if '
                "_('data.workato_service.receive_request.request.Customer').match?(/.+@.+\\..+/)\n"
                '  "Email"\n'
                'elsif _(\'data.workato_service.receive_request.request.Customer\').include?(".")\n'
                '  "Domain"\n'
                'else\n'
                '  "Name"\n'
                'end'},
    'search_sobjects_soql__1': {'field_list': 'Account$Account ID.Id\nAccount$Account ID.Name\nEmail\nUser_Email__c',
     'limit': '150',
     'query': '="AccountId != null AND (Email LIKE '
              '\'%"+_(\'data.workato_service.receive_request.request.Customer\').split("@").last+"\' '
              'OR User_Email__c LIKE '
              '\'%@"+_(\'data.workato_service.receive_request.request.Customer\').split("@").last+"\')"',
     'sobject_name': 'Contact',
     'table_list': 'Account'},
    'search_entries': {'lookup_table_id': '1492777',
     'parameters': {'col1': '=_(\'data.workato_service.receive_request.request.Customer\').split("@").last'}},
    'search_sobjects': {'Domain__c': '=_(\'data.workato_service.receive_request.request.Customer\').split("@").last',
     'field_list': 'Account__c\nAccount__r$Account.Name',
     'sobject_name': 'Domain__c',
     'table_list': 'Account'},
    'send_reply__15': {'reply': {'AccountID': {'accountId': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects","path":["Domain__c", '
                                          '{"path_element_type": "current_item"}, '
                                          '"Account__c"]}\')}',
                             'accountName': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects","path":["Domain__c", '
                                            '{"path_element_type": "current_item"}, "Account__r", '
                                            '"Name"]}\')}'},
               'Found': 'true',
               'Multiple': 'false'},
     'reply_type': 'success'},
    'accumulate_list_items': {'list_item': {'data': {'account_id': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql__1","path":["Contact", '
                                          '{"path_element_type": "current_item"}, "Account", '
                                          '"Id"]}\')}',
                            'account_name': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql__1","path":["Contact", '
                                            '{"path_element_type": "current_item"}, "Account", '
                                            '"Name"]}\')}'},
                   'schema': '[{"name":"account_id","type":"string","optional":true,"label":"Account '
                             'Id","control_type":"text"},{"name":"account_name","type":"string","optional":true,"label":"Account '
                             'Name","control_type":"text"}]'},
     'name': 'Accounts'},
    'send_reply__2': {'reply': {'AccountID': {'____source': '#{_dp(\'{"pill_type":"output","provider":"workato_list","line":"accumulate_list_items","path":["list_items"]}\')}',
                             'accountId': '#{_dp(\'{"pill_type":"output","provider":"workato_list","line":"accumulate_list_items","path":["list_items", '
                                          '{"path_element_type": "current_item"}, '
                                          '"account_id"]}\')}',
                             'accountName': '#{_dp(\'{"pill_type":"output","provider":"workato_list","line":"accumulate_list_items","path":["list_items", '
                                            '{"path_element_type": "current_item"}, '
                                            '"account_name"]}\')}'},
               'Found': 'true',
               'Multiple': 'false'},
     'reply_type': 'success'},
    'log_message__2': {'message': '='},
    'accumulate_list_items__3': {'list_item': {'data': {'account_id': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql__1","path":["Contact", '
                                          '{"path_element_type": "current_item"}, "Account", '
                                          '"Id"]}\')}',
                            'account_name': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql__1","path":["Contact", '
                                            '{"path_element_type": "current_item"}, "Account", '
                                            '"Name"]}\')}'},
                   'schema': '[{"name":"account_id","type":"string","optional":true,"label":"Account '
                             'Id","control_type":"text"},{"name":"account_name","type":"string","optional":true,"label":"Account '
                             'Name","control_type":"text"}]'},
     'name': 'Accounts'},
    'send_reply__8': {'reply': {'AccountID': {'____source': '#{_dp(\'{"pill_type":"output","provider":"workato_list","line":"accumulate_list_items","path":["list_items"]}\')}',
                             'accountId': '#{_dp(\'{"pill_type":"output","provider":"workato_list","line":"accumulate_list_items","path":["list_items", '
                                          '{"path_element_type": "current_item"}, '
                                          '"account_id"]}\')}',
                             'accountName': '#{_dp(\'{"pill_type":"output","provider":"workato_list","line":"accumulate_list_items","path":["list_items", '
                                            '{"path_element_type": "current_item"}, '
                                            '"account_name"]}\')}'},
               'Found': 'true',
               'Multiple': 'false'},
     'reply_type': 'success'},
    'accumulate_list_items__1': {'list_item': {'data': {'account_id': "=_('data.foreach.foreach.Account.Id')",
                            'account_name': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"foreach","path":["Account", '
                                            '"Name"]}\')}',
                            'email': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"foreach","path":["Email"]}\')}',
                            'user_email': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"foreach","path":["User_Email__c"]}\')}'},
                   'schema': '[{"name":"account_id","type":"string","optional":true,"label":"Account '
                             'Id","control_type":"text"},{"name":"account_name","type":"string","optional":true,"label":"Account '
                             'Name","control_type":"text"},{"name":"email","type":"string","optional":true,"label":"Email","control_type":"text"},{"name":"user_email","type":"string","optional":true,"label":"User '
                             'Email","control_type":"text"}]'},
     'name': 'Contacts'},
    'create_list': {'list_name': 'Contacts',
     'list_source': "=_('data.workato_list.accumulate_list_items__1.list_items')",
     'primary_index': 'account_id'},
    'query_list': {'col_sep': 'comma',
     'csv': 'false',
     'headers': 'false',
     'result_schema_json': '[{"name":"Account_Name","type":"string","control_type":"text"},{"name":"Account_Id","type":"string","control_type":"text"}]',
     'sql': 'SELECT account_name, Account_Id FROM Contacts WHERE Email = '
            '\'#{_dp(\'{"pill_type":"output","provider":"workato_service","line":"receive_request","path":["request", '
            '"Customer"]}\')}\' OR User_Email = '
            '\'#{_dp(\'{"pill_type":"output","provider":"workato_service","line":"receive_request","path":["request", '
            '"Customer"]}\')}\''},
    'send_reply': {'reply': {'AccountID': {'____source': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list","path":["rows"]}\')}',
                             'accountId': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list","path":["rows", '
                                          '{"path_element_type": "current_item"}, '
                                          '"Account_Id"]}\')}',
                             'accountName': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list","path":["rows", '
                                            '{"path_element_type": "current_item"}, '
                                            '"Account_Name"]}\')}'},
               'Found': 'true',
               'Multiple': 'false'},
     'reply_type': 'success'},
    'send_reply__4': {'reply': {'AccountID': {'____source': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list","path":["rows"]}\')}',
                             'accountId': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list","path":["rows", '
                                          '{"path_element_type": "current_item"}, '
                                          '"Account_Id"]}\')}',
                             'accountName': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list","path":["rows", '
                                            '{"path_element_type": "current_item"}, '
                                            '"Account_Name"]}\')}'},
               'Found': 'true',
               'Multiple': 'true'},
     'reply_type': 'success'},
    'query_list__2': {'col_sep': 'comma',
     'csv': 'false',
     'headers': 'false',
     'result_schema_json': '[{"name":"Account_Name","type":"string","control_type":"text"},{"name":"Account_Id","type":"string","control_type":"text"}]',
     'sql': 'SELECT DISTINCT Account_Name, Account_Id FROM Contacts'},
    'send_reply__3': {'reply': {'AccountID': {'____source': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list__2","path":["rows"]}\')}',
                             'accountId': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list__2","path":["rows", '
                                          '{"path_element_type": "current_item"}, '
                                          '"Account_Id"]}\')}',
                             'accountName': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list__2","path":["rows", '
                                            '{"path_element_type": "current_item"}, '
                                            '"Account_Name"]}\')}'},
               'Found': 'false',
               'Multiple': 'true'},
     'reply_type': 'success'},
    'accumulate_list_items__6': {'list_item': {'data': {'account_id': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"foreach__2","path":["Account", '
                                          '"Id"]}\')}',
                            'account_name': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"foreach__2","path":["Account", '
                                            '"Name"]}\')}'},
                   'schema': '[{"name":"account_id","type":"string","optional":true,"label":"Account '
                             'Id","control_type":"text"},{"name":"account_name","type":"string","optional":true,"label":"Account '
                             'Name","control_type":"text"}]'},
     'name': 'Accounts'},
    'create_list__1': {'list_name': 'Accounts',
     'list_source': "=_('data.workato_list.accumulate_list_items__6.list_items')",
     'primary_index': 'account_id'},
    'query_list__1': {'col_sep': 'comma',
     'csv': 'false',
     'headers': 'false',
     'result_schema_json': '[{"name":"account_name","type":"string","control_type":"text"},{"name":"account_id","type":"string","control_type":"text"}]',
     'sql': 'SELECT DISTINCT account_name, account_id FROM Accounts'},
    'send_reply__9': {'reply': {'AccountID': {'____source': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list__1","path":["rows"]}\')}',
                             'accountId': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list__1","path":["rows", '
                                          '{"path_element_type": "current_item"}, '
                                          '"account_id"]}\')}',
                             'accountName': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list__1","path":["rows", '
                                            '{"path_element_type": "current_item"}, '
                                            '"account_name"]}\')}'},
               'Found': 'true',
               'Multiple': 'false'},
     'reply_type': 'success'},
    'send_reply__11': {'reply': {'AccountID': {'____source': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list__1","path":["rows"]}\')}',
                             'accountId': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list__1","path":["rows", '
                                          '{"path_element_type": "current_item"}, '
                                          '"account_id"]}\')}',
                             'accountName': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list__1","path":["rows", '
                                            '{"path_element_type": "current_item"}, '
                                            '"account_name"]}\')}'},
               'Found': 'true',
               'Multiple': 'true'},
     'reply_type': 'success'},
    'send_reply__13': {'reply': {'Found': 'false', 'Multiple': 'false'}, 'reply_type': 'success'},
    'd8cbbff7': {'message': '=_(\'data.workato_service.receive_request.request.Customer\').gsub(/\\\'/, "%")'},
    'search_sobjects_soql': {'field_list': 'Id\nName',
     'limit': '150',
     'query': '="Name LIKE \'%" + (_(\'data.logger.log_message.message\') == "Domain" ?  '
              '_(\'data.workato_service.receive_request.request.Customer\').split(".")[0] : '
              '_(\'data.logger.d8cbbff7.message\')) + "%\'"',
     'sobject_name': 'Account',
     'table_list': 'Account_sobject'},
    'send_reply__5': {'reply': {'Found': 'false', 'Multiple': 'false'}, 'reply_type': 'success'},
    'send_reply__6': {'reply': {'AccountID': {'____source': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql","path":["Account"]}\')}',
                             'accountId': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql","path":["Account", '
                                          '{"path_element_type": "current_item"}, "Id"]}\')}',
                             'accountName': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql","path":["Account", '
                                            '{"path_element_type": "current_item"}, "Name"]}\')}'},
               'Found': 'true',
               'Multiple': 'true'},
     'reply_type': 'success'},
    'send_reply__7': {'reply': {'AccountID': {'____source': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql","path":["Account"]}\')}',
                             'accountId': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql","path":["Account", '
                                          '{"path_element_type": "current_item"}, "Id"]}\')}',
                             'accountName': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql","path":["Account", '
                                            '{"path_element_type": "current_item"}, "Name"]}\')}'},
               'Found': 'true',
               'Multiple': 'false'},
     'reply_type': 'success'},
    'send_reply__14': {'message': '#{_dp(\'{"pill_type":"output","provider":"catch","line":"catch","path":["message"]}\')}',
     'reply_type': 'error'},
}
IF_CONDITIONS: dict[int, dict[str, Any]] = {
    3: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_service","line":"receive_request","path":["request", '
                            '"Customer"]}\')}',
                     'operand': 'blank'}],
     'operand': 'and',
     'type': 'compound'},
    6: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_service","line":"receive_request","path":["request", '
                            '"Customer"]}\')}',
                     'operand': 'present'}],
     'operand': 'and',
     'type': 'compound'},
    8: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"logger","line":"log_message","path":["message"]}\')}',
                     'operand': 'equals_to',
                     'rhs': 'Email'},
                    {'lhs': '#{_dp(\'{"pill_type":"output","provider":"logger","line":"log_message","path":["message"]}\')}',
                     'operand': 'equals_to',
                     'rhs': 'Domain'}],
     'operand': 'or',
     'type': 'compound'},
    11: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"logger","line":"log_message","path":["message"]}\')}',
                     'operand': 'equals_to',
                     'rhs': 'Domain'},
                    {'lhs': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql__1","path":["Contact", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'equals_to',
                     'rhs': '0'},
                    {'lhs': "=(_('data.salesforce.search_sobjects_soql__1.Contact.first.____Size', "
                            "'list_meta', '____Size', "
                            "'data.salesforce.search_sobjects_soql__1.Contact') > 0 and "
                            "_('data.lookup_table.search_entries.entries.first.____Size', "
                            "'list_meta', '____Size', 'data.lookup_table.search_entries.entries') "
                            '== 0)',
                     'operand': 'is_true'}],
     'operand': 'or',
     'type': 'compound'},
    13: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects","path":["Domain__c", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'greater_than',
                     'rhs': '0'}],
     'operand': 'and',
     'type': 'compound'},
    16: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql__1","path":["Contact", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'equals_to',
                     'rhs': '1'},
                    {'lhs': '#{_dp(\'{"pill_type":"output","provider":"lookup_table","line":"search_entries","path":["entries", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'less_than',
                     'rhs': '1'}],
     'operand': 'and',
     'type': 'compound'},
    20: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql__1","path":["Contact", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'equals_to',
                     'rhs': '1'},
                    {'lhs': '#{_dp(\'{"pill_type":"output","provider":"lookup_table","line":"search_entries","path":["entries", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'greater_than',
                     'rhs': '0'}],
     'operand': 'and',
     'type': 'compound'},
    25: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql__1","path":["Contact", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'greater_than',
                     'rhs': '1'}],
     'operand': 'and',
     'type': 'compound'},
    26: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"logger","line":"log_message","path":["message"]}\')}',
                     'operand': 'equals_to',
                     'rhs': 'Email'}],
     'operand': 'and',
     'type': 'compound'},
    31: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list","path":["rows", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'equals_to',
                     'rhs': '1'}],
     'operand': 'and',
     'type': 'compound'},
    34: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list","path":["rows", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'greater_than',
                     'rhs': '1'}],
     'operand': 'and',
     'type': 'compound'},
    37: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list","path":["rows", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'equals_to',
                     'rhs': '0'}],
     'operand': 'and',
     'type': 'compound'},
    41: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"logger","line":"log_message","path":["message"]}\')}',
                     'operand': 'equals_to',
                     'rhs': 'Domain'},
                    {'lhs': '#{_dp(\'{"pill_type":"output","provider":"lookup_table","line":"search_entries","path":["entries", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'less_than',
                     'rhs': '1'}],
     'operand': 'and',
     'type': 'compound'},
    46: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list__1","path":["rows", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'equals_to',
                     'rhs': '1'}],
     'operand': 'and',
     'type': 'compound'},
    49: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_smart_list","line":"query_list__1","path":["rows", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'greater_than',
                     'rhs': '1'}],
     'operand': 'and',
     'type': 'compound'},
    52: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"logger","line":"log_message","path":["message"]}\')}',
                     'operand': 'equals_to',
                     'rhs': 'Domain'},
                    {'lhs': '#{_dp(\'{"pill_type":"output","provider":"lookup_table","line":"search_entries","path":["entries", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'greater_than',
                     'rhs': '0'}],
     'operand': 'and',
     'type': 'compound'},
    55: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"logger","line":"log_message","path":["message"]}\')}',
                     'operand': 'equals_to',
                     'rhs': 'Name'},
                    {'lhs': "=_('data.salesforce.search_sobjects_soql__1.Contact.first.____Size', "
                            "'list_meta', '____Size', "
                            "'data.salesforce.search_sobjects_soql__1.Contact') == 0 and "
                            "_('data.salesforce.search_sobjects.Domain__c.first.____Size', "
                            "'list_meta', '____Size', 'data.salesforce.search_sobjects.Domain__c') "
                            '== 0',
                     'operand': 'is_true',
                     'rhs': '0'}],
     'operand': 'or',
     'type': 'compound'},
    58: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql","path":["Account", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'equals_to',
                     'rhs': '0'}],
     'operand': 'and',
     'type': 'compound'},
    61: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql","path":["Account", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'greater_than',
                     'rhs': '1'}],
     'operand': 'and',
     'type': 'compound'},
    64: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql","path":["Account", '
                            '{"path_element_type": "size"}]}\')}',
                     'operand': 'equals_to',
                     'rhs': '1'}],
     'operand': 'and',
     'type': 'compound'},
}
FOREACH_NODES: dict[int, dict[str, Any]] = {
    27: {'as': 'foreach', 'repeat_mode': None, 'source': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql__1","path":["Contact"]}\')}'},
    42: {'as': 'foreach__2', 'repeat_mode': None, 'source': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"search_sobjects_soql__1","path":["Contact"]}\')}'},
}
STOP_NUMBERS: list[int] = [5, 15, 19, 24, 33, 36, 40, 48, 51, 54, 60, 63, 66]
TRY_NUMBERS: list[int] = [2]
CATCH_NODES: list[tuple[int, str, dict[str, Any]]] = [(67, 'catch', {'max_retry_count': '0', 'retry_interval': '2'})]
TRIGGER_INPUT_CFG: dict[str, Any] = {'reply_schema_json': '[{"name":"AccountID","type":"array","of":"object","label":"Account '
                      'ID","optional":true,"properties":[{"control_type":"text","label":"Account '
                      'ID","name":"accountId","type":"string","optional":false},{"control_type":"text","label":"Account '
                      'Name","name":"accountName","type":"string","optional":false}]},{"control_type":"checkbox","label":"Found","render_input":{},"parse_output":{},"toggle_hint":"Select '
                      'from option '
                      'list","toggle_field":{"label":"Found","control_type":"text","toggle_hint":"Use '
                      'custom '
                      'value","name":"Found","type":"boolean"},"name":"Found","type":"boolean"},{"control_type":"checkbox","label":"Multiple","render_input":{},"parse_output":{},"toggle_hint":"Select '
                      'from option '
                      'list","toggle_field":{"label":"Multiple","control_type":"text","toggle_hint":"Use '
                      'custom '
                      'value","name":"Multiple","type":"boolean"},"name":"Multiple","type":"boolean"}]',
 'request_schema_json': '[{"name":"Customer","type":"string","control_type":"text"}]',
 'rest_request_method': 'get',
 'rest_request_path': '/getacct',
 'service_name': 'Get AccountID'}

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_service.send_reply",
    "workato_runtime.log_message",
    "salesforce.search_records",
    "lookup_table.search_entries",
    "workato_runtime.accumulate_list_items",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "lookup_table.search_entries",
    "workato_service.send_reply",
]
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")


def validate_88707332(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed")
    if raw.get("input") != TRIGGER_INPUT_CFG:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger configuration changed: {raw.get('input')!r}")
    actions = _collect_actions(raw)
    actual = [
        (a.get("number"), str(a.get("as")), str(a.get("provider")), str(a.get("name")))
        for a in actions
    ]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    for action in actions:
        step_as = str(action.get("as"))
        if action.get("input") != ACTION_INPUTS[step_as]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} action {step_as} input changed: {action.get('input')!r}"
            )
    control = _collect_control_nodes(raw)
    if_numbers = sorted(number for keyword, number in control if keyword == "if")
    if if_numbers != sorted(IF_CONDITIONS):
        raise RuntimeError(f"recipe {RECIPE_ID} if-node numbers changed: {if_numbers}")
    for (keyword, number), node in control.items():
        if keyword == "if" and node.get("input") != IF_CONDITIONS[number]:
            raise RuntimeError(f"recipe {RECIPE_ID} if {number} conditions changed: {node.get('input')!r}")
    foreach_numbers = sorted(number for keyword, number in control if keyword == "foreach")
    if foreach_numbers != sorted(FOREACH_NODES):
        raise RuntimeError(f"recipe {RECIPE_ID} foreach numbers changed: {foreach_numbers}")
    for number, spec in FOREACH_NODES.items():
        node = control[("foreach", number)]
        node_input = node.get("input") if isinstance(node.get("input"), dict) else {}
        if (
            str(node.get("as") or "") != spec["as"]
            or node.get("repeat_mode") != spec["repeat_mode"]
            or node_input.get("source") != spec["source"]
        ):
            raise RuntimeError(f"recipe {RECIPE_ID} foreach {number} changed")
    stop_numbers = sorted(number for keyword, number in control if keyword == "stop")
    if stop_numbers != STOP_NUMBERS:
        raise RuntimeError(f"recipe {RECIPE_ID} stop numbers changed: {stop_numbers}")
    for number in STOP_NUMBERS:
        if control[("stop", number)].get("input") != {"stop_with_error": "false"}:
            raise RuntimeError(f"recipe {RECIPE_ID} stop {number} is no longer graceful")
    try_numbers = sorted(number for keyword, number in control if keyword == "try")
    if try_numbers != TRY_NUMBERS:
        raise RuntimeError(f"recipe {RECIPE_ID} try numbers changed: {try_numbers}")
    catch_actual = [
        (number, str(control[("catch", number)].get("as") or ""), control[("catch", number)].get("input"))
        for keyword, number in sorted(control)
        if keyword == "catch"
    ]
    if catch_actual != CATCH_NODES:
        raise RuntimeError(f"recipe {RECIPE_ID} catch nodes changed: {catch_actual!r}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "service_name": TRIGGER_INPUT_CFG["service_name"],
        "actions": [
            {"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")}
            for a in actions
        ],
    }


def seed_88707332(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88707332(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    request = trigger.get("request")
    if not isinstance(request, dict) or "Customer" not in request:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger input must carry request.Customer explicitly "
            "(empty string for the blank branch)"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if not isinstance(data.get("expect"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track"),
        "raw_validation": validation,
    }
    refs: dict[str, str] = {}
    if "salesforce" in seed_in:
        if not isinstance(seed_in.get("salesforce"), dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce must be an object")
        provision = ctx.tools.call(
            "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)
        out["salesforce_ref_tokens"] = dict(refs)
    out["trigger"] = _replace_value(trigger, refs)
    _require_resolved(out["trigger"], "trigger")
    out["expect"] = _replace_value(deepcopy(data["expect"]), refs)
    _require_resolved(out["expect"], "expect")
    for key, value in seed_in.items():
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_88707332(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88707332(raw)
    initial_snapshot = _snapshot(ctx, seed)
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("salesforce_live"), dict):
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
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
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_88707332(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_ids = [
        str(record.get("id") or "")
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id")
    ]
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(live_ids) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(live_ids)} provisioned"
        )
    refs: dict[str, str] = {}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        if ref:
            refs[f"${ref.upper()}_ID"] = live_ids[idx]
    return refs


def _replace_value(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_value(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


def _require_resolved(value: dict[str, Any], label: str) -> None:
    leftover = _TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _collect_control_nodes(raw: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    control: dict[tuple[str, int], dict[str, Any]] = {}

    def walk(node: dict[str, Any]) -> None:
        for child in node.get("block") or []:
            if not isinstance(child, dict):
                continue
            keyword = str(child.get("keyword") or "")
            if keyword in {"if", "stop", "foreach", "catch", "try"}:
                control[(keyword, int(child.get("number") or 0))] = child
            walk(child)

    walk(raw)
    return control


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
