from _pytest.monkeypatch import MonkeyPatch

from typeguard import TypeCheckConfiguration


def test_custom_type_checker(monkeypatch: MonkeyPatch) -> None:
    def lookup_func(origin_type, args, extras):
        pass

    class FakeEntryPoint:
        name = "test"

        def load(self):
            return lookup_func

    def fake_entry_points(group):
        assert group == "typeguard.checker_lookup"
        return [FakeEntryPoint()]

    monkeypatch.setattr("typeguard._config.entry_points", fake_entry_points)
    config = TypeCheckConfiguration()
    assert config.checker_lookup_functions[0] is lookup_func
