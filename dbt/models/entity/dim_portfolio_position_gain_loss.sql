-- Note: stg_portfolio_tracker__portfolio_positions.close_price refers to closed positions
-- as opposed to fct_stock_open_close_prices.close_price which refers to the latest price of the stock 

with final as (

    select
        p.id,
        p.holder,
        p.account,
        p.ticker,
        p.shares,
        p.buy_date,
        p.buy_price,
        p.shares * p.buy_price as cost_basis,
        p.close_date,
        p.close_price,  
        coalesce(p.close_price, s.close_price) as last_price,
        coalesce(p.close_date, s.date) as last_date,
        p.shares * last_price as market_value,
        market_value - cost_basis as gain_loss,
        p.close_price is null as is_open_position,
        p.last_edited as position_last_edited
    from {{ ref('stg_portfolio_tracker__portfolio_positions') }} as p
    left join {{ ref('fct_stock_open_close_prices') }} as s
        on p.ticker = s.ticker
        and s.is_latest_price

)

select * from final
