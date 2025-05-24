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

# Load environment variables (for GOOGLE_API_KEY)
# Construct the path to the .env file relative to this script's location
# __file__ is .../backend/app/rag_logic.py
# .env is in .../backend/.env
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path=dotenv_path)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Construct paths relative to this file's location
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

DOCUMENTS_PATH = os.path.join(ROOT_DIR, 'documents')
VECTORSTORE_PATH = os.path.join(BACKEND_DIR, 'vectorstore_faiss')


llm = None
embeddings = None
vector_store = None
is_initialized = False

def initialize_rag_components():
    global llm, embeddings, vector_store, is_initialized
    
    if is_initialized:
        print("RAG components already initialized.")
        return

    print("Initializing RAG components...")
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY_HERE":
        print("WARNING: GOOGLE_API_KEY not found or is a placeholder. RAG system will not function correctly.")
        # We can let it proceed to allow app to start, but queries will fail.
        # Or raise ValueError("GOOGLE_API_KEY not found or is a placeholder in environment variables.")
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=GOOGLE_API_KEY, temperature=0.7)
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"Error initializing Google AI components: {e}")
        print("Please ensure your GOOGLE_API_KEY is valid and has the Gemini API enabled.")
        # Not raising an error here to allow the rest of the app to potentially work,
        # but RAG queries will fail.
        is_initialized = False # Mark as not successfully initialized
        return


    if os.path.exists(VECTORSTORE_PATH):
        print(f"Loading existing vector store from {VECTORSTORE_PATH}")
        try:
            vector_store = FAISS.load_local(VECTORSTORE_PATH, embeddings, allow_dangerous_deserialization=True)
            print("Vector store loaded successfully.")
        except Exception as e:
            print(f"Error loading vector store: {e}. Re-creating...")
            os.rmdir(VECTORSTORE_PATH) # Remove potentially corrupted store
            vector_store = None # Ensure it's reset
            # Proceed to create new one
    
    if not vector_store: # If not loaded or loading failed
        print(f"Creating new vector store. Loading documents from: {DOCUMENTS_PATH}")
        if not os.path.exists(DOCUMENTS_PATH):
            os.makedirs(DOCUMENTS_PATH) # Create documents directory if it doesn't exist
            print(f"Created documents directory at {DOCUMENTS_PATH}")
            
        if not os.listdir(DOCUMENTS_PATH):
            print(f"No documents found in {DOCUMENTS_PATH}. RAG will have no knowledge from PDFs.")
            docs = []
        else:
            print(f"Loading PDFs from {DOCUMENTS_PATH}...")
            loader = PyPDFDirectoryLoader(DOCUMENTS_PATH)
            try:
                loaded_pages = loader.load() # Each item in loaded_pages is a Document representing a page
            except Exception as e:
                print(f"Error loading PDFs: {e}")
                loaded_pages = []
            
            docs = []
            for page_doc in loaded_pages:
                # PyPDFDirectoryLoader adds 'source' (full path) and 'page' (0-indexed)
                filename = os.path.basename(page_doc.metadata.get('source', 'Unknown Document'))
                page_number = page_doc.metadata.get('page', 0) + 1 # Convert to 1-indexed
                
                page_doc.metadata['filename'] = filename
                page_doc.metadata['page'] = page_number
                docs.append(page_doc)
        
        print(f"Loaded {len(docs)} pages from PDF documents.")
        if docs:
            try:
                vector_store = FAISS.from_documents(docs, embeddings)
                vector_store.save_local(VECTORSTORE_PATH)
                print(f"Vector store created and saved to {VECTORSTORE_PATH}")
            except Exception as e:
                print(f"Error creating or saving FAISS vector store: {e}")
                vector_store = None # Ensure vector_store is None if creation fails
        else:
            # If no documents, we need an empty vector store to avoid errors in as_retriever()
            # Create a FAISS index with a dummy document and then clear it, or handle query time.
            # For now, let's create an empty one if possible, or it remains None.
            # FAISS.from_documents requires at least one document.
            # A more robust solution might be to have a flag or return specific message if no docs.
            print("No documents loaded, vector store is empty or not created.")
            # To allow vector_store.as_retriever() later, we might need to initialize it with a dummy entry.
            # However, if embeddings are not available (e.g. API key issue), this will also fail.
            if embeddings:
                try:
                    dummy_doc = [Document(page_content="dummy", metadata={"filename":"dummy.txt", "page":0})]
                    vector_store = FAISS.from_documents(dummy_doc, embeddings)
                    # This dummy store should ideally not be saved or be cleared.
                    # For this implementation, query_rag will check for 'dummy' and handle it.
                    print("Created a dummy vector store as no documents were found.")
                except Exception as e:
                    print(f"Could not create dummy vector store: {e}")
                    vector_store = None # Explicitly set to None
            else:
                vector_store = None


    is_initialized = True
    print("RAG components initialization finished.")


# Call initialization once when the module is loaded.
# Errors during initialization are printed but don't stop the app from starting.
# Query functions should check if components are ready.
initialize_rag_components()

def format_docs_for_prompt(docs: list[Document]) -> str:
    if not docs or (len(docs) == 1 and docs[0].metadata.get('filename') == 'dummy.txt'):
        return "No relevant context found in the documents."
    return "\n\n".join(f"Source: {doc.metadata.get('filename', 'N/A')}, Page: {doc.metadata.get('page', 'N/A')}\nContent: {doc.page_content}" for doc in docs)

def query_rag(question: str) -> dict:
    global llm, vector_store, is_initialized

    if not is_initialized:
        return {"answer": "RAG system is not initialized. Please check server logs.", "sources": []}
    if not llm:
        return {"answer": "LLM not available. Please check API key and server logs.", "sources": []}
    if not vector_store:
        return {"answer": "Vector store not available. No documents loaded or error during initialization.", "sources": []}

    try:
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    except Exception as e:
        # This can happen if vector_store is FAISS but empty in a way that as_retriever fails.
        print(f"Error creating retriever: {e}")
        return {"answer": "Could not create document retriever. Vector store might be empty or corrupted.", "sources": []}

    template = """Answer the question based only on the following context:
    {context}

    If the context is empty or says 'No relevant context found', state that you don't have enough information from the documents.
    Do not use any external knowledge.

    Question: {question}

    Answer:
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
        print(f"Error during RAG chain invocation: {e}")
        # Check if it's an API key issue with Gemini
        if "API key not valid" in str(e) or "PERMISSION_DENIED" in str(e):
             return {"answer": "Could not connect to the AI service. Please check the GOOGLE_API_KEY.", "sources": []}
        return {"answer": "An error occurred while generating the answer.", "sources": []}
    
    # Retrieve documents again to ensure we have the correct metadata for sources
    try:
        retrieved_docs = retriever.get_relevant_documents(question)
        # Filter out the dummy document if it was used
        actual_retrieved_docs = [doc for doc in retrieved_docs if doc.metadata.get('filename') != 'dummy.txt']
    except Exception as e:
        print(f"Error retrieving documents for sources: {e}")
        actual_retrieved_docs = []

    sources = []
    if actual_retrieved_docs:
        for doc in actual_retrieved_docs:
            sources.append({
                "filename": doc.metadata.get('filename', os.path.basename(doc.metadata.get('source', 'Unknown'))),
                "page": doc.metadata.get('page', 'N/A')
            })
            
    return {"answer": answer, "sources": sources}

# Example usage (for testing)
if __name__ == '__main__':
    print("Testing RAG logic...")
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY_HERE":
        print("Skipping test: GOOGLE_API_KEY is not set or is a placeholder.")
    elif not is_initialized or not llm or not vector_store:
        print("Skipping test: RAG components not fully initialized.")
    else:
        # Create a dummy PDF if none exists for testing
        if not os.listdir(DOCUMENTS_PATH):
            print(f"No documents in {DOCUMENTS_PATH}. Consider adding a test PDF.")
            # test_pdf_path = os.path.join(DOCUMENTS_PATH, "test_doc.pdf")
            # with open(test_pdf_path, "w") as f: # This will not be a valid PDF
            #     f.write("This is a test document about safety during earthquakes.")
            # print(f"Created a dummy text file named test_doc.pdf for testing. PyPDFLoader might not parse it.")
            # print("Please re-run initialize_rag_components() or restart the script if you added files manually.")
        
        # Re-initialize to pick up any new files if added manually for testing
        # initialize_rag_components() # This might be redundant if module load already did it.

        test_question = "What should I do during an earthquake?"
        print(f"\nQuerying with: '{test_question}'")
        response = query_rag(test_question)
        print("\nResponse:")
        print(f"  Answer: {response['answer']}")
        print(f"  Sources: {response['sources']}")

        test_question_no_context = "What is the capital of France?"
        print(f"\nQuerying with: '{test_question_no_context}' (expected no relevant context)")
        response_no_context = query_rag(test_question_no_context)
        print("\nResponse (no context):")
        print(f"  Answer: {response_no_context['answer']}")
        print(f"  Sources: {response_no_context['sources']}")
