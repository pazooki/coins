Coins
=====
Coins is a modular real-time bidder that is configurable and compatible with bitcoin exchanges.

Available Strategies:
---------------------
- EMA
- Bollinger Bands
- SMA
- RSI
- MACD

Here is an example of a `bid` method for a `Strategy` implementation:
```
    def bid(self):
        self.init_position()
        # price_mode, price_direction = self.analyze_depth()

        long_signals = filters_to_signals(self.long_condition_is_valid)
        short_signals = filters_to_signals(self.short_condition_is_valid)
        # long_signals = all(self.long_condition_is_valid)
        # short_signals = all(self.short_condition_is_valid)

        must_buy = all([
            (not self.trades or self.trades[-1].side == SIDE_SELL),
            self.balance['USDT'] > self.BALANCE_MIN_USDT,
            long_signals > short_signals,
            long_signals >= self.SIGNAL_THRESHOLD,
            # is_uptrend,
            # price_mode in ['SUPPORT']
        ])

        must_sell = all([
            (not self.trades or self.trades[-1].side == SIDE_BUY),
            self.balance['BTC'] > self.BALANCE_MIN_BTC,
            short_signals > long_signals,
            short_signals >= self.SIGNAL_THRESHOLD,
            # not is_uptrend,
            # price_mode in ['RESISTANCE']
        ])

        header = {}
        header.update(self.balance)
        header.update(dict(
            tp=self.TAKE_PROFIT_PCT, 
            sl=self.STOP_LOSS_PCT, 
            st_at=self.time__started.strftime("%d %H:%M:%S"),
            cur_at=self.time__current.strftime("%d %H:%M:%S")
        ))
        self.logger.log('BALANCE:  {BTC:.8f} BTC   {USDT:.2f} USDT    |   TP: {tp}%    SL: {sl}%   |   ST@: {st_at}     CUR@: {cur_at}      |'.format(**header))
        self.logger.log('-' * 140)
        self.logger.log('POS>   PRICE: %.2f   -  CUR PRICE: %.2f   =   DIFF: %.2f    PL_PCT: %.4f%%     |   SIGS>  L: %d %s   S: %d %s    UP_TREND: %s    |' % (
            self.position.open_price,
            self.last_price,
            self.last_price - self.position.open_price,
            self.position.calc_pl_pct(self.last_price),
            long_signals, must_buy, short_signals, must_sell, self.price_is_uptrend
        ))
        self.logger.log('-' * 140)
        self.logger.log('STATS> T#: %d     WINS: %d     LOSSES: %d  |   SIDE: %s    |' % (
            len(self.trades),
            sum(1 if t == POS_WIN else 0 for t in list(self.trades_history.status)),
            sum(1 if t == POS_LOSS else 0 for t in list(self.trades_history.status)),
            self.current_side 
        ))

        # return None

        if not self.can_enter:
            self.logger.log('CANNOT ENTER')
            return None
        
        if must_buy: #self.position.side == SIDE_SELL:# and can_buy and price_mode in ['SUPPORT']:
            if self.has_no_trades:
                self.call_until_executed(self.long_all_market, dict(status=POS_INIT))
            else:
                take_profit_trigger = self.position.calc_pl_pct(self.last_price) < (-self.TAKE_PROFIT_PCT)
                stop_loss_trigger = self.position.calc_pl_pct(self.last_price) >= self.STOP_LOSS_PCT

                if take_profit_trigger:# and price_direction > self.last_price:
                    self.call_until_executed(self.long_all_market, dict(status=POS_WIN))
                elif stop_loss_trigger:# and price_direction > self.last_price:
                    self.call_until_executed(self.long_all_market, dict(status=POS_LOSS))
                else:
                    self.logger.log('ACTION) NO BUY')
        elif must_sell: #and self.position.side == SIDE_BUY:# and price_mode in ['RESISTANCE']:
            if self.has_no_trades:
                self.call_until_executed(self.short_all_market, dict(status=POS_INIT))
            else:
                # self.logger.log('pl_pct: ', self.position.calc_pl_pct(self.last_price))
                take_profit_trigger = self.position.calc_pl_pct(self.last_price) > self.TAKE_PROFIT_PCT
                stop_loss_trigger = self.position.calc_pl_pct(self.last_price) <= self.STOP_LOSS_PCT

                if take_profit_trigger: # and price_direction <= self.last_price and price_mode in ['RESISTANCE']:
                    self.call_until_executed(self.short_all_market, dict(status=POS_WIN))
                elif stop_loss_trigger:# and price_direction < self.last_price:
                    self.call_until_executed(self.short_all_market, dict(status=POS_LOSS))
                else:
                    self.logger.log('ACTION) NO SELL')
```
