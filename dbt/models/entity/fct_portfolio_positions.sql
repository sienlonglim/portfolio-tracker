with final as (

    select
        id,
        account,
        sym as ticker,
        shares,
        buy_date,
        buy_price,
        close_date,
        close_price
    from {{ ref('seed_portfolio_positions') }}

)

select * from final
