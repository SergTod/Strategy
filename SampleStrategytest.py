# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy, merge_informative_pair, DecimalParameter, IntParameter
import pandas as pd
import numpy as np
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class SampleStrategytest(IStrategy):
    # --- Strategy Parameters ---
    minimal_roi = {"0": 0.02}
    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    timeframe = '1h'
    stake_currency = 'USDT'
    startup_candle_count: int = 200

    # Risk exposure control
    max_drawdown = -0.10  # Used in logic for hard exit
    loss_streak_limit = 3
    loss_streak = 0  # Internal counter

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[
            (dataframe['close'] > dataframe['ema_200']) &
            (dataframe['adx'] > 25) &
            (dataframe['rsi'] < 30),
            'enter_long'] = 1
        return dataframe

    def custom_exit(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].copy()

        # Dynamic ATR-based stop
        atr_stop = trade.open_rate - 2 * last_candle['atr']
        if current_rate < atr_stop:
            return 'atr_stop'

        # Drawdown guard
        if current_profit < self.max_drawdown:
            return 'drawdown_guard'

        # ROI target logic
        if current_profit > 0.03:
            return 'roi_target'

        return None

    def custom_stake_amount(self, pair: str, current_price: float, proposed_stake: float, **kwargs) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].copy()
        atr = last_candle['atr']
        risk_per_trade = 0.01  # 1% of account
        account_balance = 10000  # Can also fetch dynamically if needed

        # Volatility-adjusted stake
        stake_amount = (account_balance * risk_per_trade) / (atr if atr > 0 else 1)
        stake_value = stake_amount * current_price
        return min(stake_value, proposed_stake)
