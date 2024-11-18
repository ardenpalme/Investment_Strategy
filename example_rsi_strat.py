from vectorbtpro import *

data = vbt.BinanceData.pull(['BTCUSDT', 'ETHUSDT'])

open_price=data.get('Open')
close_price=data.get('Close')

windows = list(range(8,21))
wtypes = ["simple", "exp", "wilder"]
rsi = vbt.RSI.run(
    open_price,
    window=windows,
    wtype=wtypes,
    param_product=True)

lower_ths = list(range(20,31))
upper_ths = list(range(70,81))
lower_ths_prod, upper_ths_prod = zip(*product(lower_ths, upper_ths))

lower_th_index = vbt.Param(lower_ths_prod, name='lower_th')
entries = rsi.rsi_crossed_below(lower_th_index)

upper_th_index = vbt.Param(upper_ths_prod, name='upper_th')
exits = rsi.rsi_crossed_above(upper_th_index)

pf = vbt.Portfolio.from_signals(
    close=close_price,
    entries=entries,
    exits=exits,
    size=100,
    size_type='value',
    init_cash='auto'
)
stats_df = pf.stats([
    'total_return',
    'total_trades',
    'win_rate',
    'expectancy'
], agg_func=None)

print(stats_df)

eth_mask = stats_df.index.get_level_values('symbol') == 'ETHUSDT'
btc_mask = stats_df.index.get_level_values('symbol') == 'BTCUSDT'
pd.DataFrame({
    'ETHUSDT': stats_df[eth_mask]['Expectancy'].values,
    'BTCUSDT': stats_df[btc_mask]['Expectancy'].values
}).vbt.histplot(xaxis=dict(title="Expectancy")).show() 