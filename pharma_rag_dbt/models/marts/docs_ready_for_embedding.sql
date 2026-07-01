with chunks as (
    select
        chunk_id,
        file_name,
        document_type,
        is_draft,
        page_count,
        section_number,
        section_heading,
        chunk_text,
        word_count,
        dbt_updated_at
    from {{ ref('int_document_chunks') }}
),

final as (
    select
        -- unique identifier
        chunk_id,

        -- document identity
        file_name,
        document_type,
        is_draft,
        page_count,

        -- chunk identity
        section_number,
        section_heading,

        -- text content ready for embedding
        chunk_text,

        -- enriched text for embedding
        -- combining heading + text gives better semantic context
        section_heading || ' ' || chunk_text as text_for_embedding,

        -- quality filters
        word_count,

        -- only keep chunks with meaningful content
        -- too short = noise, too long = poor retrieval
        case
            when word_count < 20  then 'TOO_SHORT'
            when word_count > 800 then 'TOO_LONG'
            else 'GOOD'
        end as chunk_quality,

        -- metadata for citation in RAG responses
        current_timestamp() as embedded_at

    from chunks
    where word_count >= 20
)

select * from final