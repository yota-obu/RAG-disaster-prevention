import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document

# Module to be tested
from backend.app import rag_logic 

@pytest.fixture(autouse=True)
def mock_rag_components(monkeypatch):
    """
    Automatically mocks components critical to RAG logic for all tests in this module.
    This prevents actual initialization (API calls, file system access) and provides
    controllable mocks for llm, embeddings, and vector_store.
    """
    # Mock environment variables if rag_logic tries to load them directly at import time
    monkeypatch.setenv("GOOGLE_API_KEY", "fake_api_key_for_testing")
    
    # Prevent actual initialization by initialize_rag_components if it runs on import or is called
    # We also mock the global variables that initialize_rag_components would set.
    monkeypatch.setattr(rag_logic, 'is_initialized', True) # Assume it's initialized for most tests
    
    # Mock the LLM, Embeddings, and VectorStore instances
    mock_llm_instance = MagicMock()
    monkeypatch.setattr(rag_logic, 'llm', mock_llm_instance)
    
    mock_embeddings_instance = MagicMock()
    monkeypatch.setattr(rag_logic, 'embeddings', mock_embeddings_instance)
    
    mock_vector_store_instance = MagicMock()
    monkeypatch.setattr(rag_logic, 'vector_store', mock_vector_store_instance)

    # Mock the PyPDFDirectoryLoader to prevent file system access if initialize_rag_components was somehow triggered
    mock_pdf_loader = MagicMock()
    mock_pdf_loader.load.return_value = [Document(page_content="dummy pdf content", metadata={"source": "dummy.pdf", "page": 0})]
    monkeypatch.setattr('backend.app.rag_logic.PyPDFDirectoryLoader', MagicMock(return_value=mock_pdf_loader))

    # Mock FAISS to prevent file system access
    mock_faiss = MagicMock()
    mock_faiss.load_local.return_value = mock_vector_store_instance # Simulate loading existing store
    mock_faiss.from_documents.return_value = mock_vector_store_instance # Simulate creating new store
    monkeypatch.setattr('backend.app.rag_logic.FAISS', mock_faiss)


def test_query_rag_success(monkeypatch):
    # Mock the vector store's retriever behavior for this specific test
    mock_retriever = MagicMock()
    mock_doc = Document(page_content="This is a test document about disasters.", metadata={"filename": "test.pdf", "page": 1})
    # get_relevant_documents is the method used by the RAG chain for retrieval
    mock_retriever.get_relevant_documents.return_value = [mock_doc] 
    
    # Ensure our global vector_store mock (from autouse fixture) returns this retriever
    rag_logic.vector_store.as_retriever.return_value = mock_retriever

    # Mock the LLM's response for this specific test
    # The llm mock is already in place from the autouse fixture. We just configure its invoke.
    rag_logic.llm.invoke.return_value = "Mocked LLM answer about disasters."
    
    question = "What about disasters?"
    result = rag_logic.query_rag(question)

    assert result['answer'] == "Mocked LLM answer about disasters."
    assert len(result['sources']) == 1
    assert result['sources'][0]['filename'] == "test.pdf"
    assert result['sources'][0]['page'] == 1 # Metadata 'page' is 1-indexed by rag_logic
    
    rag_logic.vector_store.as_retriever.assert_called_once()
    mock_retriever.get_relevant_documents.assert_called_with(question)
    # rag_logic.llm.invoke should be called by the chain; verifying its call can be complex due to chain internals.
    # For this test, checking the direct output based on mocked inputs is the primary goal.


def test_query_rag_not_initialized_vector_store_none(monkeypatch):
    monkeypatch.setattr(rag_logic, 'vector_store', None) # Simulate vector_store not being ready
    monkeypatch.setattr(rag_logic, 'is_initialized', True) # Keep other components "ready"

    question = "Test question when vector store is None"
    result = rag_logic.query_rag(question)

    # Based on current rag_logic.py:
    # if not vector_store: return {"answer": "Vector store not available...", "sources": []}
    assert "Vector store not available" in result['answer']
    assert len(result['sources']) == 0

def test_query_rag_not_initialized_llm_none(monkeypatch):
    monkeypatch.setattr(rag_logic, 'llm', None) # Simulate LLM not being ready
    monkeypatch.setattr(rag_logic, 'is_initialized', True) # Keep other components "ready"

    question = "Test question when LLM is None"
    result = rag_logic.query_rag(question)
    
    # Based on current rag_logic.py:
    # if not llm: return {"answer": "LLM not available...", "sources": []}
    assert "LLM not available" in result['answer']
    assert len(result['sources']) == 0

def test_query_rag_not_initialized_is_initialized_false(monkeypatch):
    monkeypatch.setattr(rag_logic, 'is_initialized', False)

    question = "Test question when RAG is not initialized"
    result = rag_logic.query_rag(question)

    # Based on current rag_logic.py:
    # if not is_initialized: return {"answer": "RAG system is not initialized...", "sources": []}
    assert "RAG system is not initialized" in result['answer']
    assert len(result['sources']) == 0


def test_query_rag_no_documents_found(monkeypatch):
    mock_retriever = MagicMock()
    mock_retriever.get_relevant_documents.return_value = [] # No docs found
    rag_logic.vector_store.as_retriever.return_value = mock_retriever

    # LLM will be called with an empty context.
    # The prompt template includes: "If the context is empty or says 'No relevant context found', state that you don't have enough information from the documents."
    # So the LLM's response should reflect this based on the prompt.
    expected_llm_response_for_no_context = "Based on the provided documents, I don't have enough information to answer that."
    rag_logic.llm.invoke.return_value = expected_llm_response_for_no_context

    question = "Unknown topic"
    result = rag_logic.query_rag(question)
    
    assert result['answer'] == expected_llm_response_for_no_context
    assert len(result['sources']) == 0 # No documents retrieved means no sources
    mock_retriever.get_relevant_documents.assert_called_with(question)


def test_query_rag_llm_api_key_error(monkeypatch):
    # Simulate an API key error during LLM interaction.
    # rag_logic.py catches general exceptions around chain.invoke and has a specific check for API key messages.
    
    # Configure the global llm mock to raise an exception that matches the API key error check
    # The specific error message checked in rag_logic.py is "API key not valid" or "PERMISSION_DENIED"
    error_message = "API key not valid. Please pass a valid API key."
    rag_logic.llm.invoke.side_effect = Exception(error_message)

    # Retriever needs to be set up to be called before the LLM
    mock_retriever = MagicMock()
    mock_doc = Document(page_content="Test content", metadata={"filename": "test.pdf", "page": 1})
    mock_retriever.get_relevant_documents.return_value = [mock_doc]
    rag_logic.vector_store.as_retriever.return_value = mock_retriever
    
    question = "A question that would trigger LLM"
    result = rag_logic.query_rag(question)

    # Based on rag_logic.py's error handling for API key issues:
    assert "Could not connect to the AI service. Please check the GOOGLE_API_KEY." in result['answer']
    assert len(result['sources']) == 0 # Sources should be empty on error

def test_query_rag_general_llm_error(monkeypatch):
    # Simulate a generic error during LLM interaction.
    generic_error_message = "Some unexpected LLM error"
    rag_logic.llm.invoke.side_effect = Exception(generic_error_message)

    # Retriever setup
    mock_retriever = MagicMock()
    mock_doc = Document(page_content="Test content", metadata={"filename": "test.pdf", "page": 1})
    mock_retriever.get_relevant_documents.return_value = [mock_doc]
    rag_logic.vector_store.as_retriever.return_value = mock_retriever
    
    question = "Another question"
    result = rag_logic.query_rag(question)

    # Based on rag_logic.py's generic error handling:
    assert "An error occurred while generating the answer." in result['answer']
    assert len(result['sources']) == 0


def test_format_docs_for_prompt_with_docs():
    docs = [
        Document(page_content="Content page 1", metadata={"filename": "doc1.pdf", "page": 1}),
        Document(page_content="Content page 2", metadata={"filename": "doc2.pdf", "page": 5}),
    ]
    formatted_string = rag_logic.format_docs_for_prompt(docs)
    assert "Source: doc1.pdf, Page: 1\nContent: Content page 1" in formatted_string
    assert "Source: doc2.pdf, Page: 5\nContent: Content page 2" in formatted_string

def test_format_docs_for_prompt_no_docs():
    formatted_string = rag_logic.format_docs_for_prompt([])
    assert formatted_string == "No relevant context found in the documents."

def test_format_docs_for_prompt_dummy_doc():
    # As per rag_logic.py, a dummy doc might be used if no real docs found during init
    docs = [Document(page_content="dummy", metadata={"filename":"dummy.txt", "page":0})]
    formatted_string = rag_logic.format_docs_for_prompt(docs)
    assert formatted_string == "No relevant context found in the documents."

# Note: To test the initialize_rag_components function itself would be more complex,
# as it involves file system operations (PyPDFDirectoryLoader, FAISS save/load).
# The current fixture strategy focuses on making query_rag testable by mocking
# the components that initialize_rag_components would create.
# This is a common approach for testing functions that depend on a complex initialization routine.
