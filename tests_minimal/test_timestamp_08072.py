"""Tests for the 08072 timestamp fix: hybrid UTC/local serialization."""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_serialize_old_data_as_utc():
    """Pre-2026-08-08 data stored as UTC naive → serialize with +00:00."""
    from backend.app.models import _serialize_timestamp
    old = datetime(2026, 8, 7, 16, 5, 23)  # naive UTC
    result = _serialize_timestamp(old)
    assert "+00:00" in result, f"expected +00:00 suffix, got {result}"
    print("old naive →", result)


def test_serialize_new_data_as_local():
    """Post-2026-08-08 data stored as local naive → serialize with +08:00."""
    from backend.app.models import _serialize_timestamp
    new = datetime(2026, 8, 8, 0, 30, 0)  # naive local (cutoff + 30min)
    result = _serialize_timestamp(new)
    assert "+08:00" in result, f"expected +08:00 suffix, got {result}"
    print("new naive →", result)


def test_serialize_aware_unchanged():
    """Aware timestamps pass through unchanged."""
    from backend.app.models import _serialize_timestamp
    aware = datetime(2026, 8, 8, 0, 30, 0, tzinfo=timezone.utc)
    result = _serialize_timestamp(aware)
    assert "+00:00" in result
    print("aware utc →", result)


def test_serialize_none_safe():
    """None passes through."""
    from backend.app.models import _serialize_timestamp
    assert _serialize_timestamp(None) is None


def test_js_local_consistency_for_old_data():
    """模拟浏览器：JS new Date 把 '...+00:00' 当 UTC，再 toLocaleString('zh-CN', {hour12:false}) 转本地。"""
    from datetime import datetime, timezone, timedelta
    # 历史 UTC 16:05 → +08:00 → 实际北京时间 00:05:23（次日凌晨）
    utc_iso = "2026-08-07T16:05:23+00:00"
    # Python 模拟 JS Date 解析 + toLocaleString
    parsed = datetime.fromisoformat(utc_iso)
    # 转为北京时间显示
    beijing = parsed.astimezone(timezone(timedelta(hours=8)))
    formatted = beijing.strftime("%Y/%m/%d %H:%M:%S")
    assert "2026/08/08 00:05:23" == formatted, f"got {formatted}"
    print("display:", formatted)


def test_js_local_consistency_for_new_data():
    """新数据本地时间 00:30:00 + +08:00 → JS 显示 2026/08/08 00:30:00。"""
    iso = "2026-08-08T00:30:00+08:00"
    parsed = datetime.fromisoformat(iso)
    formatted = parsed.strftime("%Y/%m/%d %H:%M:%S")
    assert "2026/08/08 00:30:00" == formatted, f"got {formatted}"
    print("display:", formatted)


if __name__ == "__main__":
    test_serialize_old_data_as_utc()
    test_serialize_new_data_as_local()
    test_serialize_aware_unchanged()
    test_serialize_none_safe()
    test_js_local_consistency_for_old_data()
    test_js_local_consistency_for_new_data()
    print("All passed")