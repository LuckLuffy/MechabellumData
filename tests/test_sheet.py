import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import convert_to_json
import sheet_updater
from config import BASELINE_XLSX


def _baseline_copy(dst_dir, name):
    dst = os.path.join(dst_dir, name)
    shutil.copy2(BASELINE_XLSX, dst)
    return dst


class TestCumulativeWorkbook(unittest.TestCase):
    """load_workbook(path=None) 应解析到 outputs/ 最新版本，实现跨版本累积。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._out_patcher = mock.patch("sheet_updater.OUTPUT_DIR", self._tmp)
        self._out_patcher.start()
        self.addCleanup(self._out_patcher.stop)
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_load_workbook_falls_back_to_baseline_copy(self):
        # 只有 --init 复制出的 vbaseline：解析到它，值仍为基准值
        _baseline_copy(self._tmp, "unit_data_vbaseline.xlsx")
        wb, ws, row_map, col_map = sheet_updater.load_workbook()
        self.assertEqual(
            ws.cell(row=row_map["爬虫"], column=col_map["单体血量"]).value, 263)

    def test_changes_accumulate_across_runs(self):
        _baseline_copy(self._tmp, "unit_data_vbaseline.xlsx")

        # 第一轮：从最新版本加载，应用一条变更并保存为 v1.0
        wb, ws, row_map, col_map = sheet_updater.load_workbook()
        self.assertTrue(
            sheet_updater.apply_change(ws, row_map, col_map, "爬虫", "单体血量", "300"))
        sheet_updater.save_new_sheet(wb, "1.0")

        # 第二轮：load_workbook() 应解析到 v1.0（而非基准表），变更得以保留
        wb2, ws2, row_map2, col_map2 = sheet_updater.load_workbook()
        self.assertEqual(
            ws2.cell(row=row_map2["爬虫"], column=col_map2["单体血量"]).value, 300)

    def test_resolve_newest_uses_latest_mtime_not_name(self):
        old = _baseline_copy(self._tmp, "unit_data_v2.0.xlsx")
        new = _baseline_copy(self._tmp, "unit_data_vbaseline.xlsx")
        # 让 vbaseline 更新（名字排后不应影响“最新”判定）
        os.utime(new, (os.path.getmtime(old) + 10,) * 2)
        self.assertEqual(sheet_updater._resolve_newest_sheet(), new)


class TestConvertToJsonCumulative(unittest.TestCase):
    """convert_to_json.main() 无参时应跟随 load_workbook 解析最新版本。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._out_patcher = mock.patch("sheet_updater.OUTPUT_DIR", self._tmp)
        self._out_patcher.start()
        self._json_path = os.path.join(self._tmp, "unit_data.json")
        self._json_patcher = mock.patch("convert_to_json.OUTPUT_PATH", self._json_path)
        self._json_patcher.start()
        self.addCleanup(self._json_patcher.stop)
        self.addCleanup(self._out_patcher.stop)
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_main_follows_cumulative_resolution(self):
        _baseline_copy(self._tmp, "unit_data_vbaseline.xlsx")

        # 应用一条变更并保存新版本
        wb, ws, row_map, col_map = sheet_updater.load_workbook()
        sheet_updater.apply_change(ws, row_map, col_map, "爬虫", "单体血量", "300")
        sheet_updater.save_new_sheet(wb, "1.12")

        # 无参 main()：应导出最新版（含变更），而非基准值
        units = convert_to_json.main()
        crawler = next(u for u in units if u["name"] == "爬虫")
        self.assertEqual(crawler["单体血量"], 300)
        with open(self._json_path, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), units)

    def test_main_with_explicit_source_path(self):
        explicit = _baseline_copy(self._tmp, "custom.xlsx")
        units = convert_to_json.main(source_path=explicit)
        crawler = next(u for u in units if u["name"] == "爬虫")
        self.assertEqual(crawler["单体血量"], 263)  # 显式文件：基准值


if __name__ == "__main__":
    unittest.main()
