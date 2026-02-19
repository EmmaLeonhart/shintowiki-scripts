#!/usr/bin/env python3
"""
generate_lists.py

Generates:
 - find_list.txt  (360 lines of "qq-Month Day (Lunisolar)-qq")
 - replace_list.txt  (360 template blocks with Chinese and Korean titles)
"""

import itertools
import os

# English month names
months_en = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

# Chinese lunar month numbers
chinese_month_nums = {
    1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六",
    7: "七", 8: "八", 9: "九", 10: "十", 11: "十一", 12: "十二"
}

# Chinese lunar day names
chinese_day_nums = {}
for i in range(1, 10):
    chinese_day_nums[i] = f"初{['一','二','三','四','五','六','七','八','九'][i-1]}"
chinese_day_nums[10] = "初十"
for i, num in enumerate(['十一','十二','十三','十四','十五','十六','十七','十八','十九'], start=11):
    chinese_day_nums[i] = num
chinese_day_nums[20] = "二十"
for i, num in enumerate(['廿一','廿二','廿三','廿四','廿五','廿六','廿七','廿八','廿九'], start=21):
    chinese_day_nums[i] = num
chinese_day_nums[30] = "三十"

# Replacement template
template = """{{afc comment|1=This article as with the other date articles is relatively limited in scope to Japan. Reviewing the translation of this is good and also adding content translated from Chinese and Korean wikipedias will also be good. Both wikipedias are also relatively centered around their own countries for their Lunisolar calendar dates~~~~}}
{{Globalize|article|Japan|date=April 2025}}
{{Expand Chinese|1={chinese}|topic=hist|date=April 2025}}
{{Expand Korean|1={korean}|topic=hist|date=April 2025}}"""

def main():
    # Write to files in current working directory
    find_path = os.path.join(os.getcwd(), "find_list.txt")
    replace_path = os.path.join(os.getcwd(), "replace_list.txt")

    # Build find list
    find_list = [
        f"qq-{month} {day} (Lunisolar)-qq"
        for month in months_en
        for day in range(1, 31)
    ]

    # Build replace list
    replace_list = []
    for idx, (month, day) in enumerate(
        itertools.product(months_en, range(1, 31)),
        start=1
    ):
        lunar_month = ((idx - 1) // 30) + 1
        chinese = f"{chinese_month_nums[lunar_month]}月{chinese_day_nums[day]}"
        korean = f"음력 {lunar_month}월 {day}일"
        replace_list.append(template.format(chinese=chinese, korean=korean))

    # Write find_list.txt
    with open(find_path, "w", encoding="utf-8") as f:
        for line in find_list:
            f.write(line + "\n")

    # Write replace_list.txt
    with open(replace_path, "w", encoding="utf-8") as f:
        for block in replace_list:
            f.write(block + "\n\n")

    print(f"Generated:\n  - {find_path}\n  - {replace_path}")

if __name__ == "__main__":
    main()
