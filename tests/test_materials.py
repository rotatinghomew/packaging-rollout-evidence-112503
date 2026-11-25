"""从项目根目录执行资料契约检查。"""
from pathlib import Path
import json
import unittest

import numpy as np
from scipy import sparse

DATA = Path(__file__).resolve().parents[1] / "资料"

def load(name):
    """读取已经登记的 UTF-8 JSON 资料。"""
    with (DATA / f"{name}.json").open(encoding="utf-8") as source:
        return json.load(source)

KEYS = {'分配计划': 'assignment', '发货箱': 'box', '装箱明细': 'piece', '售后请求': 'receipt', '照片回单': 'id'}
REFERENCES = [('发货箱', 'assignment', '分配计划', 'assignment'), ('装箱明细', 'box', '发货箱', 'box'), ('售后请求', 'box', '发货箱', 'box'), ('照片回单', 'receipt', '售后请求', 'receipt'), ('照片回单', 'piece', '装箱明细', 'piece')]

class MaterialChecks(unittest.TestCase):
    def test_identity(self):
        """检查来源主键与登记范围。"""
        for collection, field in KEYS.items():
            with self.subTest(collection=collection):
                entries = load(collection)
                self.assertTrue(entries)
                values = [r[field] for r in entries]
                self.assertEqual(len(set(values)), len(entries))
                self.assertNotIn(None, values)

    def test_references(self):
        """核对资料表之间的引用，不改变原记录。"""
        for origin, source_field, target, target_field in REFERENCES:
            with self.subTest(origin=origin, field=source_field):
                codes = {r[target_field] for r in load(target)}
                for row in load(origin):
                    if row[source_field] is not None:
                        self.assertIn(row[source_field], codes)

    def test_data_runtime(self):
        """确认锁定的数组和稀疏矩阵依赖可用，并读取本项目资料。"""
        sizes = np.array([len(load(name)) for name in KEYS], dtype=np.int64)
        self.assertTrue(np.all(sizes > 0))
        self.assertEqual(int(sparse.csr_matrix(sizes.reshape(1, -1)).sum()), int(sizes.sum()))

    def test_related_material(self):
        """检查业务记录、变动与交接凭据是否实际存在。"""
        boxes = {r["box"]: r for r in load("发货箱")}
        pieces = load("装箱明细")
        claims = {r["receipt"]: r for r in load("售后请求")}
        for key, box in boxes.items():
            self.assertEqual(box["pieces"], sum(r["box"] == key for r in pieces))
        self.assertTrue(any(len({r["actual"] for r in pieces if r["box"] == box}) > 1 for box in boxes))
        for claim in claims.values():
            self.assertIsNotNone(boxes[claim["box"]]["delivered"])
            self.assertTrue(set(claim["possible_pieces"]) <= {r["piece"] for r in pieces if r["box"] == claim["box"]})
        for photo in load("照片回单"):
            self.assertIn(photo["piece"], claims[photo["receipt"]]["possible_pieces"])
