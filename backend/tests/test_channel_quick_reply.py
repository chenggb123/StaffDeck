from types import SimpleNamespace

from app.core.harness_v2_engine import HarnessV2Engine


def _request(channel: str, message: str) -> SimpleNamespace:
    return SimpleNamespace(channel=channel, message=message)


def _session(**kwargs) -> SimpleNamespace:
    values = {
        "active_skill_id": None,
        "active_step_id": None,
        "pending_tasks_json": None,
        "awaiting_input_json": None,
        "resume_after_answer_json": None,
    }
    values.update(kwargs)
    return SimpleNamespace(**values)


def test_wecom_casual_message_can_use_quick_reply() -> None:
    request = _request("wecom", "你好")
    session = _session()

    assert HarnessV2Engine._can_use_channel_quick_reply(request, session) is True


def test_wecom_task_message_does_not_use_quick_reply() -> None:
    request = _request("wecom", "帮我提一个工单")
    session = _session()

    assert HarnessV2Engine._can_use_channel_quick_reply(request, session) is False


def test_wecom_active_task_does_not_use_quick_reply() -> None:
    request = _request("wecom", "你好")
    session = _session(pending_tasks_json=[{"task_id": "task_a"}])

    assert HarnessV2Engine._can_use_channel_quick_reply(request, session) is False


def test_web_message_does_not_use_quick_reply() -> None:
    request = _request("web", "你好")
    session = _session()

    assert HarnessV2Engine._can_use_channel_quick_reply(request, session) is False
