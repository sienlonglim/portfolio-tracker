with final as (

    select
        ticker,
        date,
        open_price,
        high_price,
        low_price,
        close_price,
        traded_volume,
        row_number() over (partition by ticker order by date desc) = 1 as is_latest_price,
        date = current_date() as is_updated_price
    from {{ ref('stg_portfolio_tracker__stock_open_close_prices') }}

)

select * from final