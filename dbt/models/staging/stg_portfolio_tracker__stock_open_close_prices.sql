with final as (

    select
        ticker::varchar as ticker,
        date::date as date,
        open::double as open_price,
        high::double as high_price,
        low::double as low_price,
        close::double as close_price,
        volume::bigint as traded_volume,
        metafile_name::varchar as metafile_name,
        metafile_modified::timestamp as metafile_modified
    from portfolio_tracker.raw.stock_open_close_prices
    where open is not null
    qualify row_number() over (
        partition by ticker, date
        order by metafile_modified desc
    ) = 1

)

select * from final
