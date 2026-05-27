"""
Vector Store - Milvus-compatible interface with FAISS-style in-memory index
"""
import asyncio
from typing import List, Dict, Any, Optional
import hashlib
import numpy as np


class VectorStore:
    """
    向量存储接口，支持在线构建索引和高效检索
    内嵌FAISS-style FlatIP索引（全量精确搜索，适合小规模数据集）
    """

    def __init__(self):
        self.client = None
        self.collection_name = "research_papers"
        self.embeddings: Dict[str, List[float]] = {}
        # FAISS-style 索引：id列表 + 矩阵
        self._ids: List[str] = []
        self._matrix: Optional[np.ndarray] = None
        self._dirty = True  # 标记矩阵是否需要重建

    def _build_matrix(self):
        """惰性构建矩阵索引"""
        if not self._ids:
            self._matrix = np.zeros((0, 384), dtype=np.float32)
        else:
            self._matrix = np.array(
                [self.embeddings[iid] for iid in self._ids], dtype=np.float32
            )
        self._dirty = False

    async def initialize(self, uri: str = "./milvus.db"):
        """初始化Milvus客户端"""
        # In production:
        # from pymilvus import MilvusClient
        # self.client = MilvusClient(uri=uri)
        # self.client.create_collection(...)
        self.client = {"connected": True, "uri": uri}
        return True

    async def insert(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """插入文档向量"""
        if ids is None:
            ids = [self._generate_id(t) for t in texts]

        for i, text in enumerate(texts):
            embedding = self._generate_embedding(text)
            self.embeddings[ids[i]] = embedding

            # In production: self.client.insert(...)

        # 新增：更新索引
        self._ids = list(self.embeddings.keys())
        self._dirty = True
        return ids

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filter_expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """向量相似度检索：用矩阵乘法代替逐个余弦计算"""
        query_embedding = self._generate_embedding(query)
        q = np.array(query_embedding, dtype=np.float32).reshape(1, -1)

        # 惰性构建索引矩阵
        if self._dirty:
            self._build_matrix()

        # 批量计算内积（等价于归一化后的余弦相似度）
        # 矩阵shape: (n_vectors, 384)，q shape: (1, 384)
        scores = np.dot(self._matrix, q.T).flatten()  # (n,)

        # 取top_k（用argpartition保持O(n)平均复杂度）
        if scores.shape[0] <= top_k:
            order = np.argsort(scores)[::-1]
        else:
            # partial sort: O(n) instead of O(n log n)
            order = np.argpartition(scores, -top_k)[-top_k:]
            order = order[np.argsort(scores[order])[::-1]]

        results = []
        for idx in order:
            doc_id = self._ids[idx]
            results.append({
                "id": doc_id,
                "score": float(scores[idx]),
                "embedding": self.embeddings[doc_id]
            })

        return results

    async def delete(self, ids: List[str]) -> bool:
        """删除向量"""
        for id_ in ids:
            self.embeddings.pop(id_, None)
        self._ids = list(self.embeddings.keys())
        self._dirty = True
        return True

    async def get_by_id(self, id_: str) -> Optional[Dict[str, Any]]:
        """根据ID获取"""
        return self.embeddings.get(id_)

    def _generate_id(self, text: str) -> str:
        """生成文档ID"""
        return hashlib.md5(text.encode()).hexdigest()[:16]

    def _generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入向量"""
        # 修复：使用确定性哈希而非随机向量——相同文本每次生成相同向量
        # 适用于demo/测试环境；生产环境替换为真实embedding服务
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        seed = int.from_bytes(h[:4], "little")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(384).astype(np.float32)
        # L2归一化：这样内积直接等于余弦相似度
        vec /= (np.linalg.norm(vec) + 1e-8)
        return vec.tolist()

    async def collection_stats(self) -> Dict[str, Any]:
        """获取集合统计"""
        return {
            "total_vectors": len(self.embeddings),
            "collection": self.collection_name,
            "indexed": not self._dirty
        }
