with source as (
    select
        relative_path,
        parsed_content,
        loaded_at
    from {{ source('raw', 'parsed_documents') }}
),

cleaned as (
    select
        -- file identity
        relative_path,
        loaded_at,

        -- extract text content from JSON
        parsed_content:content::string as raw_text,

        -- extract page count from metadata
        parsed_content:metadata:pageCount::integer as page_count,

        -- derive document name from file path
        split_part(relative_path, '/', -1) as file_name,

        -- classify document type based on filename keywords
        case
            when lower(relative_path) like '%guidance%'       then 'FDA_GUIDANCE'
            when lower(relative_path) like '%protocol%'       then 'CLINICAL_PROTOCOL'
            when lower(relative_path) like '%sap%'            then 'STATISTICAL_ANALYSIS_PLAN'
            when lower(relative_path) like '%dg_%'            then 'FDA_GUIDANCE'
            when lower(relative_path) like '%fnl%'            then 'FDA_GUIDANCE'
            when lower(relative_path) like '%draft%'          then 'FDA_GUIDANCE'
            when lower(relative_path) like '%optimiz%'        then 'FDA_GUIDANCE'
            when lower(relative_path) like '%oncology%'       then 'FDA_GUIDANCE'
            when lower(relative_path) like '%clinical%'       then 'CLINICAL_PROTOCOL'
            else 'FDA_GUIDANCE'
        end as document_type,

        -- strip repeated boilerplate footer/header text
        regexp_replace(
            regexp_replace(
                parsed_content:content::string,
                'Contains Nonbinding Recommendations\\s*', ''
            ),
            'Draft — Not for Implementation\\s*', ''
        ) as cleaned_text,

        -- flag whether document is a draft
        case
            when lower(parsed_content:content::string) like '%draft guidance%' then true
            else false
        end as is_draft,

        -- capture load timestamp for freshness tracking
        current_timestamp() as dbt_updated_at

    from source
    where parsed_content:content::string is not null
)

select * from cleaned