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
        coalesce(s.close_price, p.close_price) as last_price,
        coalesce(s.date, p.close_date) as last_date,
        p.shares * last_price as market_value,
        market_value - cost_basis as gain_loss,
        cost_basis / benchmark_buy.open_price * benchmark_current.close_price as benchmark_market_value,  -- Buy at the open of buy date, value at close of current date
        benchmark_market_value - cost_basis as benchmark_gain_loss,
        p.close_price is null as is_open_position,
        p.last_edited as position_last_edited
    from {{ ref('stg_portfolio_tracker__portfolio_positions') }} as p
    left join {{ ref('fct_stock_open_close_prices') }} as s
        on p.ticker = s.ticker
        and s.date >= p.buy_date
        and s.date <= coalesce(p.close_date, strftime(current_date, '%Y-%m-%d'))
    left join {{ ref('fct_stock_open_close_prices') }} as benchmark_current
        on benchmark_current.ticker = 'CSPX.AS'
        and benchmark_current.date = s.date
    left join {{ ref('fct_stock_open_close_prices') }} as benchmark_buy
        on benchmark_buy.ticker = 'CSPX.AS'
        and benchmark_buy.date = p.buy_date

)
select * from final
