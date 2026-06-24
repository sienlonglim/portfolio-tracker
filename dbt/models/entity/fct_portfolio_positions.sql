with final as (

    select
        p.id,
        p.account,
        p.sym as ticker,
        p.shares,
        p.buy_date,
        p.buy_price,
        p.close_date,
        p.close_price,
        coalesce(p.close_price, s.close_price) as current_price,
        coalesce(p.close_date, s.date) as current_date,
        p.close_price is not null as is_closed_position
    from {{ ref('seed_portfolio_positions') }} as p
    left join {{ ref('fct_stock_open_close_prices') }} as s
        on p.sym = s.ticker
    where s.is_latest_price

)

select * from final
