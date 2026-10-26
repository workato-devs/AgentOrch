from __future__ import annotations

import json
import os
import ssl
import urllib.parse
import urllib.request
from typing import Any


class SlackLiveClient:
    def __init__(self, bot_token: str) -> None:
        if not bot_token:
            raise RuntimeError("missing SLACK_BOT_TOKEN")
        self.bot_token = bot_token
        ca_file = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
        self.ssl_context = (
            ssl.create_default_context(cafile=ca_file)
            if ca_file
            else ssl.create_default_context()
        )

    def request(self, method: str, payload: dict[str, Any], http_get: bool = False) -> dict[str, Any]:
        headers = {"Authorization": "Bearer " + self.bot_token}
        if http_get:
            url = "https://slack.com/api/" + method + "?" + urllib.parse.urlencode(payload)
            data = None
        else:
            url = "https://slack.com/api/" + method
            headers["Content-Type"] = "application/json; charset=utf-8"
            data = json.dumps(payload).encode()

        request = urllib.request.Request(
            url,
            data=data,
            method="GET" if http_get else "POST",
            headers=headers,
        )
        with urllib.request.urlopen(request, context=self.ssl_context, timeout=60) as response:
            body = json.loads(response.read().decode())

        if not isinstance(body, dict):
            raise RuntimeError(f"Slack {method} returned non-object response: {body}")
        return body

    def call(self, method: str, payload: dict[str, Any], http_get: bool = False) -> dict[str, Any]:
        body = self.request(method, payload, http_get)
        if not isinstance(body, dict) or not body.get("ok"):
            raise RuntimeError(f"Slack {method} failed: {body}")
        return body

    def post_message(
        self,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        thread_ts: str = "",
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not channel:
            raise RuntimeError("missing Slack channel")
        if not text and not blocks and not attachments:
            raise RuntimeError("refusing to post empty Slack message")
        payload: dict[str, Any] = {"channel": channel, "text": text}
        if blocks is not None:
            payload["blocks"] = blocks
        if attachments is not None:
            payload["attachments"] = attachments
        if thread_ts:
            payload["thread_ts"] = thread_ts
        response = self.call("chat.postMessage", payload)
        response.setdefault("thread_ts", thread_ts or response.get("ts"))
        return response

    def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not channel or not ts:
            raise RuntimeError("missing Slack channel or message ts for update")
        if not text:
            raise RuntimeError("refusing to update Slack message with empty text")
        payload: dict[str, Any] = {"channel": channel, "ts": ts, "text": text}
        if blocks is not None:
            payload["blocks"] = blocks
        if attachments is not None:
            payload["attachments"] = attachments
        response = self.call("chat.update", payload)
        response.setdefault("channel", channel)
        response.setdefault("ts", ts)
        return response

    def post_reply(
        self,
        channel: str,
        text: str,
        thread_ts: str = "",
        blocks: list[dict[str, Any]] | None = None,
        *,
        user: str = "",
        ephemeral: bool = False,
        replace_original: bool = False,
        delete_original: bool = False,
        original_ts: str = "",
    ) -> dict[str, Any]:
        if not channel:
            raise RuntimeError("missing Slack channel")
        if not text and not blocks:
            raise RuntimeError("refusing to post empty Slack reply")
        if replace_original:
            if not original_ts:
                raise RuntimeError("Slack replacement reply requires original_ts")
            response = self.update_message(channel, original_ts, text, blocks)
            response["replaced_original"] = True
            return response
        if delete_original:
            if not original_ts:
                raise RuntimeError("Slack delete-and-reply requires original_ts")
            self.delete_message(channel, original_ts)
        payload = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        if blocks is not None:
            payload["blocks"] = blocks
        if ephemeral:
            if not user:
                raise RuntimeError("Slack ephemeral reply requires invoking user")
            payload["user"] = user
            response = self.call("chat.postEphemeral", payload)
            response["ephemeral"] = True
        else:
            response = self.call("chat.postMessage", payload)
        if delete_original:
            response["deleted_original"] = True
            response["original_ts"] = original_ts
        return response

    def delete_message(self, channel: str, ts: str) -> dict[str, Any]:
        if not channel or not ts:
            raise RuntimeError("missing Slack channel or message ts for delete")
        return self.call("chat.delete", {"channel": channel, "ts": ts})

    def update_blocks_by_block_id(self, message_json: Any, blocks_to_update: list[Any]) -> dict[str, Any]:
        original = _message_json(message_json)
        channel = str(original.get("channel") or original.get("channel_id") or "")
        ts = str(original.get("ts") or original.get("message_ts") or "")
        if not channel or not ts:
            message = original.get("message") if isinstance(original.get("message"), dict) else {}
            channel = channel or str(message.get("channel") or message.get("channel_id") or "")
            ts = ts or str(message.get("ts") or message.get("message_ts") or "")
        if not channel or not ts:
            raise RuntimeError("Slack block update requires message_json with channel and ts")
        old_blocks = _message_blocks(original)
        new_blocks = _apply_block_updates(old_blocks, blocks_to_update)
        text = str(original.get("text") or "Updated benchmark Slack message")
        response = self.call("chat.update", {"channel": channel, "ts": ts, "text": text, "blocks": new_blocks})
        return {**response, "channel": channel, "ts": ts, "blocks": new_blocks}

    def lookup_user_by_email(self, email: str) -> dict[str, Any]:
        if not email:
            raise RuntimeError("missing Slack user email")
        body = self.request("users.lookupByEmail", {"email": email}, http_get=True)
        if body.get("ok"):
            user = body.get("user") if isinstance(body.get("user"), dict) else {}
            profile = user.get("profile") if isinstance(user.get("profile"), dict) else {}
            return {
                "ok": True,
                "id": user.get("id"),
                "name": user.get("name"),
                "real_name": user.get("real_name") or profile.get("real_name"),
                "email": profile.get("email"),
                # Workato's output schema exposes profile at the top level
                # (pills walk ["profile","image_512"]).
                "profile": profile,
                "user": user,
            }
        if body.get("error") == "users_not_found":
            return {
                "ok": True,
                "not_found": True,
                "id": None,
                "name": None,
                "real_name": None,
                "email": email,
            }
        raise RuntimeError(f"Slack users.lookupByEmail failed: {body}")

    def lookup_user_by_id(self, user_id: str) -> dict[str, Any]:
        if not user_id:
            raise RuntimeError("missing Slack user id")
        body = self.request("users.info", {"user": user_id}, http_get=True)
        if body.get("ok"):
            user = body.get("user") if isinstance(body.get("user"), dict) else {}
            profile = user.get("profile") if isinstance(user.get("profile"), dict) else {}
            return {
                "ok": True,
                "id": user.get("id"),
                "name": user.get("name"),
                "real_name": user.get("real_name") or profile.get("real_name"),
                "email": profile.get("email"),
                # Workato's output schema exposes profile at the top level
                # (pills walk ["profile","image_512"]).
                "profile": profile,
                "user": user,
            }
        if body.get("error") == "user_not_found":
            return {
                "ok": True,
                "not_found": True,
                "id": user_id,
                "name": None,
                "real_name": None,
                "email": None,
            }
        raise RuntimeError(f"Slack users.info failed: {body}")

    def publish_home(self, user_id: str, view: dict[str, Any]) -> dict[str, Any]:
        if not user_id:
            raise RuntimeError("missing Slack App Home user_id")
        return self.call("views.publish", {"user_id": user_id, "view": _home_view(view)})

    def open_modal(self, trigger_id: str, view: dict[str, Any]) -> dict[str, Any]:
        if not trigger_id:
            raise RuntimeError("missing Slack modal trigger_id")
        return self.call("views.open", {"trigger_id": trigger_id, "view": _modal_view(view)})


def _plain_text(text: Any, field: str = "text", limit: int = 75) -> dict[str, str]:
    value = str(text or "").strip()
    if not value:
        raise RuntimeError(f"Slack block {field} is empty; refusing to substitute placeholder text")
    return {"type": "plain_text", "text": value[:limit]}


def _mrkdwn(text: Any, field: str = "text") -> dict[str, str]:
    value = str(text or "")
    if not value.strip():
        raise RuntimeError(f"Slack block {field} is empty; refusing to substitute placeholder text")
    return {"type": "mrkdwn", "text": value}


def _dedupe_action_ids(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Slack rejects a view whose interactive elements share an action_id
    # (invalid_arguments: '`action_id` "..." already exists'). Production
    # Workato generates per-element ids; this converter passes raw
    # bot_command ids through, so a recipe with two buttons bound to the
    # same command collides only here. Dedupe deterministically in document
    # order: first occurrence keeps the id, repeats get _2, _3, ...
    # Collision-free views are untouched.
    seen: dict[str, int] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            action_id = node.get("action_id")
            if isinstance(action_id, str) and action_id:
                count = seen.get(action_id, 0) + 1
                seen[action_id] = count
                if count > 1:
                    node["action_id"] = f"{action_id}_{count}"[:255]
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(blocks)
    return blocks


def _modal_view(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise RuntimeError("Slack modal view must be an object")
    blocks = _view_blocks(raw)
    if not blocks:
        raise RuntimeError("Slack modal view must contain at least one block")
    view: dict[str, Any] = {
        "type": "modal",
        "title": _plain_text(raw.get("modal_title"), "modal_title", 24),
        "blocks": _dedupe_action_ids(blocks),
    }
    submit_view = raw.get("submit_view") if isinstance(raw.get("submit_view"), dict) else {}
    if submit_view.get("submit_text"):
        view["submit"] = _plain_text(submit_view.get("submit_text"), "submit_text", 24)
    if submit_view.get("close_text"):
        view["close"] = _plain_text(submit_view.get("close_text"), "close_text", 24)
    return view


def _home_view(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise RuntimeError("Slack App Home view must be an object")
    blocks = _view_blocks(raw)
    if not blocks:
        raise RuntimeError("Slack App Home view must contain at least one block")
    return {"type": "home", "blocks": _dedupe_action_ids(blocks)}


def _view_blocks(raw: dict[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, raw_block in enumerate(raw.get("blocks") or []):
        if not isinstance(raw_block, dict):
            continue
        block = _modal_block(raw_block, index)
        if block is None and raw_block.get("type") not in (None, ""):
            block = _standard_view_block(raw_block, index)
        if block:
            blocks.append(block)
    return blocks


def _standard_view_block(raw: dict[str, Any], index: int) -> dict[str, Any] | None:
    """Normalize public Slack Block Kit into the same view used for Workato.

    Recipes store Workato's connector-specific ``block_type`` representation,
    while the public benchmark contract exposes a Slack ``view`` object.  A
    model that supplies ordinary Block Kit must not be forced to guess the
    private connector transport encoding.
    """

    block_type = str(raw.get("type") or "")
    default_prefix = {
        "section": "section_with_text",
        "actions": "actions",
        "divider": "divider",
        "context": "context",
        "image": "image",
        "input": "input",
        "header": "header",
    }.get(block_type, block_type or "block")
    block_id = str(raw.get("block_id") or f"{default_prefix}_{index}")[:255]
    if block_type == "divider":
        return {"type": "divider", "block_id": block_id}
    if block_type == "section":
        raw_text = raw.get("text")
        if isinstance(raw_text, dict) and raw_text.get("text") not in (None, ""):
            text = {
                "type": str(raw_text.get("type") or "mrkdwn"),
                "text": str(raw_text.get("text")),
            }
        else:
            text = _mrkdwn(raw.get("section_text"), "section_text")
        block: dict[str, Any] = {
            "type": "section",
            "block_id": block_id,
            "text": text,
        }
        raw_accessory = raw.get("accessory")
        if isinstance(raw_accessory, dict):
            accessory = _standard_view_element(raw_accessory, block_id)
            if accessory:
                block["accessory"] = accessory
        fields = [
            _standard_text_object(field, "section field")
            for field in raw.get("fields") or []
            if isinstance(field, (dict, str))
        ]
        if fields:
            block["fields"] = fields[:10]
        return block
    if block_type == "actions":
        elements = [
            element
            for element_index, raw_element in enumerate(raw.get("elements") or [])
            if isinstance(raw_element, dict)
            for element in [
                _standard_view_element(raw_element, f"{block_id}_{element_index}")
            ]
            if element
        ]
        return (
            {"type": "actions", "block_id": block_id, "elements": elements}
            if elements
            else None
        )
    if block_type == "context":
        elements = [
            _standard_text_object(element, "context element")
            for element in raw.get("elements") or []
            if isinstance(element, (dict, str))
        ]
        return (
            {"type": "context", "block_id": block_id, "elements": elements[:10]}
            if elements
            else None
        )
    if block_type == "image":
        image_url = _image_url_or_placeholder(raw.get("image_url"))
        if not image_url:
            raise RuntimeError(f"Slack image block {block_id} has no image_url")
        block = {
            "type": "image",
            "block_id": block_id,
            "image_url": image_url[:3000],
            "alt_text": str(raw.get("alt_text") or "image")[:2000],
        }
        if isinstance(raw.get("title"), dict):
            block["title"] = _standard_text_object(raw["title"], "image title")
        return block
    if block_type == "header":
        return {
            "type": "header",
            "block_id": block_id,
            "text": _standard_text_object(raw.get("text"), "header text"),
        }
    if block_type == "input" and isinstance(raw.get("element"), dict):
        return {
            "type": "input",
            "block_id": block_id,
            "label": _standard_text_object(raw.get("label"), "input label"),
            "optional": bool(raw.get("optional", False)),
            "element": dict(raw["element"]),
        }
    return None


def _standard_text_object(value: Any, field: str) -> dict[str, Any]:
    if isinstance(value, dict):
        text = value.get("text")
        if text in (None, ""):
            raise RuntimeError(f"Slack block {field} is empty")
        result: dict[str, Any] = {
            "type": str(value.get("type") or "mrkdwn"),
            "text": str(text),
        }
        if "emoji" in value:
            result["emoji"] = bool(value["emoji"])
        return result
    return _mrkdwn(value, field)


def _standard_view_element(raw: dict[str, Any], fallback_id: str) -> dict[str, Any] | None:
    element_type = str(raw.get("type") or "")
    if element_type != "button":
        return dict(raw) if element_type else None
    raw_text = raw.get("text")
    title = raw_text.get("text") if isinstance(raw_text, dict) else raw_text
    if title in (None, ""):
        return None
    button: dict[str, Any] = {
        "type": "button",
        "text": _plain_text(title, "button text", 75),
        "action_id": str(raw.get("action_id") or fallback_id)[:255],
        "value": str(raw.get("value") or title)[:2000],
    }
    style = str(raw.get("style") or "")
    if style in {"primary", "danger"}:
        button["style"] = style
    if raw.get("url") not in (None, ""):
        button["url"] = str(raw["url"])[:3000]
    return button


def _modal_block(raw: dict[str, Any], index: int) -> dict[str, Any] | None:
    block_type = str(raw.get("block_type") or "")
    block_id = str(raw.get("block_id") or f"{block_type or 'block'}_{index}")[:255]
    if block_type == "divider":
        return {"type": "divider", "block_id": block_id}
    if block_type == "section_with_text":
        block: dict[str, Any] = {"type": "section", "block_id": block_id, "text": _mrkdwn(raw.get("section_text"), "section_text")}
        button = _button(raw, block_id)
        if button:
            block["accessory"] = button
        return block
    if block_type == "actions":
        elements = [
            button
            for index, action in enumerate(raw.get("actions") or [])
            if isinstance(action, dict)
            for button in [_button(action, f"{block_id}_{index}")]
            if button
        ]
        return {"type": "actions", "block_id": block_id, "elements": elements} if elements else None
    if block_type == "select_menu_input":
        options = [
            {
                "text": _plain_text(option.get("title"), "menu option title", 75),
                "value": str(option.get("value") or option.get("title") or "option")[:75],
            }
            for option in raw.get("options") or []
            if isinstance(option, dict)
        ]
        if not options:
            raise RuntimeError(f"Slack static select block {block_id} has no options")
        element: dict[str, Any] = {
            "type": "static_select",
            "action_id": block_id,
            "options": options,
        }
        if raw.get("placeholder_text"):
            element["placeholder"] = _plain_text(raw.get("placeholder_text"), "placeholder_text", 150)
        return {
            "type": "input",
            "block_id": block_id,
            "label": _plain_text(raw.get("label_text") or raw.get("section_text"), "label_text", 2000),
            "optional": str(raw.get("optional") or "").lower() == "true",
            "element": element,
        }
    if block_type == "image":
        # Anon-wrapped image URLs are anonymizer FICTION (the host does not
        # exist) and Slack downloads image_url at publish time — the stripped
        # URL still hard-fails views.publish. The semantic observable is the
        # block shape, so substitute the stable Slack-hosted placeholder.
        # Free-form texts stay raw-faithful — only the URL is a live boundary.
        image_url = _image_url_or_placeholder(raw.get("image_url"))
        if not image_url:
            raise RuntimeError(f"Slack image block {block_id} has no image_url")
        image_block: dict[str, Any] = {
            "type": "image",
            "block_id": block_id,
            "image_url": image_url[:3000],
            "alt_text": str(raw.get("alt_text") or raw.get("image_title") or "image")[:2000],
        }
        if raw.get("image_title") not in (None, ""):
            image_block["title"] = _plain_text(raw.get("image_title"), "image_title", 2000)
        return image_block
    if block_type == "section_with_button":
        section_block: dict[str, Any] = {
            "type": "section",
            "block_id": block_id,
            "text": _mrkdwn(raw.get("section_text"), "section_text"),
        }
        button = _button(raw, block_id)
        if button:
            section_block["accessory"] = button
        return section_block
    if block_type == "section_with_image":
        section_image_block: dict[str, Any] = {
            "type": "section",
            "block_id": block_id,
            "text": _mrkdwn(raw.get("section_text"), "section_text"),
        }
        accessory_url = _image_url_or_placeholder(raw.get("image_url"))
        if accessory_url:
            section_image_block["accessory"] = {
                "type": "image",
                "image_url": accessory_url[:3000],
                "alt_text": str(raw.get("alt_text") or "image")[:2000],
            }
        return section_image_block
    if block_type == "context":
        context_elements = [
            _mrkdwn(element.get("text"), "context element")
            for element in raw.get("elements") or []
            if isinstance(element, dict) and element.get("text") not in (None, "")
        ]
        if not context_elements:
            raise RuntimeError(f"Slack context block {block_id} has no text elements")
        return {"type": "context", "block_id": block_id, "elements": context_elements[:10]}
    if block_type == "section_with_fields":
        fields = [
            _mrkdwn(
                "*%s*\n%s" % (str(field.get("title") or ""), str(field.get("value") or "")),
                "attachment_fields",
            )
            for field in raw.get("attachment_fields") or []
            if isinstance(field, dict)
        ]
        if not fields:
            raise RuntimeError(f"Slack section_with_fields block {block_id} has no attachment_fields")
        fields_block: dict[str, Any] = {"type": "section", "block_id": block_id, "fields": fields[:10]}
        if raw.get("section_text") not in (None, ""):
            fields_block["text"] = _mrkdwn(raw.get("section_text"), "section_text")
        return fields_block
    if block_type in {"plain_text_input", "multiline_plain_text_input"}:
        element = {
            "type": "plain_text_input",
            "action_id": block_id,
            "multiline": block_type == "multiline_plain_text_input",
        }
        if raw.get("initial_value") not in (None, ""):
            element["initial_value"] = str(raw.get("initial_value"))
        if raw.get("placeholder_text"):
            element["placeholder"] = _plain_text(raw.get("placeholder_text"), "placeholder_text", 150)
        return {
            "type": "input",
            "block_id": block_id,
            "label": _plain_text(raw.get("label_text"), "label_text", 2000),
            "optional": str(raw.get("optional") or "").lower() == "true",
            "element": element,
        }
    return None


def _image_url_or_placeholder(raw_url: Any) -> str:
    """Any anonymizer tag in an image URL makes it fiction (fully wrapped or a
    tagged path segment) — Slack downloads image urls at publish time, so
    fiction hosts/paths hard-fail views.publish. Substitute the stable
    Slack-hosted placeholder; clean urls pass through verbatim."""
    url = str(raw_url or "")
    if "<anon>" in url:
        return "https://a.slack-edge.com/80588/img/plugins/app/service_72.png"
    return url


def _button(raw: dict[str, Any], fallback_id: str) -> dict[str, Any] | None:
    title = raw.get("button_title")
    if title in (None, ""):
        return None
    button: dict[str, Any] = {
        "type": "button",
        "text": _plain_text(title, "button_title", 75),
        "action_id": str(raw.get("button_id") or raw.get("bot_command") or fallback_id)[:255],
        "value": str(raw.get("bot_command") or title)[:2000],
    }
    style = str(raw.get("style") or "")
    if style in {"primary", "danger"}:
        button["style"] = style
    return button


def _message_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Slack message_json is not valid JSON") from exc
        if isinstance(parsed, dict):
            return parsed
    raise RuntimeError("Slack message_json must be an object")


def _message_blocks(message: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = message.get("blocks")
    if not isinstance(blocks, list) and isinstance(message.get("message"), dict):
        blocks = message["message"].get("blocks")
    if not isinstance(blocks, list):
        return []
    return [dict(block) for block in blocks if isinstance(block, dict)]


def _apply_block_updates(old_blocks: list[dict[str, Any]], updates: list[Any]) -> list[dict[str, Any]]:
    new_blocks = [dict(block) for block in old_blocks]
    for raw_update in updates:
        if not isinstance(raw_update, dict):
            continue
        target_id = str(raw_update.get("block_id") or "")
        if not target_id:
            if not raw_update:
                # Workato ignores blank block-update slots (a trailing empty {}
                # left in blocks_to_update); skip them rather than raising.
                continue
            raise RuntimeError("Slack block update missing block_id")
        replacement = _replacement_blocks(target_id, raw_update)
        remove_block = _truthy(raw_update.get("remove_block"))
        out: list[dict[str, Any]] = []
        replaced = False
        for block in new_blocks:
            if str(block.get("block_id") or "") != target_id:
                out.append(block)
                continue
            replaced = True
            if not remove_block:
                out.extend(replacement)
        if not replaced and not remove_block:
            out.extend(replacement)
        new_blocks = out
    return new_blocks


def _replacement_blocks(target_id: str, raw_update: dict[str, Any]) -> list[dict[str, Any]]:
    raw_blocks = raw_update.get("blocks")
    if not isinstance(raw_blocks, list):
        raw_blocks = []
    blocks: list[dict[str, Any]] = []
    for index, raw_block in enumerate(raw_blocks):
        if not isinstance(raw_block, dict):
            continue
        block_input = dict(raw_block)
        if not block_input.get("block_id"):
            block_input["block_id"] = target_id if index == 0 else f"{target_id}_{index}"
        block = _modal_block(block_input, index)
        if block:
            blocks.append(block)
    return blocks


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}
