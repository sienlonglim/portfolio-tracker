with final as (

    select
        *,
        row_number() over (partition by ticker order by date desc) = 1 as is_latest_price,
        date = current_date() as is_updated_price
    from {{ ref('stg_portfolio_tracker__stock_open_close_prices') }}

)

select * from final