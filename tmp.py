@njit
def get_sc(close, period=10, fast_ma_len=2, slow_ma_len=30):
    fastest_sc = 2 / (fast_ma_len + 1)
    slowest_sc = 2 / (slow_ma_len + 1)

    price_shifted_1 = np.roll(close,1)
    price_shifted_1[0] = np.nan
    diff_close = np.abs(close - price_shifted_1)

    conv_arr = np.ones(period, dtype=int)
    denom = np.convolve(diff_close, conv_arr, 'full')[:-(period-1)]

    price_shifted_period = np.roll(A,period)
    price_shifted_period[0:period] = np.nan
    ER = np.abs(close - price_shifted_period) / denom
    sc = (ER * (fastest_sc - slowest_sc) + slowest_sc) ** 2

    return sc
    

@njit
def get_kama(close, sc):
    # assert(close.shape[0] == sc.shape[0])
    kama = np.full((close.shape[0]), np.nan)
    for i in range(1,close.shape[0]):  
        if not np.isnan(sc[i]):
            if np.isnan(kama[i-1]):
                kama[i-1] = close[0]
            kama[i] = kama[i-1] + (sc[i] * (close[i] - kama[i-1]))
        else:
            kama[i] = np.nan
    return kama
            