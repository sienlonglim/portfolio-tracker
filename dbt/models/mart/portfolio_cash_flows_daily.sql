with final as (

    select
        holder,
        event_date,
        cash_deployed,
        cash_pool
    from {{ ref('fct_portfolio_cash_flows') }}
    qualify row_number() over (
        partition by holder, event_date
        order by same_day_order_precedence desc, id desc
    ) = 1

)

select * from final
