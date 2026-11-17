with events as (
    -- buys: cash out
    select
        holder,
        id,
        ticker,
        'BUY' as event_type,
        cast(buy_date as date) as event_date,
        1 as same_day_order_precedence,
        -shares * buy_price as cash_flow
    from {{ ref('stg_portfolio_tracker__portfolio_positions') }}
    where buy_date is not null

    union all

    -- sells: cash back into the pool
    select
        holder,
        id,
        ticker,
        'SELL',
        cast(close_date as date),
        0,
        shares * close_price
    from {{ ref('stg_portfolio_tracker__portfolio_positions') }}
    where close_date is not null

),

running as (

    select
        *,
        sum(cash_flow) over w as cum_net_flow
    from events
    window w as (
        partition by holder
        order by event_date, same_day_order_precedence, id
        rows between unbounded preceding and current row
    )

),

deployed as (

    select
        *,
        greatest(0, -min(cum_net_flow) over w) as cash_deployed
    from running
    window w as (
        partition by holder
        order by event_date, same_day_order_precedence, id
        rows between unbounded preceding and current row
    )

),

final as (

  select
      holder,
      event_date,
      event_type,
      same_day_order_precedence,
      id,
      ticker,
      cash_flow,
      cash_deployed - lag(cash_deployed, 1, 0) over (
          partition by holder
          order by event_date, same_day_order_precedence, id
      ) as new_cash_added,
      cash_deployed,
      cum_net_flow + cash_deployed as cash_pool
  from deployed

)

select * from final
