"""
构建RAG向量索引
从所有HTML页面提取文本，分块，向量化，存入ChromaDB
"""
import sys
import os
import re
import glob


def _ensure_sqlite_supported():
    """chromadb 要求 sqlite3 >= 3.35；旧版 Python（如 Windows 上的 3.8）自带更低版本。

    做法：在任何地方 import sqlite3 之前，先从本机其他 Python 安装（或环境变量
    SQLITE3_DLL 指定的路径）预加载一个更新的 sqlite3.dll。DLL 基名必须与原文件
    同名（sqlite3.dll），Windows 才会复用已加载模块，从而不改动 Python 安装。
    注意：必须早于首次 import sqlite3 执行，否则 _sqlite3.pyd 已绑定旧 DLL。
    """
    if sys.version_info >= (3, 9):
        # 现代 Python 自带的 sqlite3 已满足 chromadb 要求，直接跳过
        try:
            import sqlite3
            if tuple(int(x) for x in sqlite3.sqlite_version.split('.')[:3]) >= (3, 35, 0):
                return
        except Exception:
            return

    import ctypes
    import glob
    import shutil
    import tempfile

    candidates = []
    env_dll = os.environ.get('SQLITE3_DLL')
    if env_dll:
        candidates.append(env_dll)
    home = os.path.expanduser('~')
    roots = [
        os.path.join(home, 'AppData', 'Local', 'Programs', 'Python'),
        r'C:\Program Files',
        'C:\\',
    ]
    for root in roots:
        if os.path.isdir(root):
            candidates.extend(sorted(glob.glob(os.path.join(root, '**', 'DLLs', 'sqlite3.dll'),
                                              recursive=False), reverse=True))
    # 兜底：按已知版本目录直接拼路径
    for ver in ('Python312', 'Python311', 'Python310', 'Python39'):
        candidates.append(os.path.join(home, 'AppData', 'Local', 'Programs', 'Python', ver, 'DLLs', 'sqlite3.dll'))

    tmp_dir = os.path.join(tempfile.gettempdir(), 'sqlite3_shim')
    for dll in candidates:
        if not dll or not os.path.exists(dll):
            continue
        try:
            os.makedirs(tmp_dir, exist_ok=True)
            target = os.path.join(tmp_dir, 'sqlite3.dll')
            shutil.copy2(dll, target)
            ctypes.CDLL(target)          # 必须早于任何 import sqlite3
        except Exception:
            continue
        import sqlite3
        if tuple(int(x) for x in sqlite3.sqlite_version.split('.')[:3]) >= (3, 35, 0):
            print("[sqlite shim] 已预加载 %s → sqlite3 %s" % (dll, sqlite3.sqlite_version))
            return
    print("[sqlite shim] 未找到可用的新版 sqlite3.dll，"
          "请设置环境变量 SQLITE3_DLL 指向 sqlite3(>=3.35) 的 DLL 后重试")


_ensure_sqlite_supported()

def _ensure_posthog_importable():
    """chromadb 的遥测模块会 import posthog；新版 posthog 需要 Python >= 3.9。

    若当前环境无法导入 posthog，则注入 rag/_stubs 下的极简桩模块
    （不发送任何遥测数据），保证 chromadb 可用。
    """
    try:
        import posthog  # noqa: F401
        return
    except Exception:
        pass
    stub_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_stubs')
    if os.path.isdir(stub_dir) and stub_dir not in sys.path:
        sys.path.insert(0, stub_dir)
        print("[posthog stub] 真实 posthog 不可用，已启用空实现桩模块（不上报任何数据）")


_ensure_posthog_importable()


# 依赖路径：优先使用当前环境（site-packages）已安装的包；
# 仅当导入失败时，才回退到本地打包目录（旧环境打包的包可能不兼容新版 Python）。
PACKAGE_DIR = os.path.join(os.path.dirname(__file__), 'packages')
RAG_PKGS = r'D:\rag_pkgs'


def _ensure_deps_on_path():
    for mod in ('bs4', 'lxml', 'sentence_transformers', 'chromadb'):
        try:
            __import__(mod)
        except Exception:
            break
    else:
        return  # 环境已具备全部依赖，无需注入打包路径
    for p in (PACKAGE_DIR, RAG_PKGS):
        if os.path.exists(p):
            sys.path.insert(0, p)


_ensure_deps_on_path()

from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions

# 配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'chroma')
MODEL_NAME = 'BAAI/bge-small-zh-v1.5'
CHUNK_SIZE = 500  # 字符数
CHUNK_OVERLAP = 100  # 重叠字符数

# 需要索引的HTML文件（排除导航等重复内容）
# 说明：改为自动发现根目录页面，避免新增页面后清单过期。
# 如需排除某页，加入 EXCLUDE 即可。
EXCLUDE_FILES = {
    'education.html',      # 跳转桩页
    'knowledge-graph.html',# 空壳页，KG 内容由 JS 动态渲染
}
EXCLUDE_PREFIX = '_'      # 下划线开头的临时/开发文件不索引
MIN_SIZE_KB = 1.0         # 小于 1KB 的页面视为跳转桩页，跳过
# 优先索引顺序（其余按文件名字典序追加）
PRIORITY_FILES = [
    'index.html', 'frameworks.html', 'metrics.html', 'methodology.html',
    'interview.html', 'graph.html', 'knowledge-graph.html',
]

def _is_indexable(filepath):
    """体积过小的页面（跳转桩页）不索引"""
    try:
        return os.path.getsize(filepath) / 1024.0 >= MIN_SIZE_KB
    except OSError:
        return False


def get_html_files():
    """自动发现根目录与子目录下所有需索引的 HTML 页面"""
    html_files = []

    # 根目录页面（自动发现）
    discovered = sorted(
        f for f in os.listdir(BASE_DIR)
        if f.endswith('.html')
        and f not in EXCLUDE_FILES
        and not f.startswith(EXCLUDE_PREFIX)
    )
    ordered = [f for f in PRIORITY_FILES if f in discovered] + \
              [f for f in discovered if f not in PRIORITY_FILES]
    for f in ordered:
        filepath = os.path.join(BASE_DIR, f)
        if os.path.exists(filepath) and _is_indexable(filepath):
            html_files.append({
                'path': filepath,
                'url': f'../{f}',
                'category': '知识框架'
            })

    # 子目录页面
    sub_dirs = ['新能源', '旅游业', '物流']
    for sub_dir in sub_dirs:
        dir_path = os.path.join(BASE_DIR, sub_dir)
        if os.path.isdir(dir_path):
            for filename in sorted(os.listdir(dir_path)):
                if not filename.endswith('.html'):
                    continue
                filepath = os.path.join(dir_path, filename)
                if not _is_indexable(filepath):
                    continue
                html_files.append({
                    'path': filepath,
                    'url': f'../{sub_dir}/{filename}',
                    'category': sub_dir
                })

    return html_files

def extract_text_from_html(filepath):
    """从HTML提取纯文本内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'lxml')
    
    # 移除导航栏、脚本、样式
    for tag in soup(['nav', 'script', 'style', 'header', 'footer']):
        if tag.get('class') and ('encyclopedia-nav' in tag.get('class', []) or 'nav' in tag.get('class', [])):
            tag.decompose()
    
    # 获取标题
    title = ''
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)
    else:
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
    
    # 获取正文文本
    main_content = soup.find('main') or soup.find('div', class_='container') or soup.find('div', class_='app')
    
    if main_content:
        text = main_content.get_text(separator='\n', strip=True)
    else:
        text = soup.get_text(separator='\n', strip=True)
    
    # 清理多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return title, text

def chunk_text(text, title, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """将文本分块"""
    chunks = []
    
    # 先按段落分割
    paragraphs = text.split('\n\n')
    
    current_chunk = ''
    current_length = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        para_length = len(para)
        
        if current_length + para_length <= chunk_size:
            # 加入当前块
            if current_chunk:
                current_chunk += '\n\n'
            current_chunk += para
            current_length += para_length + 2
        else:
            # 当前块满了，保存
            if current_chunk:
                chunks.append(current_chunk)
            
            # 如果段落本身比chunk大，就拆分
            if para_length > chunk_size:
                for i in range(0, para_length, chunk_size - overlap):
                    chunk = para[i:i + chunk_size]
                    if len(chunk) > 50:  # 太短的块不要
                        chunks.append(chunk)
                current_chunk = ''
                current_length = 0
            else:
                current_chunk = para
                current_length = para_length
    
    if current_chunk:
        chunks.append(current_chunk)
    
    # 给每个块加上标题前缀
    titled_chunks = []
    for i, chunk in enumerate(chunks):
        titled_chunk = f"【{title}】\n{chunk}"
        titled_chunks.append({
            'text': titled_chunk,
            'chunk_index': i,
            'total_chunks': len(chunks)
        })
    
    return titled_chunks

def main():
    print("=" * 60)
    print("构建 RAG 向量索引")
    print("=" * 60)
    
    # 1. 获取所有HTML文件
    print("\n1. 扫描HTML文件...")
    html_files = get_html_files()
    print(f"   找到 {len(html_files)} 个HTML文件")
    
    # 2. 提取文本并分块
    print("\n2. 提取文本并分块...")
    all_chunks = []
    
    for file_info in html_files:
        filepath = file_info['path']
        try:
            title, text = extract_text_from_html(filepath)
            chunks = chunk_text(text, title)
            
            for chunk in chunks:
                all_chunks.append({
                    'text': chunk['text'],
                    'title': title,
                    'url': file_info['url'],
                    'category': file_info['category'],
                    'chunk_index': chunk['chunk_index']
                })
            
            print(f"   ✓ {title}: {len(chunks)} 个块")
        except Exception as e:
            print(f"   ✗ {filepath}: {e}")
    
    print(f"\n   总共 {len(all_chunks)} 个文本块")
    
    # 3. 加载embedding模型
    print(f"\n3. 加载Embedding模型: {MODEL_NAME}")
    print("   首次运行会自动下载模型，请稍候...")
    
    try:
        model = SentenceTransformer(MODEL_NAME)
        print("   ✓ 模型加载成功")
    except Exception as e:
        print(f"   ✗ 模型加载失败: {e}")
        print("\n尝试使用备用方案...")
        # 备用：使用Chroma内置的embedding（可能需要联网）
        model = None
    
    # 4. 创建ChromaDB集合
    print("\n4. 创建向量数据库...")
    
    os.makedirs(CHROMA_PATH, exist_ok=True)
    
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # 删除已存在的集合
    try:
        client.delete_collection(name="industry_encyclopedia")
        print("   已删除旧索引")
    except:
        pass
    
    if model:
        # 使用自定义embedding函数
        class SentenceTransformerEmbeddingFunction(embedding_functions.EmbeddingFunction):
            def __init__(self, model):
                self.model = model
            
            def __call__(self, input):
                return self.model.encode(input, normalize_embeddings=True).tolist()
        
        ef = SentenceTransformerEmbeddingFunction(model)
        collection = client.create_collection(
            name="industry_encyclopedia",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"}
        )
    else:
        # 使用默认embedding
        collection = client.create_collection(
            name="industry_encyclopedia",
            metadata={"hnsw:space": "cosine"}
        )
    
    # 5. 批量添加数据
    print("\n5. 向量化并存入数据库...")
    
    batch_size = 50
    total = len(all_chunks)
    
    for i in range(0, total, batch_size):
        batch = all_chunks[i:i+batch_size]
        
        ids = [f"chunk_{j}" for j in range(i, i+len(batch))]
        documents = [chunk['text'] for chunk in batch]
        metadatas = [{
            'title': chunk['title'],
            'url': chunk['url'],
            'category': chunk['category'],
            'chunk_index': chunk['chunk_index']
        } for chunk in batch]
        
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        progress = min(i + batch_size, total)
        print(f"   进度: {progress}/{total} ({int(progress/total*100)}%)")
    
    # 6. 验证
    print("\n6. 验证索引...")
    count = collection.count()
    print(f"   索引中共有 {count} 个向量")
    
    # 测试搜索
    results = collection.query(
        query_texts=["SaaS的核心指标是什么"],
        n_results=3
    )
    
    print("\n   测试搜索: 'SaaS的核心指标是什么'")
    for i, doc in enumerate(results['documents'][0]):
        title = results['metadatas'][0][i]['title']
        score = results['distances'][0][i]
        print(f"   {i+1}. {title} (相似度: {1-score:.3f})")
    
    print("\n" + "=" * 60)
    print("索引构建完成！")
    print("=" * 60)

if __name__ == '__main__':
    main()
