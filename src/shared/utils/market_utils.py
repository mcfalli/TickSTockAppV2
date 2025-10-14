'''

def get_market_context(timestamp, market_status):
    """Get detailed market context for any timestamp"""
    
    if market_status != "REGULAR":
        return {
            'status': market_status,
            'period': market_status.lower(),
            'minutes_into_session': 0,
            'volatility_multiplier': 3.0 if market_status in ["PRE", "POST"] else 1.0
        }
    
    # Calculate minutes since 9:30 AM ET
    market_open = timestamp.replace(hour=9, minute=30, second=0)
    minutes_since_open = (timestamp - market_open).total_seconds() / 60
    
    # Determine period
    if minutes_since_open < 30:
        period = "opening_30"
        volatility_multiplier = 2.0
    elif minutes_since_open < 60:
        period = "opening_hour"
        volatility_multiplier = 1.5
    elif 120 < minutes_since_open < 240:
        period = "midday"
        volatility_multiplier = 0.8
    elif minutes_since_open > 360:
        period = "closing_30"
        volatility_multiplier = 1.5
    else:
        period = "regular"
        volatility_multiplier = 1.0
    
    return {
        'status': market_status,
        'period': period,
        'minutes_into_session': minutes_since_open,
        'volatility_multiplier': volatility_multiplier
    }
    
'''
