import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFDirectoryLoader # Loads all PDFs in a dir
# from langchain.text_splitter import RecursiveCharacterTextSplitter # Or another that respects page boundaries - Not used for now as PyPDFDirectoryLoader handles page-wise loading
from langchain_community.vectorstores import FAISS
# from langchain.chains import RetrievalQA # Replaced by manual chain construction
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough, RunnableParallel
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.document import Document # Added for type hinting and clarity

# 環境変数 (GOOGLE_API_KEY用) の読み込み
# このスクリプトの場所からの相対パスで .env ファイルへのパスを構築
# __file__ は .../backend/app/rag_logic.py
# .env は .../backend/.env
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path=dotenv_path)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# このファイルの場所からの相対パスを構築
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

DOCUMENTS_PATH = os.path.join(ROOT_DIR, 'documents')
VECTORSTORE_PATH = os.path.join(BACKEND_DIR, 'vectorstore_faiss')


llm = None
embeddings = None
vector_store = None
is_initialized = False # 初期化済みフラグ

def initialize_rag_components():
    global llm, embeddings, vector_store, is_initialized
    
    if is_initialized:
        print("RAGコンポーネントは既に初期化されています。")
        return

    print("RAGコンポーネントを初期化しています...")
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY_HERE":
        print("警告: GOOGLE_API_KEYが見つからないか、プレースホルダーのままです。RAGシステムは正常に機能しません。")
        # アプリの起動を許可するために続行するが、クエリは失敗する
        # または ValueError("GOOGLE_API_KEYが環境変数に見つからないか、プレースホルダーのままです。") を発生させる
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=GOOGLE_API_KEY, temperature=0.7)
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"Google AIコンポーネントの初期化中にエラー: {e}")
        print("GOOGLE_API_KEYが有効で、Gemini APIが有効になっていることを確認してください。")
        # アプリの他の部分が動作する可能性を残すためにここではエラーを発生させない
        # ただし、RAGクエリは失敗する
        is_initialized = False # 正常に初期化されなかったことを示す
        return


    if os.path.exists(VECTORSTORE_PATH):
        print(f"既存のベクターストアを {VECTORSTORE_PATH} から読み込んでいます。")
        try:
            vector_store = FAISS.load_local(VECTORSTORE_PATH, embeddings, allow_dangerous_deserialization=True)
            print("ベクターストアの読み込みに成功しました。")
        except Exception as e:
            print(f"ベクターストアの読み込みエラー: {e}。再作成します...")
            os.rmdir(VECTORSTORE_PATH) # 破損している可能性のあるストアを削除
            vector_store = None # リセットを確実にする
            # 新規作成に進む
    
    if not vector_store: # 読み込まれなかった場合、または読み込みに失敗した場合
        print(f"新しいベクターストアを作成しています。ドキュメントを {DOCUMENTS_PATH} から読み込んでいます。")
        if not os.path.exists(DOCUMENTS_PATH):
            os.makedirs(DOCUMENTS_PATH) # ドキュメントディレクトリが存在しない場合は作成
            print(f"{DOCUMENTS_PATH} にドキュメントディレクトリを作成しました。")
            
        if not os.listdir(DOCUMENTS_PATH):
            print(f"{DOCUMENTS_PATH} にドキュメントが見つかりません。RAGはPDFからの知識ベースを持ちません。")
            docs = []
        else:
            print(f"{DOCUMENTS_PATH} からPDFを読み込んでいます...")
            loader = PyPDFDirectoryLoader(DOCUMENTS_PATH)
            try:
                loaded_pages = loader.load() # loaded_pages の各アイテムはページを表す Document
            except Exception as e:
                print(f"PDFの読み込みエラー: {e}")
                loaded_pages = []
            
            docs = []
            for page_doc in loaded_pages:
                # PyPDFDirectoryLoader は 'source' (フルパス) と 'page' (0から始まる) を追加する
                filename = os.path.basename(page_doc.metadata.get('source', 'Unknown Document'))
                page_number = page_doc.metadata.get('page', 0) + 1 # 1から始まるように変換
                
                page_doc.metadata['filename'] = filename
                page_doc.metadata['page'] = page_number
                docs.append(page_doc)
        
        print(f"PDFドキュメントから {len(docs)} ページを読み込みました。")
        if docs:
            try:
                vector_store = FAISS.from_documents(docs, embeddings)
                vector_store.save_local(VECTORSTORE_PATH)
                print(f"ベクターストアを作成し、{VECTORSTORE_PATH} に保存しました。")
            except Exception as e:
                print(f"FAISSベクターストアの作成または保存エラー: {e}")
                vector_store = None # 作成失敗時は vector_store を None にする
        else:
            # ドキュメントがない場合、as_retriever() でのエラーを避けるために空のベクターストアが必要
            # ダミードキュメントでFAISSインデックスを作成し、クリアするか、クエリ時に処理する
            # 現在は、可能であれば空のものを作成するか、None のままにする
            # FAISS.from_documents は少なくとも1つのドキュメントを必要とする
            # より堅牢な解決策は、フラグを持つか、ドキュメントがない場合に特定のメッセージを返すこと
            print("ドキュメントが読み込まれなかったため、ベクターストアは空か作成されていません。")
            # 後で vector_store.as_retriever() を許可するために、ダミーエントリで初期化する必要があるかもしれない
            # ただし、埋め込みが利用できない場合 (APIキーの問題など)、これも失敗する
            if embeddings:
                try:
                    dummy_doc = [Document(page_content="dummy", metadata={"filename":"dummy.txt", "page":0})]
                    vector_store = FAISS.from_documents(dummy_doc, embeddings)
                    # このダミーストアは理想的には保存しないか、クリアするべき
                    # この実装では、query_rag が 'dummy' をチェックして処理する
                    print("ドキュメントが見つからなかったため、ダミーのベクターストアを作成しました。")
                except Exception as e:
                    print(f"ダミーベクターストアを作成できませんでした: {e}")
                    vector_store = None # 明示的に None に設定
            else:
                vector_store = None


    is_initialized = True
    print("RAGコンポーネントの初期化が完了しました。")


# モジュール読み込み時に一度初期化を呼び出す
# 初期化中のエラーは表示されるが、アプリの起動は停止しない
# クエリ関数はコンポーネントが準備できているか確認すべき
initialize_rag_components()

def format_docs_for_prompt(docs: list[Document]) -> str:
    if not docs or (len(docs) == 1 and docs[0].metadata.get('filename') == 'dummy.txt'):
        return "ドキュメント内に関連する情報が見つかりませんでした。"
    return "\n\n".join(f"Source: {doc.metadata.get('filename', 'N/A')}, Page: {doc.metadata.get('page', 'N/A')}\nContent: {doc.page_content}" for doc in docs)

def query_rag(question: str) -> dict:
    global llm, vector_store, is_initialized

    if not is_initialized:
        return {"answer": "RAGシステムが初期化されていません。サーバーログを確認してください。", "sources": []}
    if not llm:
        return {"answer": "LLMが利用できません。APIキーとサーバーログを確認してください。", "sources": []}
    if not vector_store:
        return {"answer": "ベクターストアが利用できません。ドキュメントが読み込まれていないか、初期化中にエラーが発生しました。", "sources": []}

    try:
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    except Exception as e:
        # vector_store が FAISS だが、as_retriever が失敗する方法で空の場合に発生する可能性がある
        print(f"リトリーバーの作成エラー: {e}")
        return {"answer": "ドキュメントリトリーバーを作成できませんでした。ベクターストアが空か破損している可能性があります。", "sources": []}

    template = """以下のコンテキストのみに基づいて質問に答えてください:
    {context}

    コンテキストが空か「関連する情報が見つかりませんでした」と表示されている場合は、ドキュメントから十分な情報が得られなかったと述べてください。
    外部の知識は使用しないでください。

    質問: {question}

    回答:
    """
    prompt = PromptTemplate.from_template(template)

    rag_chain = (
        RunnableParallel(
            context=(retriever | format_docs_for_prompt),
            question=RunnablePassthrough()
        )
        | prompt
        | llm
        | StrOutputParser()
    )

    try:
        answer = rag_chain.invoke(question)
    except Exception as e:
        print(f"RAGチェーンの実行中にエラー: {e}")
        # Gemini の API キーの問題かどうかを確認
        if "API key not valid" in str(e) or "PERMISSION_DENIED" in str(e):
             return {"answer": "AIサービスに接続できませんでした。GOOGLE_API_KEYを確認してください。", "sources": []}
        return {"answer": "回答の生成中にエラーが発生しました。", "sources": []}
    
    # 情報源の正しいメタデータを確保するためにドキュメントを再度取得
    try:
        retrieved_docs = retriever.get_relevant_documents(question)
        # ダミードキュメントが使用された場合は除外
        actual_retrieved_docs = [doc for doc in retrieved_docs if doc.metadata.get('filename') != 'dummy.txt']
    except Exception as e:
        print(f"情報源のドキュメント取得エラー: {e}")
        actual_retrieved_docs = []

    sources = []
    if actual_retrieved_docs:
        for doc in actual_retrieved_docs:
            sources.append({
                "filename": doc.metadata.get('filename', os.path.basename(doc.metadata.get('source', 'Unknown'))),
                "page": doc.metadata.get('page', 'N/A')
            })
            
    return {"answer": answer, "sources": sources}

# 使用例 (テスト用)
if __name__ == '__main__':
    print("RAGロジックのテスト中...")
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY_HERE":
        print("テストをスキップ: GOOGLE_API_KEY が設定されていないか、プレースホルダーです。")
    elif not is_initialized or not llm or not vector_store:
        print("テストをスキップ: RAGコンポーネントが完全に初期化されていません。")
    else:
        # テスト用に存在しない場合はダミーPDFを作成
        if not os.listdir(DOCUMENTS_PATH):
            print(f"{DOCUMENTS_PATH} にドキュメントがありません。テストPDFの追加を検討してください。")
            # test_pdf_path = os.path.join(DOCUMENTS_PATH, "test_doc.pdf")
            # with open(test_pdf_path, "w") as f: # これは有効なPDFにはなりません
            #     f.write("これは地震時の安全に関するテストドキュメントです。")
            # print(f"テスト用に test_doc.pdf という名前のダミーテキストファイルを作成しました。PyPDFLoader はこれを解析できないかもしれません。")
            # print("ファイルを手動で追加した場合は、initialize_rag_components() を再実行するか、スクリプトを再起動してください。")
        
        # テスト用に手動でファイルを追加した場合に新しいファイルを取得するために再初期化
        # initialize_rag_components() # モジュールのロードで既に実行されている場合は冗長かもしれない

        test_question = "地震の時はどうすればいいですか？"
        print(f"\n問い合わせ内容: '{test_question}'")
        response = query_rag(test_question)
        print("\n応答:")
        print(f"  回答: {response['answer']}")
        print(f"  情報源: {response['sources']}")

        test_question_no_context = "フランスの首都は？"
        print(f"\n問い合わせ内容: '{test_question_no_context}' (関連コンテキストなしを想定)")
        response_no_context = query_rag(test_question_no_context)
        print("\n応答 (コンテキストなし):")
        print(f"  回答: {response_no_context['answer']}")
        print(f"  情報源: {response_no_context['sources']}")
