with final as (

    select
        id::bigint as id,
        holder::varchar as holder,
        account::varchar as account,
        sym::varchar as ticker,
        shares::double as shares,
        buy_date::varchar as buy_date,
        buy_price::double as buy_price,
        close_date::varchar as close_date,
        close_price::double as close_price,
        last_edited::timestamptz as last_edited
    from portfolio_tracker.raw.portfolio_positions
    where sym::varchar not in (select delisted_tickers from {{ ref('seed_delisted_tickers') }})

)

select * from final
