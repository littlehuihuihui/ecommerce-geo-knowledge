"""
RAG 搜索后端
提供语义搜索和问答API
"""
import sys
import os

# 添加本地包路径
PACKAGE_DIR = os.path.join(os.path.dirname(__file__), 'packages')
if os.path.exists(PACKAGE_DIR):
    sys.path.insert(0, PACKAGE_DIR)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import chromadb
from sentence_transformers import SentenceTransformer

app = Flask(__name__)
CORS(app)

# 配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'chroma')
MODEL_NAME = 'BAAI/bge-small-zh-v1.5'

# 全局变量
collection = None
model = None

def init_rag():
    """初始化RAG系统"""
    global collection, model
    
    print("正在加载模型和索引...")
    
    # 加载模型
    try:
        model = SentenceTransformer(MODEL_NAME)
        print(f"✓ 模型加载成功: {MODEL_NAME}")
    except Exception as e:
        print(f"✗ 模型加载失败: {e}")
        model = None
    
    # 加载向量数据库
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = client.get_collection(name="industry_encyclopedia")
        print(f"✓ 索引加载成功，共 {collection.count()} 个向量")
    except Exception as e:
        print(f"✗ 索引加载失败: {e}")
        print("请先运行 build_index.py 构建索引")
        collection = None
    
    print("初始化完成！")

@app.route('/')
def index():
    """搜索页面"""
    return send_from_directory('.', 'search.html')

@app.route('/api/search', methods=['POST'])
def search():
    """语义搜索"""
    if collection is None:
        return jsonify({'error': '索引未加载，请先构建索引'}), 500
    
    data = request.json
    query = data.get('query', '')
    n_results = data.get('n_results', 5)
    
    if not query:
        return jsonify({'error': '查询不能为空'}), 400
    
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # 格式化结果
        formatted_results = []
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            similarity = 1 - distance  # 余弦相似度
            
            # 提取摘要（去掉标题前缀）
            content = doc
            if content.startswith('【'):
                end_idx = content.find('】')
                if end_idx > 0:
                    content = content[end_idx + 1:].strip()
            
            # 截取摘要
            summary = content[:200] + '...' if len(content) > 200 else content
            
            formatted_results.append({
                'title': metadata['title'],
                'url': metadata['url'],
                'category': metadata['category'],
                'content': content,
                'summary': summary,
                'similarity': round(similarity, 4),
                'chunk_index': metadata['chunk_index']
            })
        
        return jsonify({
            'query': query,
            'total': len(formatted_results),
            'results': formatted_results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ask', methods=['POST'])
def ask():
    """
    简单问答（基于检索结果的抽取式问答）
    注意：这是简化版，没有LLM生成，只是返回最相关的内容
    如果需要真正的生成式问答，需要接入LLM
    """
    if collection is None:
        return jsonify({'error': '索引未加载，请先构建索引'}), 500
    
    data = request.json
    question = data.get('question', '')
    n_results = data.get('n_results', 3)
    
    if not question:
        return jsonify({'error': '问题不能为空'}), 400
    
    try:
        results = collection.query(
            query_texts=[question],
            n_results=n_results
        )
        
        # 构建答案（从检索结果中提取关键信息）
        answers = []
        sources = []
        
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            similarity = 1 - distance
            
            # 去掉标题前缀
            content = doc
            if content.startswith('【'):
                end_idx = content.find('】')
                if end_idx > 0:
                    content = content[end_idx + 1:].strip()
            
            answers.append(content)
            sources.append({
                'title': metadata['title'],
                'url': metadata['url'],
                'similarity': round(similarity, 4)
            })
        
        # 简单的答案拼接（真正的RAG需要LLM来生成）
        answer = '\n\n'.join(answers[:2])
        
        return jsonify({
            'question': question,
            'answer': answer,
            'sources': sources,
            'note': '这是基于检索的抽取式回答，如需生成式问答请接入LLM'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def stats():
    """获取索引统计信息"""
    if collection is None:
        return jsonify({'error': '索引未加载'}), 500
    
    return jsonify({
        'total_chunks': collection.count(),
        'model': MODEL_NAME
    })

if __name__ == '__main__':
    init_rag()
    print("\n启动服务器: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
