with final as (

    select
        p.id,
        p.holder,
        p.account,
        p.ticker,
        p.shares,
        p.buy_date,
        p.buy_price,
        p.close_date,
        p.close_price,
        coalesce(p.close_price, s.close_price) as last_price,
        coalesce(p.close_date, s.date) as last_date,
        p.close_price is not null as is_closed_position,
        p.last_edited as position_last_edited
    from {{ ref('stg_portfolio_tracker__portfolio_positions') }} as p
    left join {{ ref('fct_stock_open_close_prices') }} as s
        on p.ticker = s.ticker
    where s.is_latest_price

)

select * from final
