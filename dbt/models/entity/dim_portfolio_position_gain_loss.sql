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
        cost_basis / benchmark_buy.open_price as benchmark_shares,
        coalesce(benchmark_date_match.date, benchmark_latest.date) as benchmark_latest_date,
        benchmark_shares
        * coalesce(benchmark_date_match.close_price, benchmark_latest.close_price) as benchmark_market_value,
        benchmark_market_value - cost_basis as benchmark_gain_loss,
        gain_loss - benchmark_gain_loss as performance_against_benchmark,
        benchmark_date_match.ticker is not null as is_up_to_date_benchmark,
        p.close_price is null as is_open_position,
        p.last_edited as position_last_edited
    from {{ ref('stg_portfolio_tracker__portfolio_positions') }} as p
    left join {{ ref('fct_stock_open_close_prices') }} as s
        on p.ticker = s.ticker
        and s.is_latest_price
    left join {{ ref('fct_stock_open_close_prices') }} as benchmark_buy  -- Track benchmark price when position was bought
        on benchmark_buy.ticker = 'CSPX.L'
        and benchmark_buy.date = p.buy_date
    left join {{ ref('fct_stock_open_close_prices') }} as benchmark_date_match   -- Track matching benchmark prices
        on benchmark_date_match.ticker = 'CSPX.L'
        and benchmark_date_match.date = p.close_date
    left join {{ ref('fct_stock_open_close_prices') }} as benchmark_latest  -- Track any lagging benchmark prices when no matches
        on benchmark_latest.ticker = 'CSPX.L'
        and benchmark_latest.is_latest_price

)

select * from final
