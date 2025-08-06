import json
import pickle
import networkx as nx
from datetime import datetime
import numpy as np
import re
import os
from init import Global
from openai import OpenAI
from sentence_transformers import SentenceTransformer
import spacy
import requests

class GraphRAGMemory:
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.conversations = []
        self.entity_embeddings = {}
        self.conversation_embeddings = {}
        
        self.init_models()
        dirname = os.path.dirname(Global.character_json)
        self.memory_path = os.path.join(dirname, 'memory')
        if os.path.exists(self.memory_path):
            self.load_from_file(self.memory_path)
        
    def init_models(self):
        self.embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", local_files_only=True, device=Global.device)
        self.nlp = spacy.load("zh_core_web_sm")
            
    def extract_entities(self, text):
        entities = []
        
        doc = self.nlp(text)
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char,
                'confidence': 1.0
            })
            
        enhanced_entities = self.enhance_entities_with_llm(text, entities)
        
        return enhanced_entities
    
    def enhance_entities_with_llm(self, text, initial_entities):
        prompt = f"""
        分析以下文本，提取所有重要的实体（人名、地名、机构、概念等），并识别它们的类型和关系。

        文本：{text}

        已识别的实体：{[e['text'] for e in initial_entities]}

        请以JSON格式返回增强后的实体列表，包含以下字段：
        - text: 实体文本
        - type: 实体类型
        - description: 实体描述
        - importance: 重要性评分(0-1)
        
        JSON输出示例：
        [
            {{
                "text": "张三",
                "type": "人名",
                "description": "公司CEO，负责战略决策",
                "importance": 0.9
            }},
            {{
                "text": "北京",
                "type": "地名",
                "description": "中国首都，重要政治经济中心",
                "importance": 0.8
            }}
        ]
        
        只返回JSON，不要其他内容。
        """
        
        response = self.call_llm(prompt)
        enhanced_entities = json.loads(response)
        
        entity_texts = {e['text'] for e in initial_entities}
        for ent in enhanced_entities:
            if ent['text'] not in entity_texts:
                initial_entities.append(ent)
                
        return initial_entities

    def extract_relationships(self, text, entities):
        if len(entities) < 2:
            return []
            
        entity_texts = [e['text'] for e in entities]
        
        prompt = f"""
        分析以下文本中实体之间的关系：

        文本：{text}
        实体：{entity_texts}

        请以JSON格式返回关系列表，每个关系包含：
        - source: 源实体
        - target: 目标实体  
        - relation: 关系类型
        - confidence: 置信度(0-1)
        - evidence: 支持证据文本

        JSON输出示例：
        [
            {{
                "source": "张三",
                "target": "ABC公司",
                "relation": "担任CEO",
                "confidence": 0.95,
                "evidence": "张三担任ABC公司的首席执行官"
            }},
            {{
                "source": "ABC公司",
                "target": "北京",
                "relation": "总部位于",
                "confidence": 0.9,
                "evidence": "ABC公司总部设在北京市朝阳区"
            }}
        ]

        只返回JSON数组，不要其他内容。
        """
        
        response = self.call_llm(prompt)
        relationships = json.loads(response)
        return relationships
    
    def call_llm(self, prompt):
        if Global.auxiliary['base_url'] and Global.auxiliary['api_key']:
            self.client = OpenAI(
                base_url=Global.auxiliary['base_url'],
                api_key=Global.auxiliary['api_key']
            )

            response = self.client.chat.completions.create(
                model=Global.auxiliary['chat_model'],
                messages=[{'role':'user', 'content':prompt}]
            )

            match = re.search(r'```json\s*(.*?)\s*```', response.choices[0].message.content, re.DOTALL)
            return match.group(1).strip()
        else:
            while True:
                payload = {
                    "model": "deepseek-v3",
                    "messages": [{'role':'user', 'content':prompt}],
                    "stream": False
                }
                response = requests.post('https://api.pearktrue.cn/api/aichat/', json=payload)
                response_data = response.json()

                if 'content' in response_data:
                    match = re.search(r'```json\s*(.*?)\s*```', response_data['content'], re.DOTALL)
                    if match:
                        return match.group(1).strip()
    
    def add_conversation(self, conversation, conversation_id = None):
        if conversation_id is None:
            conversation_id = f"conv_{len(self.conversations)}"
        
        full_text = ''
        for msg in conversation:
            if msg['role'] == 'user':
                full_text += msg['content'].replace('我', 'user').replace('你', 'assistant') + ' '
            elif msg['role'] == 'assistant':
                full_text += msg['content'].replace('我', 'assistant').replace('你', 'user') + ' '
        
        conv_embedding = self.embedding_model.encode(full_text)
        self.conversation_embeddings[conversation_id] = conv_embedding
        
        conv_data = {
            'id': conversation_id,
            'messages': conversation,
            'timestamp': datetime.now().isoformat(),
            'embedding': conv_embedding.tolist()
        }
        self.conversations.append(conv_data)
        
        entities = self.extract_entities(full_text)
        relationships = self.extract_relationships(full_text, entities)
        
        for entity in entities:
            entity_text = entity['text']
            
            entity_embedding = self.embedding_model.encode(entity_text)
            self.entity_embeddings[entity_text] = entity_embedding
            
            if not self.graph.has_node(entity_text):
                self.graph.add_node(entity_text, 
                                  type=entity.get('type', 'unknown'),
                                  description=entity.get('description', ''),
                                  importance=entity.get('importance', 0.5),
                                  first_seen=conv_data['timestamp'],
                                  conversations=[conversation_id],
                                  embedding=entity_embedding.tolist())
            else:
                if conversation_id not in self.graph.nodes[entity_text].get('conversations', []):
                    self.graph.nodes[entity_text]['conversations'].append(conversation_id)
        
        for rel in relationships:
            source = rel['source']
            target = rel['target']
            relation = rel['relation']
            
            if source in [e['text'] for e in entities] and target in [e['text'] for e in entities]:
                self.graph.add_edge(source, target,
                                  relation=relation,
                                  confidence=rel.get('confidence', 0.5),
                                  evidence=rel.get('evidence', ''),
                                  conversation_id=conversation_id,
                                  timestamp=conv_data['timestamp'])
        
        self.save_to_file(self.memory_path)
    
    def semantic_search(self, query, top_k = 5, similarity_threshold=0.7):
        query = query.replace('我', 'user')
        query_embedding = self.embedding_model.encode(query)
        
        results = []
        
        for conv in self.conversations:
            conv_embedding = np.array(conv['embedding'])
            similarity = np.dot(query_embedding, conv_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(conv_embedding)
            )
            
            if similarity > similarity_threshold:
                results.append({
                    'type': 'conversation',
                    'id': conv['id'],
                    'similarity': float(similarity),
                    'content': conv['messages'],
                    'timestamp': conv['timestamp']
                })
        
        for entity_text, entity_embedding in self.entity_embeddings.items():
            similarity = np.dot(query_embedding, entity_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(entity_embedding)
            )
            
            if similarity > similarity_threshold:
                results.append({
                    'type': 'entity',
                    'text': entity_text,
                    'similarity': float(similarity),
                    'info': self.graph.nodes[entity_text]
                })
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def build_context(self, relevant_info):
        context_parts = []
        
        for info in relevant_info:
            if info['type'] == 'conversation':
                conv_text = "\n".join([f"{msg.get('speaker', '未知')}: {msg.get('content', '')}" 
                                     for msg in info['content']])
                context_parts.append(f"对话片段 (相似度: {info['similarity']:.2f}):\n{conv_text}")
            elif info['type'] == 'entity':
                entity_info = info['info']
                context_parts.append(f"实体: {info['text']} (相似度: {info['similarity']:.2f})\n"
                                    f"类型: {entity_info.get('type', '未知')}\n"
                                    f"描述: {entity_info.get('description', '无描述')}")
        
        return "\n\n".join(context_parts)
    
    def save_to_file(self, filepath):
        conversations_serializable = []
        for conv in self.conversations:
            conv_copy = conv.copy()
            if isinstance(conv_copy.get('embedding'), np.ndarray):
                conv_copy['embedding'] = conv_copy['embedding'].tolist()
            conversations_serializable.append(conv_copy)
        
        data = {
            'conversations': conversations_serializable,
            'graph_nodes': dict(self.graph.nodes(data=True)),
            'graph_edges': [(u, v, d) for u, v, d in self.graph.edges(data=True)],
            'entity_embeddings': {k: v.tolist() for k, v in self.entity_embeddings.items()},
            'conversation_embeddings': {k: v.tolist() for k, v in self.conversation_embeddings.items()}
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
    
    def load_from_file(self, filepath):
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.graph = nx.MultiDiGraph()
        self.graph.add_nodes_from(data['graph_nodes'].items())
        self.graph.add_edges_from(data['graph_edges'])
        
        self.conversations = data['conversations']
        self.entity_embeddings = {k: np.array(v) for k, v in data['entity_embeddings'].items()}
        self.conversation_embeddings = {k: np.array(v) for k, v in data['conversation_embeddings'].items()}
