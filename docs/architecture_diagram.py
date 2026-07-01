from diagrams import Diagram, Cluster, Edge
from diagrams.generic.storage import Storage
from diagrams.generic.database import SQL
from diagrams.generic.compute import Rack
from diagrams.onprem.client import User
from diagrams.programming.language import Python
from diagrams.onprem.analytics import Dbt

with Diagram(
    "PharmaRAG — FDA Regulatory Knowledge Assistant",
    filename="docs/architecture",
    outformat="png",
    show=False,
    direction="LR"
):
    user = User("User")

    with Cluster("Data Sources"):
        fda = Storage("FDA Guidance\nDocuments (PDFs)")
        ct = Storage("ClinicalTrials.gov\nProtocols (PDFs)")

    with Cluster("Snowflake Platform"):

        with Cluster("Ingestion Layer"):
            stage = SQL("Internal Stage\n(doc_stage)")
            parse = Rack("PARSE_DOCUMENT\n(Cortex)")

        with Cluster("dbt Pipeline"):
            raw = SQL("raw.\nparsed_documents")
            stg = SQL("staging.\nstg_documents")
            intr = SQL("intermediate.\nint_document_chunks")
            mart = SQL("marts.\ndocs_ready_for_embedding")
            dbt = Dbt("dbt Core")

        with Cluster("AI Layer"):
            embed = Rack("EMBED_TEXT_768\n(Cortex)")
            embedtable = SQL("marts.\ndocument_embeddings")
            search = Rack("Cortex Search\nService")
            llm = Rack("COMPLETE\nMistral Large 2")

    with Cluster("Application Layer"):
        rag = Python("rag_query.py\n(RAG Pipeline)")
        app = Python("Streamlit App\n(Chat UI)")

    # data flow
    fda >> stage
    ct >> stage
    stage >> parse >> raw
    raw >> dbt
    dbt >> stg >> intr >> mart
    mart >> embed >> embedtable >> search
    user >> app >> rag
    rag >> search
    search >> Edge(label="top-k chunks") >> rag
    rag >> llm
    llm >> Edge(label="cited answer") >> app