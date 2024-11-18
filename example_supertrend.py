from vectorbtpro import *
import talib

data = vbt.HDFData.pull(['my_data.h5/BTCUSDT', 'my_data.h5/ETHUSDT'])
date_range = slice('2020-01-01', '2020-02-01')

high = data.get('High')
low = data.get('Low')
close = data.get('Close')

def get_med_price(high, low):
    return (high + low) / 2

def get_atr_np(high, low, close, period):
    shifted_close = vbt.nb.fshift_1d_nb(close)  
    tr0 = np.abs(high - low)
    tr1 = np.abs(high - shifted_close)
    tr2 = np.abs(low - shifted_close)
    tr = np.column_stack((tr0, tr1, tr2)).max(axis=1)  
    atr = vbt.nb.wwm_mean_1d_nb(tr, period)  
    return atr

def get_basic_bands(med_price, atr, multiplier):
    matr = multiplier * atr
    upper = med_price + matr
    lower = med_price - matr
    return upper, lower

@njit
def get_final_bands_nb(close, upper, lower):  
    trend = np.full(close.shape, np.nan)  
    dir_ = np.full(close.shape, 1)
    long = np.full(close.shape, np.nan)
    short = np.full(close.shape, np.nan)

    for i in range(1, close.shape[0]):
        if close[i] > upper[i - 1]:  
            dir_[i] = 1
        elif close[i] < lower[i - 1]:
            dir_[i] = -1
        else:
            dir_[i] = dir_[i - 1]
            if dir_[i] > 0 and lower[i] < lower[i - 1]:
                lower[i] = lower[i - 1]
            if dir_[i] < 0 and upper[i] > upper[i - 1]:
                upper[i] = upper[i - 1]

        if dir_[i] > 0:
            trend[i] = long[i] = lower[i]
        else:
            trend[i] = short[i] = upper[i]

    return trend, dir_, long, short

def faster_supertrend_talib(high, low, close, period=7, multiplier=3):
    avg_price = talib.MEDPRICE(high, low)  
    atr = talib.ATR(high, low, close, period)
    upper, lower = get_basic_bands(avg_price, atr, multiplier)
    return get_final_bands_nb(close, upper, lower)

def faster_supertrend(high, low, close, period=7, multiplier=3):
    med_price = get_med_price(high, low)
    atr = get_atr_np(high, low, close, period)
    upper, lower = get_basic_bands(med_price, atr, multiplier)
    return get_final_bands_nb(close, upper, lower)

supert, superd, superl, supers = faster_supertrend_talib(
    high['BTCUSDT'].values, 
    low['BTCUSDT'].values, 
    close['BTCUSDT'].values
)

SuperTrend = vbt.IF(
    class_name='SuperTrend',
    short_name='st',
    input_names=['high', 'low', 'close'],
    param_names=['period', 'multiplier'],
    output_names=['supert', 'superd', 'superl', 'supers']
).with_apply_func(
    faster_supertrend_talib,
    takes_1d=True,
    period=7,
    multiplier=3
)

class SuperTrend(SuperTrend):
    def plot(self, 
             column=None,  
             close_kwargs=None,  
             superl_kwargs=None,
             supers_kwargs=None,
             fig=None,  
             **layout_kwargs):  

        close_kwargs = close_kwargs if close_kwargs else {}
        superl_kwargs = superl_kwargs if superl_kwargs else {}
        supers_kwargs = supers_kwargs if supers_kwargs else {}

        close = self.select_col_from_obj(self.close, column).rename('Close')
        supers = self.select_col_from_obj(self.supers, column).rename('Short')
        superl = self.select_col_from_obj(self.superl, column).rename('Long')

        fig = close.vbt.plot(fig=fig, **close_kwargs, **layout_kwargs)  
        supers.vbt.plot(fig=fig, **supers_kwargs)
        superl.vbt.plot(fig=fig, **superl_kwargs)

        return fig

st = SuperTrend.run(high,low,close)

entries = (~st.superl.isnull()).vbt.signals.fshift()
exits = (~st.supers.isnull()).vbt.signals.fshift()

pf = vbt.Portfolio.from_signals(
    close=close, 
    entries=entries, 
    exits=exits, 
    fees=0.001, 
    freq='1h'
)