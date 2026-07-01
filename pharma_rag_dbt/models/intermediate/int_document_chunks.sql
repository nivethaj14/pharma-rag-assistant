with documents as (
    select
        file_name,
        document_type,
        is_draft,
        page_count,
        cleaned_text,
        dbt_updated_at
    from {{ ref('stg_documents') }}
),

-- split document text into sections based on markdown headers
split_sections as (
    select
        file_name,
        document_type,
        is_draft,
        page_count,
        dbt_updated_at,
        -- split on lines starting with # or ##
        f.value::string as section_text,
        f.index + 1 as section_number
    from documents,
    lateral flatten(
        input => split(
            cleaned_text,
            '\n#'
        )
    ) f
),

cleaned_sections as (
    select
        file_name,
        document_type,
        is_draft,
        page_count,
        section_number,
        dbt_updated_at,

        -- restore the # that got stripped by the split
        case
            when section_number = 1 then section_text
            else '#' || section_text
        end as section_text,

        -- extract section heading (first line of each chunk)
        split_part(
            case
                when section_number = 1 then section_text
                else '#' || section_text
            end,
            '\n', 1
        ) as section_heading,

        -- word count per chunk for quality checking
        array_size(
            split(trim(section_text), ' ')
        ) as word_count

    from split_sections
    where trim(section_text) != ''
      and length(trim(section_text)) > 50
),

final as (
    select
        -- unique chunk identifier
        md5(file_name || '-' || section_number::string) as chunk_id,
        file_name,
        document_type,
        is_draft,
        page_count,
        section_number,
        section_heading,
        section_text as chunk_text,
        word_count,
        dbt_updated_at
    from cleaned_sections
)

select * from final