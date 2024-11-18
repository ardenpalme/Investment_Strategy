from vectorbtpro import *
from example_streaming import *

data = vbt.HDFData.pull(['my_data.h5/BTCUSDT', 'my_data.h5/ETHUSDT'])
date_range = slice('2020-01-01', '2020-02-01')

periods = np.arange(4, 20)
multipliers = np.arange(20, 41) / 10 


SuperTrend = vbt.IF(
    class_name='SuperTrend',
    short_name='st',
    input_names=['high', 'low', 'close'],
    param_names=['period', 'multiplier'],
    output_names=['superd', 'supert', 'superl', 'supers']
).with_apply_func(
    superfast_supertrend_nb,
    takes_1d=True,
    period=7,
    multiplier=3
)

def pipeline(data, period=3, multiplier=7):
    high = data.get('High')
    low = data.get('Low')
    close = data.get('Close')
    st = SuperTrend.run(
        high, low, close, 
        period=period, 
        multiplier=multiplier
    )

    entries = (~st.superl.isnull()).vbt.signals.fshift()
    exits = (~st.supers.isnull()).vbt.signals.fshift()

    pf = vbt.Portfolio.from_signals(
        close,
        entries=entries,
        exits=exits,
        fees=0.001,
        save_returns=True,
        max_order_records=0,
        freq='1h'
    )

    return pf.sharpe_ratio

chunked_pipeline = vbt.chunked(
    size=vbt.LenSizer(arg_query='period', single_type=int),
    arg_take_spec=dict(
        data=None,
        period=vbt.ChunkSlicer(),
        multiplier=vbt.ChunkSlicer()
    ),
    merge_func= lambda x: pd.concat(x).sort_index()
)(pipeline)

@njit(nogil=True)
def pipeline_nb(high, low, close, 
                periods=np.asarray([7]),  
                multipliers=np.asarray([3]), 
                ann_factor=365):

    sharpe = np.empty(periods.size * close.shape[1], dtype=float_)
    long_entries = np.empty(close.shape, dtype=np.bool_)
    long_exits = np.empty(close.shape, dtype=np.bool_)
    group_lens = np.full(close.shape[1], 1)
    init_cash = 100.
    fees = 0.001
    k = 0
    
    for i in range(periods.size):
        for col in range(close.shape[1]):
            _, _, superl, supers = superfast_supertrend_nb(  
                high[:, col], 
                low[:, col], 
                close[:, col], 
                periods[i], 
                multipliers[i]
            )
            long_entries[:, col] = vbt.nb.fshift_1d_nb(  
                ~np.isnan(superl), 
                fill_value=False
            )
            long_exits[:, col] = vbt.nb.fshift_1d_nb(
                ~np.isnan(supers), 
                fill_value=False
            )
            
        sim_out = vbt.pf_nb.from_signals_nb(  
            target_shape=close.shape,
            group_lens=group_lens,
            init_cash=init_cash,
            high=high,
            low=low,
            close=close,
            long_entries=long_entries,
            long_exits=long_exits,
            fees=fees,
            save_returns=True
        )
        returns = sim_out.in_outputs.returns
        _sharpe = vbt.ret_nb.sharpe_ratio_nb(returns, ann_factor, ddof=1)  
        sharpe[k:k + close.shape[1]] = _sharpe  
        k += close.shape[1]
        
    return sharpe

op_tree = (product, periods, multipliers)
period_product, multiplier_product = vbt.generate_param_combs(op_tree)
period_product = np.asarray(period_product)
multiplier_product = np.asarray(multiplier_product)

ann_factor = vbt.pd_acc.returns.get_ann_factor(freq='1h')  

high = data.get('High')
low = data.get('Low')
close = data.get('Close')

def merge_func(arrs, ann_args, input_columns):  
    arr = np.concatenate(arrs)
    param_index = vbt.stack_indexes((  
        pd.Index(ann_args['periods']['value'], name='st_period'),
        pd.Index(ann_args['multipliers']['value'], name='st_multiplier')
    ))

    index = vbt.combine_indexes((  
        param_index,
        input_columns
    ))

    return pd.Series(arr, index=index)  

nb_chunked = vbt.chunked(
    size=vbt.ArraySizer(arg_query='periods', axis=0),
    arg_take_spec=dict(
            high=None,
            low=None,
            close=None,
            periods=vbt.ArraySlicer(axis=0),
            multipliers=vbt.ArraySlicer(axis=0),
            ann_factor=None
    ),
    merge_func=merge_func,
    merge_kwargs=dict(
            ann_args=vbt.Rep("ann_args")
    )
)

chunked_pipeline_nb = nb_chunked(pipeline_nb)