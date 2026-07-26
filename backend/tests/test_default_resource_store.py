from app.services.default_resource_store import default_resource_store


def test_list_templates_includes_deepseek_when_env_is_set(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-v4-flash")

    templates = default_resource_store.list_templates()
    deepseek_templates = [item for item in templates if item.provider_profile == "deepseek"]

    assert deepseek_templates, "expected env-discovered DeepSeek template"
    assert deepseek_templates[0].model_name == "deepseek-v4-flash"