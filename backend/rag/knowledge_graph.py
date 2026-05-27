"""
Knowledge Graph Manager - Neo4j Integration
Multi-granularity research knowledge graph
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

class KnowledgeGraphManager:
    """
    多粒度研究知识图谱管理器
    支持论文、概念、实验、任务等多种实体类型的统一管理
    """
    
    def __init__(self):
        self.driver = None
        self.cache: Dict[str, Any] = {}
        # 关键词索引：token -> set(node_ids)，避免每次query做全量json.dumps
        self._keyword_index: Dict[str, set] = {}
        
    async def initialize(self, uri: str = "bolt://localhost:7687", 
                         username: str = "neo4j", password: str = "password"):
        """初始化Neo4j连接"""
        # In production:
        # from neo4j import GraphDatabase
        # self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.driver = {"connected": True, "uri": uri}
        await self._create_constraints()
        
    async def _create_constraints(self):
        """创建索引和约束"""
        # In production: execute CREATE CONSTRAINT queries
        pass
        
    async def _reindex_all(self):
        """全量重建关键词索引"""
        self._keyword_index.clear()
        for node in self.cache.values():
            self._index_node(node)

    def _index_node(self, node: Dict):
        """将节点的可检索字段分词后加入倒排索引"""
        import re
        # 提取所有字符串字段拼成一个大文本
        text_fields = []
        for key in ("title", "abstract", "name", "methods"):
            val = node.get(key)
            if val:
                if isinstance(val, list):
                    text_fields.extend(str(v) for v in val)
                else:
                    text_fields.append(str(val))
        text = " ".join(text_fields).lower()
        # 简单分词：按非字母数字边界切分，过滤短词
        tokens = set(re.findall(r"[a-z0-9]{2,}", text))
        for token in tokens:
            if token not in self._keyword_index:
                self._keyword_index[token] = set()
            self._keyword_index[token].add(node["id"])

    async def add_paper(self, paper: Dict[str, Any]) -> str:
        """添加论文节点"""
        paper_id = paper.get("paper_id", f"paper_{datetime.now().timestamp()}")
        
        node = {
            "id": paper_id,
            "type": "paper",
            "title": paper.get("title", ""),
            "authors": paper.get("authors", []),
            "year": paper.get("year", 2024),
            "venue": paper.get("venue", ""),
            "abstract": paper.get("abstract", ""),
            "citations": paper.get("citations", 0),
            "relevance_score": paper.get("relevance_score", 0.5),
            "methods": paper.get("methods", []),
            "created_at": datetime.now().isoformat()
        }
        
        # In production: Cypher CREATE
        self.cache[paper_id] = node
        self._index_node(node)
        return paper_id
        
    async def add_method(self, method_name: str, properties: Dict = None) -> str:
        """添加方法论节点"""
        method_id = f"method_{method_name}"
        node = {
            "id": method_id,
            "type": "method",
            "name": method_name,
            "properties": properties or {},
            "papers_using": []
        }
        self.cache[method_id] = node
        self._index_node(node)
        return method_id

    async def update_node(self, node_id: str, properties: Dict) -> bool:
        """更新节点属性"""
        if node_id in self.cache:
            self.cache[node_id].update(properties)
            # 重建该节点的索引（简单做法：删除旧token再重新索引）
            # 完整做法应精确删除旧token，但成本高，这里简化处理
            self._reindex_all()
            return True
        return False
        
    async def add_relationship(
        self, from_id: str, to_id: str, relation_type: str, properties: Dict = None
    ) -> bool:
        """添加关系边"""
        edge = {
            "from": from_id,
            "to": to_id,
            "type": relation_type,
            "properties": properties or {},
            "created_at": datetime.now().isoformat()
        }
        return True
        
    async def query_by_keyword(self, keyword: str, limit: int = 20) -> List[Dict]:
        """按关键词查询：用倒排索引替代全量json.dumps扫描"""
        import re
        tokens = set(re.findall(r"[a-z0-9]{2,}", keyword.lower()))
        if not tokens:
            return []

        # 取所有token命中集合的交集
        candidate_ids = None
        for token in tokens:
            hit_ids = self._keyword_index.get(token, set())
            if candidate_ids is None:
                candidate_ids = hit_ids
            else:
                candidate_ids &= hit_ids

        if not candidate_ids:
            return []

        # 从cache取结果并按相关性排序
        results = []
        for node_id in list(candidate_ids)[:limit * 3]:  # 多取些再过滤
            node = self.cache.get(node_id)
            if node:
                results.append(node)

        results.sort(
            key=lambda n: (
                n.get("relevance_score", 0),
                n.get("citations", 0)
            ),
            reverse=True
        )
        return results[:limit]
        
    async def query_papers_by_method(self, method: str) -> List[Dict]:
        """查询使用某方法的论文"""
        results = []
        for node in self.cache.values():
            if node.get("type") == "paper" and method in node.get("methods", []):
                results.append(node)
        return results
        
    async def get_subgraph(self, root_id: str, depth: int = 2) -> Dict[str, Any]:
        """获取子图：正确的BFS，按depth逐层扩展"""
        visited = {root_id}
        from collections import deque
        queue = deque([(root_id, 0)])
        nodes = []
        edges = []

        while queue:
            node_id, d = queue.popleft()  # 左出右进，才是BFS
            if d >= depth:
                continue

            node = self.cache.get(node_id, {"id": node_id, "type": "unknown"})
            if node not in nodes:
                nodes.append(node)

            # 遍历所有节点找邻居：生产级应查Neo4j，这里修复遍历逻辑
            for other_id, other in self.cache.items():
                if other_id not in visited and other_id != node_id:
                    # 简单启发式：如果other和node有相同type或关联属性，认为是邻居
                    # 实际生产应通过边关系表查询，这里保持API契约不变
                    if other.get("type") == node.get("type") or \
                       set(other.get("methods", [])) & set(node.get("methods", [])):
                        visited.add(other_id)
                        queue.append((other_id, d + 1))
                        edges.append({
                            "from": node_id,
                            "to": other_id,
                            "type": "related"
                        })

        return {"nodes": nodes, "edges": edges}
        
    async def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计"""
        types = {}
        for node in self.cache.values():
            t = node.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        return {
            "total_nodes": len(self.cache),
            "by_type": types
        }
        
    async def close(self):
        """关闭连接"""
        if self.driver:
            await asyncio.sleep(0.01)
