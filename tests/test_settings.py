import settings


def test_default_exclude_until_saved():
    settings.factory_reset()
    assert "REX" in settings.load_exclude()["Activity"]
    settings.save_exclude({})
    assert settings.load_exclude() == {}
    settings.reset_exclude()
    assert "REX" in settings.load_exclude()["Activity"]


def test_rules_default_and_save():
    assert settings.load_rules()[0]["text"] == "Reinforcement"
    settings.save_rules([{"column": "Document Title", "op": "contains", "text": "Rebar", "on": False},
                         {"column": "", "op": "starts", "text": "x"}])
    assert settings.load_rules() == [{"column": "Document Title", "op": "contains", "text": "Rebar", "on": False}]
    settings.factory_reset()
    assert settings.load_rules()[0]["text"] == "Reinforcement"


def test_seen_values_accumulate():
    settings.save_seen_values({"Activity": ["IN2"]})
    settings.save_seen_values({"Activity": ["PR2"]})
    assert settings.load_seen_values() == {"Activity": ["IN2", "PR2"]}
