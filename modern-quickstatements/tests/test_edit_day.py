"""edit_day: cap day rolls over at 02:00 JST (UTC+7 shifted date)."""
import datetime
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from direct_daily_edits import edit_day

UTC = datetime.timezone.utc

def test_before_2am_jst_is_previous_day():
    # 16:59 UTC Jul 7 = 01:59 JST Jul 8 -> still edit-day Jul 7
    assert edit_day(datetime.datetime(2026, 7, 7, 16, 59, tzinfo=UTC)) == datetime.date(2026, 7, 7)

def test_after_2am_jst_rolls_over():
    # 17:00 UTC Jul 7 = 02:00 JST Jul 8 -> edit-day Jul 8
    assert edit_day(datetime.datetime(2026, 7, 7, 17, 0, tzinfo=UTC)) == datetime.date(2026, 7, 8)
