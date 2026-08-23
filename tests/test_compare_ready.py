from pathlib import Path
import yaml


def test_demo_pair_differs_only_by_local_policy():
    a = yaml.safe_load(Path("scenarios/fixed_20.yaml").read_text())
    b = yaml.safe_load(Path("scenarios/aggressive.yaml").read_text())
    assert a["local_policy"]["kind"] == "fixed_reserve"
    assert b["local_policy"]["kind"] == "aggressive"
    skip = {"local_policy"}
    for k in a:
        if k in skip:
            continue
        assert a[k] == b[k], k
