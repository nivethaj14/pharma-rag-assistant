import os
import json
from dotenv import load_dotenv
import snowflake.connector
from cryptography.hazmat.primitives import serialization

from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

def get_snowflake_connection():
    """Create Snowflake connection using key pair auth."""
    with open(os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"), "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None
        )
    
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        private_key=private_key_bytes,
        role=os.getenv("SNOWFLAKE_ROLE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA")
    )
    return conn


def retrieve_chunks(query: str, limit: int = 8) -> list:
    """Retrieve relevant chunks from Cortex Search."""
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    search_query = json.dumps({
        "query": query,
        "columns": [
            "chunk_id",
            "file_name",
            "section_heading",
            "chunk_text",
            "document_type"
        ],
        "limit": limit
    })

    cursor.execute("""
        SELECT PARSE_JSON(
            SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                'pharma_rag_db.marts.pharma_search_service',
                %s
            )
        ) AS search_results
    """, (search_query,))

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row and row[0]:
        data = row[0]
        if isinstance(data, str):
            data = json.loads(data)
        results = data.get("results", [])
        seen = set()
        unique_results = []
        for r in results:
            if r.get("chunk_id") not in seen:
                seen.add(r.get("chunk_id"))
                unique_results.append(r)
        return unique_results
    return []


def build_prompt(query: str, chunks: list) -> str:
    """Build a grounded prompt with retrieved context and citation instructions."""
    context_parts = []
    
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[SOURCE {i}]\n"
            f"Document: {chunk.get('file_name', 'Unknown')}\n"
            f"Section: {chunk.get('section_heading', 'Unknown')}\n"
            f"Content: {chunk.get('chunk_text', '')}\n"
        )
    
    context = "\n---\n".join(context_parts)
    
    prompt = f"""You are a regulatory affairs expert assistant specializing in FDA oncology 
guidance documents and clinical trial protocols. Answer the user's question using ONLY 
the provided source documents below. If a source contains partial information, 
extract and cite every relevant detail you can find, even if incomplete. 

Rules:
- Always cite the source document and section for every claim you make
- Use the format [SOURCE X] when citing
- If the answer is not in the provided sources, say "I cannot find this information 
  in the available documents"
- Be precise and use regulatory terminology appropriately
- Do not make up or infer information not explicitly stated in the sources

SOURCE DOCUMENTS:
{context}

USER QUESTION:
{query}

ANSWER (with citations):"""
    
    return prompt


def generate_answer(prompt: str) -> str:
    """Generate answer using Snowflake Cortex LLM."""
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large2',
            %s
        ) AS answer
    """, (prompt,))
    
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if row and row[0]:
        return row[0]
    return "Unable to generate answer."


def rag_query(question: str) -> dict:
    """
    Full RAG pipeline:
    1. Retrieve relevant chunks
    2. Build grounded prompt
    3. Generate answer with citations
    """
    # Step 1: Retrieve
    chunks = retrieve_chunks(question, limit=8)
    
    if not chunks:
        return {
            "answer": "No relevant documents found for your question.",
            "sources": [],
            "chunks_retrieved": 0
        }
    
    # Step 2: Build prompt
    prompt = build_prompt(question, chunks)
    
    # Step 3: Generate
    answer = generate_answer(prompt)
    
    # Step 4: Format sources for display
    sources = [
        {
            "file_name": c.get("file_name", ""),
            "section": c.get("section_heading", ""),
            "document_type": c.get("document_type", "")
        }
        for c in chunks
    ]
    
    return {
        "answer": answer,
        "sources": sources,
        "chunks_retrieved": len(chunks)
    }


if __name__ == "__main__":
    # Quick test
    test_question = "What are the safety monitoring requirements for radiopharmaceutical therapies?"
    print(f"Question: {test_question}\n")
    result = rag_query(test_question)
    print(f"Answer:\n{result['answer']}\n")
    print(f"Sources used: {len(result['sources'])}")
    for i, source in enumerate(result['sources'], 1):
        print(f"  [{i}] {source['file_name']} — {source['section']}")