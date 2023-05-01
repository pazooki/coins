

```
Transfer In:
    update_cross_margin_balance:  {'e': 'balanceUpdate', 'E': 1682546506976, 'a': 'BTC', 'd': '0.00040714', 'T': 1682546506976}
    update_cross_margin_balance:  {'e': 'outboundAccountPosition', 'E': 1682546506976, 'u': 1682546506976, 'B': [{'a': 'BTC', 'f': '0.00040714', 'l': '0.00000000'}]}

Transfer Out:
    update_cross_margin_balance:  {'e': 'balanceUpdate', 'E': 1682546567529, 'a': 'BTC', 'd': '-0.00040714', 'T': 1682546567528}
    update_cross_margin_balance:  {'e': 'outboundAccountPosition', 'E': 1682546567529, 'u': 1682546567528, 'B': [{'a': 'BTC', 'f': '0.00000000', 'l': '0.00000000'}]}

Trade Buy:
    update_cross_margin_balance:  {
        'e': 'balanceUpdate', 
        'E': 1682546690294, 
        'a': 'USDT', 
        'd': '11.73663950', 
        'T': 1682546690293
    }
    update_cross_margin_balance:  {
        'e': 'outboundAccountPosition', 
        'E': 1682546690294, 
        'u': 1682546690293, 
        'B': [{'a': 'USDT', 'f': '11.73663950', 'l': '0.00000000'}]
    }
    https://github.com/binance/binance-spot-api-docs/blob/master/user-data-stream.md#execution-types
    update_cross_margin_balance:  {
        'e': 'executionReport', 
        'E': 1682546690317, 
        's': 'BTCUSDT', 
        'c': 'default_09734faff5a743e99b4e868a25b6', 
        'S': 'BUY', 
        'o': 'MARKET', 
        'f': 'GTC', 
        'q': '0.00041000', 
        'p': '0.00000000', 
        'P': '0.00000000', 
        'F': '0.00000000', 
        'g': -1, 
        'C': '', 
        'x': 'NEW', 
        'X': 'NEW', 
        'r': 'NONE', 
        'i': 20931213771, 
        'l': '0.00000000', 
        'z': '0.00000000', 
        'L': '0.00000000', 
        'n': '0', 
        'N': None, 
        'T': 1682546690316, 
        't': -1, 
        'I': 44845260605, 
        'w': True, 
        'm': False, 
        'M': False, 
        'O': 1682546690316, 
        'Z': '0.00000000', 
        'Y': '0.00000000', 
        'Q': '11.73663950', 
        'j': 135934080025, 
        'J': 905101, 
        'W': 1682546690316, 
        'V': 'NONE'
    }
    update_cross_margin_balance:  {'e': 'executionReport', 'E': 1682546690317, 's': 'BTCUSDT', 'c': 'default_09734faff5a743e99b4e868a25b6', 'S': 'BUY', 'o': 'MARKET', 'f': 'GTC', 'q': '0.00041000', 'p': '0.00000000', 'P': '0.00000000', 'F': '0.00000000', 'g': -1, 'C': '', 'x': 'TRADE', 'X': 'FILLED', 'r': 'NONE', 'i': 20931213771, 'l': '0.00041000', 'z': '0.00041000', 'L': '28556.37000000', 'n': '0.00000041', 'N': 'BTC', 'T': 1682546690316, 't': 3096398299, 'I': 44845260606, 'w': False, 'm': False, 'M': True, 'O': 1682546690316, 'Z': '11.70811170', 'Y': '11.70811170', 'Q': '11.73663950', 'j': 135934080025, 'J': 905101, 'W': 1682546690316, 'V': 'NONE'}
    update_cross_margin_balance:  {
        'e': 'outboundAccountPosition', 
        'E': 1682546690317, 
        'u': 1682546690316, 
        'B': [{'a': 'BTC', 'f': '0.00081673', 'l': '0.00000000'}, {'a': 'BNB', 'f': '0.00000000', 'l': '0.00000000'}, {'a': 'USDT', 'f': '0.02852780', 'l': '0.00000000'}]
    }

Trade Sell:
    update_cross_margin_balance:  {'e': 'executionReport', 'E': 1682546748672, 's': 'BTCUSDT', 'c': 'default_b8eba1d16681433396d9d03143a4', 'S': 'SELL', 'o': 'MARKET', 'f': 'GTC', 'q': '0.00081000', 'p': '0.00000000', 'P': '0.00000000', 'F': '0.00000000', 'g': -1, 'C': '', 'x': 'NEW', 'X': 'NEW', 'r': 'NONE', 'i': 20931242525, 'l': '0.00000000', 'z': '0.00000000', 'L': '0.00000000', 'n': '0', 'N': None, 'T': 1682546748671, 't': -1, 'I': 44845322073, 'w': True, 'm': False, 'M': False, 'O': 1682546748671, 'Z': '0.00000000', 'Y': '0.00000000', 'Q': '0.00000000', 'j': 4154612456, 'J': 905102, 'W': 1682546748671, 'V': 'NONE'}
    update_cross_margin_balance:  {'e': 'executionReport', 'E': 1682546748672, 's': 'BTCUSDT', 'c': 'default_b8eba1d16681433396d9d03143a4', 'S': 'SELL', 'o': 'MARKET', 'f': 'GTC', 'q': '0.00081000', 'p': '0.00000000', 'P': '0.00000000', 'F': '0.00000000', 'g': -1, 'C': '', 'x': 'TRADE', 'X': 'FILLED', 'r': 'NONE', 'i': 20931242525, 'l': '0.00081000', 'z': '0.00081000', 'L': '28547.83000000', 'n': '0.02312374', 'N': 'USDT', 'T': 1682546748671, 't': 3096402057, 'I': 44845322074, 'w': False, 'm': False, 'M': True, 'O': 1682546748671, 'Z': '23.12374230', 'Y': '23.12374230', 'Q': '0.00000000', 'j': 4154612456, 'J': 905102, 'W': 1682546748671, 'V': 'NONE'}
    update_cross_margin_balance:  {'e': 'outboundAccountPosition', 'E': 1682546748672, 'u': 1682546748671, 'B': [{'a': 'BTC', 'f': '0.00000673', 'l': '0.00000000'}, {'a': 'BNB', 'f': '0.00000000', 'l': '0.00000000'}, {'a': 'USDT', 'f': '23.12914636', 'l': '0.00000000'}]}
    update_cross_margin_balance:  {'e': 'balanceUpdate', 'E': 1682546748828, 'a': 'USDT', 'd': '-11.73672345', 'T': 1682546748827}
    update_cross_margin_balance:  {'e': 'outboundAccountPosition', 'E': 1682546748828, 'u': 1682546748827, 'B': [{'a': 'USDT', 'f': '11.39242291', 'l': '0.00000000'}]}
```