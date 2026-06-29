with final as (

    select
        id::bigint as id,
        holder::varchar as holder,
        account::varchar as account,
        case
            when sym::varchar = 'CSPX'  -- Temporary until we get EHOD API ready
                then 'SPY'
            else sym::varchar
        end as ticker,
        shares::double as shares,
        buy_date::varchar as buy_date,
        buy_price::double as buy_price,
        close_date::varchar as close_date,
        close_price::double as close_price,
        last_edited::timestamptz as last_edited
    from portfolio_tracker.raw.portfolio_positions
    where sym::varchar not in (select delisted_tickers from {{ ref('seed_delisted_tickers') }})  -- Until EHOD API is ready, yfinance cannot get delisted stock data

)

select * from final
