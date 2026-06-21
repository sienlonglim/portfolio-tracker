-- Need to rank files
with ranked_files as (
    
    select
        *,
        row_number() over (partition by ticker, date order by created_at desc) as file_rank
    from source('portfolio_tracker', 'stock_prices_open_close')

)

select * from ranked_files
where file_rank = 1