hearthbeat 'status_update' output:
{
  "status": "healthy",
  "connected": true,
  "provider": "Test",
  "market_status": "CLOSED",
  "timestamp": "2025-07-29T20:46:26.371329",
  "avg_response": 1.593017578125
}


'stock_data' output:
{
  "highs": [
    {
      "price": 145.59,
      "event_id": "1753824856.989617_bd6a9ccf",
      "direction": "up",
      "rel_volume": 0.0,
      "percent_change": 12.80799628079963,
      "volume": 1392277,
      "count_down": 0,
      "vwap_divergence": 13.255542590431732,
      "type": "high",
      "reversal": false,
      "time": "16:34:16",
      "vwap": 128.55,
      "count": 3,
      "label": "HIGH #3",
      "ticker": "AMZN",
      "count_up": 3,
      "trend_flag": null,
      "surge_flag": null,
      "significance_score": 25.0,
      "last_update": 1753824856.988616,
      "session_high": 145.59,
      "reversal_info": null,
      "session_low": 129.06
    }
  ],
  "lows": [
    {
      "price": 77.23,
      "event_id": "1753824857.487835_7c547a1f",
      "direction": "down",
      "rel_volume": 0.8955534223503685,
      "percent_change": -5.064535955746761,
      "volume": 413472,
      "count_down": 1,
      "vwap_divergence": -6.906943105110885,
      "type": "low",
      "reversal": true,
      "time": "16:34:17",
      "vwap": 82.96,
      "count": 3,
      "label": " LOW #1",
      "ticker": "AVGO",
      "count_up": 2,
      "trend_flag": null,
      "surge_flag": "down",
      "significance_score": 36.194417779379606,
      "last_update": 1753824857.483833,
      "session_high": 91.36,
      "reversal_info": {
        "type": "V-top",
        "time_span": 9.06024169921875,
        "is_rapid": true,
        "previous_type": "high",
        "previous_price": 91.36
      },
      "session_low": 77.23
    }
  ],
  "trending": {
    "up": [
      {
        "price": 99.58,
        "rel_volume": 0.0,
        "reversal": "down-now-up",
        "count": 7,
        "direction": "↑",
        "time": "13:06:24",
        "type": "trend",
        "volume": 1035033,
        "ticker": "GOOG",
        "vwap": 141.08,
        "percent_change": 7.817236899090514,
        "label": "GOOG TREND ↑ weak",
        "count_down": 3,
        "event_id": "1753639584.813734_62b0415d",
        "vwap_divergence": -29.41593422171818,
        "count_up": 4,
        "last_trend_update": 1753639584.8137343,
        "trend_age": 0,
        "trend_medium_score": 0.3742552157975137,
        "trend_strength": "weak",
        "trend_long_score": 0.3742552157975137,
        "trend_vwap_position": "below",
        "trend_short_score": 0.3742552157975137,
        "trend_score": 0.3742552157975137
      }
    ],
    "down": [
      {
        "time": "14:26:40",
        "price": 126.07,
        "rel_volume": 0.0,
        "count": 4,
        "type": "surge",
        "direction": "down",
        "percent_change": -15.981339553482183,
        "reversal": false,
        "volume": 1744115,
        "vwap": 156.39,
        "label": "SURGE ↓ 16.0% price_and_volume",
        "count_down": 3,
        "event_id": "1753817200.332348_31da6734",
        "ticker": "GOOG",
        "vwap_divergence": -19.387428863738087,
        "count_up": 1,
        "strength": "strong",
        "surge_age": 0.36154770851135254,
        "description": "Surge down price/and/volume (16.0%)",
        "event_key": "GOOG_down_1753817200.3323476",
        "trigger_type": "price_and_volume",
        "magnitude": -15.981339553482183,
        "score": 100,
        "daily_surge_count": 4,
        "volume_multiplier": 1.9810893410109114,
        "expiration": 1753817230.3323476,
        "last_surge_timestamp": 1753817200.3323476
      }
    ]
  },
  "surging": {
    "up": [
      {
        "price": 145.59,
        "event_id": "1753824856.990617_e3ac7c3d",
        "direction": "up",
        "rel_volume": 0.0,
        "percent_change": 8.004451038575661,
        "volume": 1392277,
        "count_down": 0,
        "vwap_divergence": 13.255542590431732,
        "type": "surge",
        "reversal": false,
        "time": "16:34:16",
        "vwap": 128.55,
        "count": 1,
        "label": "SURGE ↑ 8.0% price",
        "ticker": "AMZN",
        "count_up": 1,
        "trigger_type": "price",
        "expiration": 1753824886.9906166,
        "daily_surge_count": 1,
        "event_key": "AMZN_up_1753824856.9906166",
        "surge_age": 0.2775874137878418,
        "volume_multiplier": 0.9355848308168174,
        "last_surge_timestamp": 1753824856.9906166,
        "score": 50,
        "description": "Surge up price (8.0%)",
        "strength": "weak",
        "magnitude": 8.004451038575661
      }
    ],
    "down": [
      {
        "price": 25.23,
        "rel_volume": 0.0,
        "reversal": "up-now-down",
        "count": 32,
        "direction": "↓",
        "time": "13:06:27",
        "type": "surge",
        "volume": 1032318,
        "ticker": "JPM",
        "vwap": 51.49,
        "percent_change": -12.909906800138069,
        "label": "JPM SURGE ↓ 12.9% price_and_volume",
        "count_down": 17,
        "event_id": "1753639587.846305_47c909d1",
        "vwap_divergence": -51.00019421246844,
        "count_up": 15,
        "description": "Surge down price/and/volume (12.9%)",
        "last_surge_timestamp": 1753639587.8463051,
        "volume_multiplier": 1.5811961085278317,
        "strength": "strong",
        "trigger_type": "price_and_volume",
        "score": 100,
        "magnitude": -12.909906800138069,
        "surge_age": 0.0409848690032959,
        "expiration": 1753639617.8458025,
        "event_key": "JPM_↓_1753639587.8463051",
        "daily_surge_count": 32
      }
    ]
  },
  "activity": {
    "total_highs": 46,
    "total_lows": 53,
    "activity_level": "Extreme",
    "activity_ratio": {
      "calculation_method": "ticks_per_minute",
      "current_rate": 678,
      "threshold_low": 30,
      "threshold_medium": 60,
      "threshold_high": 120,
      "threshold_very_high": 240
    },
    "ticks_10sec": 112,
    "ticks_30sec": 336,
    "ticks_60sec": 678,
    "ticks_300sec": 1014
  }
}