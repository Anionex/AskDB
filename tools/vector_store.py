#!/usr/bin/env python3
"""
Vector Store for Semantic Schema Search
使用 ChromaDB 和 Sentence Transformers 实现语义检索
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sqlalchemy.engine import Engine
from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索结果数据类"""
    name: str
    item_type: str  # "table", "column", "business_term"
    similarity: float
    metadata: Dict[str, Any]
    
    def __repr__(self):
        return f"SearchResult(type={self.item_type}, name={self.name}, similarity={self.similarity:.3f})"


class VectorStore:
    """向量存储 - 用于数据库schema的语义检索"""
    
    def __init__(self, persist_directory: str = "data/vector_db"):
        """
        初始化向量存储
        
        Args:
            persist_directory: 持久化存储目录
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        try:
            # 初始化 ChromaDB 客户端
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # 创建或获取集合 - 使用cosine相似度（最适合语义搜索）
            # 注意：如果已有旧的collection使用L2距离，需要清空后重建才能生效
            self.tables_collection = self.client.get_or_create_collection(
                name="tables",
                metadata={"hnsw:space": "cosine"}
            )
            
            self.columns_collection = self.client.get_or_create_collection(
                name="columns",
                metadata={"hnsw:space": "cosine"}
            )
            
            self.business_terms_collection = self.client.get_or_create_collection(
                name="business_terms",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(f"✅ VectorStore initialized at {self.persist_directory}")
            
        except Exception as e:
            logger.error(f"Failed to initialize VectorStore: {e}")
            raise
    
    def get_index_stats(self) -> Dict[str, int]:
        """
        获取索引统计信息
        
        Returns:
            包含各类型索引数量的字典
        """
        try:
            return {
                "tables": self.tables_collection.count(),
                "columns": self.columns_collection.count(),
                "business_terms": self.business_terms_collection.count()
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {"tables": 0, "columns": 0, "business_terms": 0}
    
    def index_tables(self, engine: Engine, progress_callback=None) -> int:
        """
        索引数据库表
        
        Args:
            engine: SQLAlchemy Engine
            progress_callback: 进度回调函数
            
        Returns:
            索引的表数量
        """
        try:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            if not tables:
                logger.warning("No tables found to index")
                return 0
            
            # 准备数据
            ids = []
            documents = []
            metadatas = []
            
            for i, table_name in enumerate(tables):
                try:
                    # 获取表的列信息
                    columns = inspector.get_columns(table_name)
                    column_names = [col['name'] for col in columns]
                    
                    # 获取主键
                    pk_constraint = inspector.get_pk_constraint(table_name)
                    pk_columns = pk_constraint.get('constrained_columns', []) if pk_constraint else []
                    
                    # 获取外键
                    fk_constraints = inspector.get_foreign_keys(table_name)
                    has_fks = len(fk_constraints) > 0
                    
                    # 创建文本表示
                    doc = f"Table: {table_name}. "
                    doc += f"Columns: {', '.join(column_names)}. "
                    if pk_columns:
                        doc += f"Primary key: {', '.join(pk_columns)}. "
                    if has_fks:
                        doc += f"Has foreign keys. "
                    
                    ids.append(f"table_{table_name}")
                    documents.append(doc)
                    metadatas.append({
                        "table_name": table_name,
                        "column_count": len(columns),
                        "has_foreign_keys": has_fks
                    })
                    
                    if progress_callback:
                        progress_callback(i + 1, len(tables), f"Indexing table: {table_name}")
                        
                except Exception as e:
                    logger.warning(f"Failed to index table {table_name}: {e}")
                    continue
            
            # 批量添加到 ChromaDB
            if ids:
                self.tables_collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
            
            logger.info(f"✅ Indexed {len(ids)} tables")
            return len(ids)
            
        except Exception as e:
            logger.error(f"Failed to index tables: {e}")
            return 0
    
    def index_columns(self, engine: Engine, progress_callback=None) -> int:
        """
        索引数据库列
        
        Args:
            engine: SQLAlchemy Engine
            progress_callback: 进度回调函数
            
        Returns:
            索引的列数量
        """
        try:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            ids = []
            documents = []
            metadatas = []
            
            total_columns = 0
            for table_name in tables:
                columns = inspector.get_columns(table_name)
                total_columns += len(columns)
            
            current = 0
            
            for table_name in tables:
                try:
                    columns = inspector.get_columns(table_name)
                    pk_constraint = inspector.get_pk_constraint(table_name)
                    pk_columns = set(pk_constraint.get('constrained_columns', []) if pk_constraint else [])
                    
                    fk_constraints = inspector.get_foreign_keys(table_name)
                    fk_columns = {}
                    for fk in fk_constraints:
                        for col in fk.get('constrained_columns', []):
                            fk_columns[col] = fk.get('referred_table', '')
                    
                    for column in columns:
                        col_name = column['name']
                        col_type = str(column['type'])
                        is_pk = col_name in pk_columns
                        is_fk = col_name in fk_columns
                        
                        # 创建文本表示
                        doc = f"Column: {table_name}.{col_name}. "
                        doc += f"Type: {col_type}. "
                        if is_pk:
                            doc += "Primary key. "
                        if is_fk:
                            doc += f"Foreign key to {fk_columns[col_name]}. "
                        if not column.get('nullable', True):
                            doc += "Not nullable. "
                        
                        ids.append(f"column_{table_name}_{col_name}")
                        documents.append(doc)
                        metadatas.append({
                            "table_name": table_name,
                            "column_name": col_name,
                            "data_type": col_type,
                            "is_primary_key": is_pk,
                            "is_foreign_key": is_fk
                        })
                        
                        current += 1
                        if progress_callback:
                            progress_callback(current, total_columns, f"Indexing: {table_name}.{col_name}")
                            
                except Exception as e:
                    logger.warning(f"Failed to index columns for table {table_name}: {e}")
                    continue
            
            # 批量添加到 ChromaDB
            if ids:
                self.columns_collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
            
            logger.info(f"✅ Indexed {len(ids)} columns")
            return len(ids)
            
        except Exception as e:
            logger.error(f"Failed to index columns: {e}")
            return 0
    
    def index_business_terms(self, json_file: str = "data/business_metadata.json", 
                            progress_callback=None) -> int:
        """
        索引业务术语
        
        Args:
            json_file: 业务元数据JSON文件路径
            progress_callback: 进度回调函数
            
        Returns:
            索引的业务术语数量
        """
        try:
            json_path = Path(json_file)
            if not json_path.exists():
                logger.warning(f"Business metadata file not found: {json_file}")
                return 0
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            terms = data.get('business_terms', [])
            if not terms:
                logger.warning("No business terms found in metadata")
                return 0
            
            ids = []
            documents = []
            metadatas = []
            
            for i, term in enumerate(terms):
                term_name = term.get('name', '')
                definition = term.get('definition', '')
                formula = term.get('formula', '')
                related_tables = term.get('related_tables', [])
                related_columns = term.get('related_columns', [])
                
                # 创建丰富的文本表示用于向量搜索
                # 包含多种描述方式以提高搜索召回率
                doc = f"业务术语/Business term: {term_name}\n"
                if definition:
                    doc += f"定义/Definition: {definition}\n"
                if formula:
                    doc += f"计算公式/Formula: {formula}\n"
                if related_tables:
                    doc += f"相关表/Related tables: {', '.join(related_tables)}\n"
                if related_columns:
                    doc += f"相关字段/Related columns: {', '.join(related_columns)}\n"
                
                # 添加关键词以提升搜索效果
                doc += f"Keywords: {term_name} 指标 metric KPI"
                
                ids.append(f"term_{term_name}")
                documents.append(doc)
                metadatas.append({
                    "term_name": term_name,
                    "definition": definition,
                    "formula": formula,
                    "related_tables": json.dumps(related_tables, ensure_ascii=False),
                    "related_columns": json.dumps(related_columns, ensure_ascii=False)
                })
                
                if progress_callback:
                    progress_callback(i + 1, len(terms), f"Indexing term: {term_name}")
            
            # 批量添加到 ChromaDB
            if ids:
                self.business_terms_collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
            
            logger.info(f"✅ Indexed {len(ids)} business terms")
            return len(ids)
            
        except Exception as e:
            logger.error(f"Failed to index business terms: {e}")
            return 0
    
    def search(self, query: str, top_k: int = 5, 
              search_types: List[str] = None) -> List[SearchResult]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            search_types: 搜索类型列表 ["table", "column", "business_term"]
            
        Returns:
            SearchResult 列表
        """
        if search_types is None:
            search_types = ["table", "column", "business_term"]
        
        results = []
        
        try:
            # 搜索表
            if "table" in search_types:
                try:
                    table_results = self.tables_collection.query(
                        query_texts=[query],
                        n_results=min(top_k, self.tables_collection.count()) if self.tables_collection.count() > 0 else 1
                    )
                    
                    if table_results['ids'] and table_results['ids'][0]:
                        for i, doc_id in enumerate(table_results['ids'][0]):
                            metadata = table_results['metadatas'][0][i]
                            distance = table_results['distances'][0][i]
                            # 使用更鲁棒的相似度计算：1 / (1 + distance)
                            # 这样distance=0时similarity=1, distance越大similarity越接近0
                            similarity = 1.0 / (1.0 + distance)
                            
                            results.append(SearchResult(
                                name=metadata['table_name'],
                                item_type="table",
                                similarity=similarity,
                                metadata=metadata
                            ))
                except Exception as e:
                    logger.debug(f"Table search error: {e}")
            
            # 搜索列
            if "column" in search_types:
                try:
                    column_results = self.columns_collection.query(
                        query_texts=[query],
                        n_results=min(top_k, self.columns_collection.count()) if self.columns_collection.count() > 0 else 1
                    )
                    
                    if column_results['ids'] and column_results['ids'][0]:
                        for i, doc_id in enumerate(column_results['ids'][0]):
                            metadata = column_results['metadatas'][0][i]
                            distance = column_results['distances'][0][i]
                            similarity = 1.0 / (1.0 + distance)
                            
                            results.append(SearchResult(
                                name=f"{metadata['table_name']}.{metadata['column_name']}",
                                item_type="column",
                                similarity=similarity,
                                metadata=metadata
                            ))
                except Exception as e:
                    logger.debug(f"Column search error: {e}")
            
            # 搜索业务术语
            if "business_term" in search_types:
                try:
                    term_results = self.business_terms_collection.query(
                        query_texts=[query],
                        n_results=min(top_k, self.business_terms_collection.count()) if self.business_terms_collection.count() > 0 else 1
                    )
                    
                    if term_results['ids'] and term_results['ids'][0]:
                        for i, doc_id in enumerate(term_results['ids'][0]):
                            metadata = term_results['metadatas'][0][i]
                            distance = term_results['distances'][0][i]
                            similarity = 1.0 / (1.0 + distance)
                            
                            results.append(SearchResult(
                                name=metadata['term_name'],
                                item_type="business_term",
                                similarity=similarity,
                                metadata=metadata
                            ))
                except Exception as e:
                    logger.debug(f"Business term search error: {e}")
            
            # 按相似度排序
            results.sort(key=lambda x: x.similarity, reverse=True)
            
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def clear_all_indexes(self):
        """清空所有索引"""
        try:
            self.client.delete_collection("tables")
            self.client.delete_collection("columns")
            self.client.delete_collection("business_terms")
            
            # 重新创建集合
            self.tables_collection = self.client.get_or_create_collection("tables")
            self.columns_collection = self.client.get_or_create_collection("columns")
            self.business_terms_collection = self.client.get_or_create_collection("business_terms")
            
            logger.info("✅ All indexes cleared")
        except Exception as e:
            logger.error(f"Failed to clear indexes: {e}")
            raise


# 创建全局实例
vector_store = VectorStore()


