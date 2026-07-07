import streamlit as st
from src.rag_query import rag_query

# page config
st.set_page_config(
    page_title="PharmaRAG — FDA Regulatory Assistant",
    page_icon="💊",
    layout="wide"
)

# header
st.title("💊 PharmaRAG")
st.subheader("FDA Regulatory & Clinical Knowledge Assistant")
st.markdown(
    "Ask questions about FDA oncology guidance documents "
    "and clinical trial protocols. All answers are grounded "
    "in source documents with citations."
)

st.divider()

# sidebar
with st.sidebar:
    st.header("About")
    st.markdown("""
    **PharmaRAG** is a Retrieval-Augmented Generation 
    system built on:
    - Snowflake Cortex Search
    - Snowflake Cortex LLM (Mistral Large 2)
    - dbt for data transformation
    - FDA public guidance documents
    """)

st.divider()
    st.info(
        "ℹ️ **Portfolio Demo**\n\n"
        "Running on a Snowflake trial account. "
        "If the app is slow to respond, the warehouse "
        "may be warming up — please wait 10-15 seconds "
        "and try again.\n\n"
        "Built by Nivetha Jayaram Raja · "
        "[LinkedIn](https://www.linkedin.com/in/nivetha-jayaram-raja-data-analytics/)"
    )

    st.divider()
    st.header("Sample Questions")
    sample_questions = [
        "What are the safety monitoring requirements for radiopharmaceutical therapies?",
        "What is the recommended approach for dose escalation in oncology trials?",
        "How should sponsors handle dosimetry in RPT clinical trials?",
        "What participant populations are suitable for RPT dose-finding trials?",
        "What are the key considerations for trial design in dosage optimization?"
    ]
    
    for q in sample_questions:
        if st.button(q, use_container_width=True):
            st.session_state.question = q

st.divider()

# initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "question" not in st.session_state:
    st.session_state.question = ""

# display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and "sources" in message:
            with st.expander("📚 Sources used"):
                for i, source in enumerate(message["sources"], 1):
                    st.markdown(
                        f"**[{i}]** `{source['file_name']}`  \n"
                        f"Section: *{source['section']}*  \n"
                        f"Type: `{source['document_type']}`"
                    )

# handle sidebar button clicks
if st.session_state.question:
    prompt = st.session_state.question
    st.session_state.question = ""
else:
    prompt = st.chat_input(
        "Ask a question about FDA oncology guidance or clinical trial protocols..."
    )

# process question
if prompt:
    # add user message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })
    
    with st.chat_message("user"):
        st.markdown(prompt)

    # generate answer
    with st.chat_message("assistant"):
        with st.spinner("Searching documents and generating answer..."):
            result = rag_query(prompt)
        
        st.markdown(result["answer"])
        
        # show sources
        with st.expander(
            f"📚 {result['chunks_retrieved']} source chunks retrieved"
        ):
            for i, source in enumerate(result["sources"], 1):
                st.markdown(
                    f"**[{i}]** `{source['file_name']}`  \n"
                    f"Section: *{source['section']}*  \n"
                    f"Type: `{source['document_type']}`"
                )
        
        # add to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"]
        })