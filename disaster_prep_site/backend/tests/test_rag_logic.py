import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document

# テスト対象モジュール
from backend.app import rag_logic 

@pytest.fixture(autouse=True)
def mock_rag_components(monkeypatch):
    """
    このモジュール内の全てのテストに対し、RAGロジックに不可欠なコンポーネントを自動的にモック化します。
    これにより、実際の初期化処理（API呼び出し、ファイルシステムアクセス）を防ぎ、
    llm、embeddings、vector_store のための制御可能なモックを提供します。
    """
    # rag_logicがインポート時に直接環境変数を読み込もうとする場合に備えてモック化
    monkeypatch.setenv("GOOGLE_API_KEY", "fake_api_key_for_testing")
    
    # initialize_rag_componentsがインポート時または呼び出し時に実行される場合に実際の初期化を防ぐ
    # また、initialize_rag_componentsが設定するグローバル変数もモック化する
    monkeypatch.setattr(rag_logic, 'is_initialized', True) # ほとんどのテストでは初期化済みとみなす
    
    # LLM、Embeddings、VectorStoreのインスタンスをモック化
    mock_llm_instance = MagicMock()
    monkeypatch.setattr(rag_logic, 'llm', mock_llm_instance)
    
    mock_embeddings_instance = MagicMock()
    monkeypatch.setattr(rag_logic, 'embeddings', mock_embeddings_instance)
    
    mock_vector_store_instance = MagicMock()
    monkeypatch.setattr(rag_logic, 'vector_store', mock_vector_store_instance)

    # initialize_rag_componentsが何らかの理由でトリガーされた場合にファイルシステムアクセスを防ぐためPyPDFDirectoryLoaderをモック化
    mock_pdf_loader = MagicMock()
    mock_pdf_loader.load.return_value = [Document(page_content="dummy pdf content", metadata={"source": "dummy.pdf", "page": 0})]
    monkeypatch.setattr('backend.app.rag_logic.PyPDFDirectoryLoader', MagicMock(return_value=mock_pdf_loader))

    # ファイルシステムアクセスを防ぐためFAISSをモック化
    mock_faiss = MagicMock()
    mock_faiss.load_local.return_value = mock_vector_store_instance # 既存ストアの読み込みをシミュレート
    mock_faiss.from_documents.return_value = mock_vector_store_instance # 新規ストアの作成をシミュレート
    monkeypatch.setattr('backend.app.rag_logic.FAISS', mock_faiss)


def test_query_rag_success(monkeypatch):
    """
    RAGシステムへの問い合わせが成功する基本的なケースを検証します。
    モックされたリトリーバーとLLMが期待通りに動作し、
    正しい回答と情報源が返されることを確認します。
    """
    # この特定のテストのためにベクターストアのリトリーバーの振る舞いをモック化
    mock_retriever = MagicMock()
    mock_doc = Document(page_content="This is a test document about disasters.", metadata={"filename": "test.pdf", "page": 1})
    # get_relevant_documents はRAGチェーンが検索に使用するメソッド
    mock_retriever.get_relevant_documents.return_value = [mock_doc] 
    
    # autouseフィクスチャからのグローバルなvector_storeモックがこのリトリーバーを返すように設定
    rag_logic.vector_store.as_retriever.return_value = mock_retriever

    # この特定のテストのためにLLMの応答をモック化
    # llmモックはautouseフィクスチャから既に設定済み。invokeのみを設定する。
    rag_logic.llm.invoke.return_value = "Mocked LLM answer about disasters."
    
    question = "What about disasters?"
    result = rag_logic.query_rag(question)

    assert result['answer'] == "Mocked LLM answer about disasters."
    assert len(result['sources']) == 1
    assert result['sources'][0]['filename'] == "test.pdf"
    assert result['sources'][0]['page'] == 1 # rag_logicによってメタデータの'page'は1から始まるようにインデックス付けされる
    
    rag_logic.vector_store.as_retriever.assert_called_once()
    mock_retriever.get_relevant_documents.assert_called_with(question)
    # rag_logic.llm.invoke はチェーンによって呼び出されるべき。その呼び出しを検証するのはチェーン内部の複雑さのため困難。
    # このテストでは、モックされた入力に基づいて直接的な出力を確認することが主な目標。


def test_query_rag_not_initialized_vector_store_none(monkeypatch):
    """
    RAGシステムのベクターストア(vector_store)が初期化されていない(None)場合の
    エラーハンドリングを検証します。
    システムが適切にエラーメッセージを返し、空の情報源リストを返すことを期待します。
    """
    monkeypatch.setattr(rag_logic, 'vector_store', None) # vector_storeが準備できていない状態をシミュレート
    monkeypatch.setattr(rag_logic, 'is_initialized', True) # 他のコンポーネントは「準備完了」状態を維持

    question = "Test question when vector store is None"
    result = rag_logic.query_rag(question)

    # 現在の rag_logic.py に基づく:
    # if not vector_store: return {"answer": "Vector store not available...", "sources": []}
    assert "Vector store not available" in result['answer'] # エラーメッセージは日本語化されているはず
    assert len(result['sources']) == 0

def test_query_rag_not_initialized_llm_none(monkeypatch):
    """
    RAGシステムのLLM(llm)が初期化されていない(None)場合のエラーハンドリングを検証します。
    システムがLLMの不在を検知し、適切なエラーメッセージと空の情報源リストを
    返すことを期待します。
    """
    monkeypatch.setattr(rag_logic, 'llm', None) # LLMが準備できていない状態をシミュレート
    monkeypatch.setattr(rag_logic, 'is_initialized', True) # 他のコンポーネントは「準備完了」状態を維持

    question = "Test question when LLM is None"
    result = rag_logic.query_rag(question)
    
    # 現在の rag_logic.py に基づく:
    # if not llm: return {"answer": "LLM not available...", "sources": []}
    assert "LLM not available" in result['answer'] # エラーメッセージは日本語化されているはず
    assert len(result['sources']) == 0

def test_query_rag_not_initialized_is_initialized_false(monkeypatch):
    """
    RAGシステム全体の初期化フラグ(is_initialized)がFalseの場合の動作を検証します。
    これは、初期化プロセスが完了していないか失敗した状況をシミュレートします。
    システムが初期化未完了を示すエラーメッセージを返すことを期待します。
    """
    monkeypatch.setattr(rag_logic, 'is_initialized', False)

    question = "Test question when RAG is not initialized"
    result = rag_logic.query_rag(question)

    # 現在の rag_logic.py に基づく:
    # if not is_initialized: return {"answer": "RAG system is not initialized...", "sources": []}
    assert "RAG system is not initialized" in result['answer'] # エラーメッセージは日本語化されているはず
    assert len(result['sources']) == 0


def test_query_rag_no_documents_found(monkeypatch):
    """
    リトリーバーが質問に関連するドキュメントを見つけられなかった場合の
    RAGシステムの動作を検証します。
    LLMはコンテキストなしで応答を生成するよう指示されており、
    その結果として情報不足を示すメッセージが返され、情報源リストが
    空であることを期待します。
    """
    mock_retriever = MagicMock()
    mock_retriever.get_relevant_documents.return_value = [] # ドキュメントが見つからない
    rag_logic.vector_store.as_retriever.return_value = mock_retriever

    # LLMは空のコンテキストで呼び出される。
    # プロンプトテンプレートには「コンテキストが空か「関連する情報が見つかりませんでした」と表示されている場合は、ドキュメントから十分な情報が得られなかったと述べてください。」とある。
    # そのため、LLMの応答はプロンプトに基づいてこれを反映するべき。
    expected_llm_response_for_no_context = "Based on the provided documents, I don't have enough information to answer that." # この部分はrag_logic.pyのプロンプトに依存
    rag_logic.llm.invoke.return_value = expected_llm_response_for_no_context

    question = "Unknown topic"
    result = rag_logic.query_rag(question)
    
    assert result['answer'] == expected_llm_response_for_no_context
    assert len(result['sources']) == 0 # ドキュメントが取得されなかったため、ソースはなし
    mock_retriever.get_relevant_documents.assert_called_with(question)


def test_query_rag_llm_api_key_error(monkeypatch):
    """
    LLMとの対話中にAPIキー関連のエラーが発生した場合のRAGシステムの挙動を検証します。
    `rag_logic.py` がAPIキーエラーを検出し、ユーザーフレンドリーなエラーメッセージ
    ("AIサービスに接続できませんでした。...") を返すことを期待します。
    """
    # LLMとのやり取り中にAPIキーエラーをシミュレート。
    # rag_logic.py は chain.invoke 周りの一般的な例外をキャッチし、APIキーメッセージを具体的にチェックする。
    
    # APIキーエラーチェックに一致する例外を発生させるようにグローバルllmモックを設定
    # rag_logic.py でチェックされる特定のエラーメッセージは "API key not valid" または "PERMISSION_DENIED"
    error_message = "API key not valid. Please pass a valid API key."
    rag_logic.llm.invoke.side_effect = Exception(error_message)

    # LLMより前に呼び出されるようにリトリーバーを設定する必要がある
    mock_retriever = MagicMock()
    mock_doc = Document(page_content="Test content", metadata={"filename": "test.pdf", "page": 1})
    mock_retriever.get_relevant_documents.return_value = [mock_doc]
    rag_logic.vector_store.as_retriever.return_value = mock_retriever
    
    question = "A question that would trigger LLM"
    result = rag_logic.query_rag(question)

    # rag_logic.py のAPIキー問題のエラーハンドリングに基づく:
    assert "Could not connect to the AI service. Please check the GOOGLE_API_KEY." in result['answer'] # エラーメッセージは日本語化されているはず
    assert len(result['sources']) == 0 # エラー時はソースは空のはず

def test_query_rag_general_llm_error(monkeypatch):
    """
    LLMとの対話中にAPIキーエラー以外の一般的なエラーが発生した場合の
    RAGシステムの挙動を検証します。
    システムが一般的なエラーメッセージ ("回答の生成中にエラーが発生しました。") を
    返すことを期待します。
    """
    # LLMとのやり取り中に一般的なエラーをシミュレート。
    generic_error_message = "Some unexpected LLM error"
    rag_logic.llm.invoke.side_effect = Exception(generic_error_message)

    # リトリーバー設定
    mock_retriever = MagicMock()
    mock_doc = Document(page_content="Test content", metadata={"filename": "test.pdf", "page": 1})
    mock_retriever.get_relevant_documents.return_value = [mock_doc]
    rag_logic.vector_store.as_retriever.return_value = mock_retriever
    
    question = "Another question"
    result = rag_logic.query_rag(question)

    # rag_logic.py の一般的なエラーハンドリングに基づく:
    assert "An error occurred while generating the answer." in result['answer'] # エラーメッセージは日本語化されているはず
    assert len(result['sources']) == 0


def test_format_docs_for_prompt_with_docs():
    """
    `format_docs_for_prompt` 関数が、複数のドキュメントオブジェクトを
    正しくフォーマットされた単一の文字列に変換できることを検証します。
    各ドキュメントの内容とメタデータ（ファイル名、ページ番号）が
    期待通りに文字列に含まれることを確認します。
    """
    docs = [
        Document(page_content="Content page 1", metadata={"filename": "doc1.pdf", "page": 1}),
        Document(page_content="Content page 2", metadata={"filename": "doc2.pdf", "page": 5}),
    ]
    formatted_string = rag_logic.format_docs_for_prompt(docs)
    assert "Source: doc1.pdf, Page: 1\nContent: Content page 1" in formatted_string
    assert "Source: doc2.pdf, Page: 5\nContent: Content page 2" in formatted_string

def test_format_docs_for_prompt_no_docs():
    """
    `format_docs_for_prompt` 関数に空のドキュメントリストが渡された場合の
    動作を検証します。
    関数が「関連する情報が見つかりませんでした。」という固定の日本語メッセージを
    返すことを期待します。
    """
    formatted_string = rag_logic.format_docs_for_prompt([])
    assert formatted_string == "No relevant context found in the documents." # このメッセージはrag_logic.pyで日本語化されているはず

def test_format_docs_for_prompt_dummy_doc():
    """
    `format_docs_for_prompt` 関数にダミードキュメントのみが含まれるリストが
    渡された場合の動作を検証します。
    これは、RAG初期化時に実際のドキュメントが見つからなかったシナリオを想定しています。
    関数が「関連する情報が見つかりませんでした。」というメッセージを返すことを期待します。
    """
    # rag_logic.py によれば、初期化時に実際のドキュメントが見つからない場合、ダミードキュメントが使用されることがある
    docs = [Document(page_content="dummy", metadata={"filename":"dummy.txt", "page":0})]
    formatted_string = rag_logic.format_docs_for_prompt(docs)
    assert formatted_string == "No relevant context found in the documents." # このメッセージはrag_logic.pyで日本語化されているはず

# 注意: initialize_rag_components 関数自体をテストするのはより複雑になる。
# ファイルシステム操作 (PyPDFDirectoryLoader, FAISS save/load) を伴うため。
# 現在のフィクスチャ戦略は、initialize_rag_components が作成するコンポーネントを
# モック化することで query_rag をテスト可能にすることに焦点を当てている。
# これは、複雑な初期化ルーチンに依存する関数をテストするための一般的なアプローチ。
