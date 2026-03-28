import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.policy import Action, LidAnglePolicy, Mode


def fresh() -> LidAnglePolicy:
    return LidAnglePolicy()


# ── Continuous mode ────────────────────────────────────────────────────────────

def test_fully_open_dims():
    p = fresh()
    assert p.evaluate(150, Mode.CONTINUOUS) == Action.DIM

def test_closing_brightens():
    p = fresh()
    p.evaluate(150, Mode.CONTINUOUS)
    assert p.evaluate(40, Mode.CONTINUOUS) == Action.BRIGHTEN

def test_middle_returns_none():
    p = fresh()
    assert p.evaluate(100, Mode.CONTINUOUS) is None
    assert p.evaluate(90,  Mode.CONTINUOUS) is None

def test_hysteresis_near_open():
    p = fresh()
    p.evaluate(150, Mode.CONTINUOUS)    # enter fully_open
    # 142° is inside hysteresis band (need < 140 to leave)
    assert p.evaluate(142, Mode.CONTINUOUS) is None
    # 138° — past hysteresis → back to middle
    assert p.evaluate(138, Mode.CONTINUOUS) == Action.RESTORE

def test_hysteresis_near_close():
    p = fresh()
    p.evaluate(40, Mode.CONTINUOUS)     # enter closing
    # 63° is inside hysteresis band (need > 65 to leave)
    assert p.evaluate(63, Mode.CONTINUOUS) is None
    # 67° — past hysteresis → middle
    assert p.evaluate(67, Mode.CONTINUOUS) == Action.RESTORE

def test_no_repeat_in_same_state():
    p = fresh()
    p.evaluate(150, Mode.CONTINUOUS)
    assert p.evaluate(155, Mode.CONTINUOUS) is None
    assert p.evaluate(160, Mode.CONTINUOUS) is None

def test_restore_after_dim():
    p = fresh()
    p.saved_brightness = 0.7
    p.evaluate(150, Mode.CONTINUOUS)
    assert p.evaluate(100, Mode.CONTINUOUS) == Action.RESTORE


# ── Binary mode ────────────────────────────────────────────────────────────────

def test_binary_open_dims():
    p = fresh()
    assert p.evaluate(180, Mode.BINARY) == Action.DIM

def test_binary_closed_brightens():
    p = fresh()
    p.evaluate(180, Mode.BINARY)
    assert p.evaluate(0, Mode.BINARY) == Action.BRIGHTEN

def test_binary_no_repeat():
    p = fresh()
    p.evaluate(180, Mode.BINARY)
    assert p.evaluate(180, Mode.BINARY) is None


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
