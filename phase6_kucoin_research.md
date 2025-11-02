# Phase 6: KuCoin Batch API Research

**Date**: 2025-11-02  
**Status**: ✅ **BATCH SUPPORT CONFIRMED**

## Executive Summary

✅ **KuCoin DOES support batch kline fetching!** The existing `kucoin-python` library's `get_kline_data()` method already supports fetching multiple candles in a single API call using start/end time parameters.

## API Capabilities

### Batch Fetching Support
- **Method**: `Client.get_kline_data(symbol, kline_type, start, end)`
- **Max Candles Per Request**: **1500** (better than Binance's 1000!)
- **Documentation**: https://www.kucoin.com/docs/rest/spot-trading/market-data/get-klines
- **Pagination**: "For each query, the system would return at most 1500 pieces of data. To obtain more data, please page the data by time."

### Supported Intervals
✅ All intervals we need are supported:
- `1day` - Daily candles ✅
- `1hour` - Hourly candles ✅  
- `15min` - 15-minute candles ✅

Also supports: 1min, 3min, 5min, 30min, 2hour, 4hour, 6hour, 8hour, 12hour, 1week

### Current Implementation Status

**Existing Code** (`shared_code/kucoin.py`):
```python
def fetch_kucoin_daily_kline(symbol: Symbol, end_date: date | None = None) -> Candle | None:
    """Fetch open, close, high, low prices and volume from KuCoin for the last full day."""
    # Currently fetches ONLY 1 candle even though API supports batching
    klines = client.get_kline_data(
        symbol.kucoin_name,
        kline_type="1day",
        start=start_time_as_int,
        end=end_time_as_int,
    )
    # Returns klines[0] - only first candle
```

**Issue**: Current implementation requests date ranges but **only uses the first result (`klines[0]`)**, ignoring the batch capability!

## Comparison: Binance vs KuCoin

| Feature | Binance | KuCoin | Winner |
|---------|---------|--------|--------|
| Max candles/request | 1000 | **1500** | 🏆 KuCoin |
| Daily candles | ✅ | ✅ | Tie |
| Hourly candles | ✅ | ✅ | Tie |
| 15-min candles | ✅ | ✅ | Tie |
| Batch support | ✅ | ✅ | Tie |
| Current implementation | ✅ Batch | ❌ Individual | 🏆 Binance |

## Implementation Plan

### What Needs to Change

1. **Create batch functions** (similar to Binance):
   - `fetch_kucoin_daily_klines_batch(symbol, start_date, end_date) -> list[Candle]`
   - `fetch_kucoin_hourly_klines_batch(symbol, start_time, end_time) -> list[Candle]`
   - `fetch_kucoin_fifteen_min_klines_batch(symbol, start_time, end_time) -> list[Candle]`

2. **Parse all results** instead of just `klines[0]`:
   ```python
   # OLD:
   return Candle(..., data=klines[0])  # Only first result
   
   # NEW:
   return [Candle(..., data=kline) for kline in klines]  # All results
   ```

3. **Update `price_checker.py`** to use KuCoin batch functions:
   ```python
   if symbol.source_id == SourceID.BINANCE:
       candles = fetch_binance_daily_klines_batch(...)
   elif symbol.source_id == SourceID.KUCOIN:
       candles = fetch_kucoin_daily_klines_batch(...)  # NEW!
   ```

### Implementation Complexity

**Effort Level**: ⭐⭐☆☆☆ (2/5 - Easy)

**Why Easy**:
- ✅ API already supports batch fetching
- ✅ Library method already exists (`get_kline_data`)
- ✅ Current code already uses start/end parameters
- ✅ Can copy pattern from Binance batch functions
- ✅ Only need to parse multiple results instead of `klines[0]`

**Estimated Time**: 2-3 hours
- 1 hour: Implement 3 batch functions
- 1 hour: Update price_checker.py dispatch logic
- 30 min: Testing with KuCoin symbols

## Benefits

### Performance Improvements

For a symbol with KuCoin source updating 30 days of data:

**Before** (current):
- 30 API calls (one per day)
- ~15-30 seconds (with rate limiting delays)

**After** (batch):
- 1 API call (all 30 days at once)
- ~1-2 seconds

**Speed Improvement**: **15-30x faster** ⚡

### Code Consistency

- ✅ Both BINANCE and KUCOIN would use batch fetching
- ✅ Consistent behavior across all sources
- ✅ Simplified `price_checker.py` logic (no special casing)

## Rate Limiting Considerations

### KuCoin API Limits
- **Public Endpoints**: Limited by IP (no API key needed for market data)
- **Weight System**: Each endpoint has a weight/quota
- **Reference**: https://www.kucoin.com/docs-new/rate-limit

### Impact on Our Use Case
- 📉 **Reduces API calls**: 30 calls → 1 call (97% reduction)
- 📉 **Reduces rate limit risk**: Less frequent requests
- ✅ **Stays within limits**: Batch fetching is MORE rate-limit friendly

## Recommendations

### Priority: **HIGH** 🔥

**Reasons**:
1. ✅ Easy to implement (existing API support)
2. ✅ Significant performance improvement (15-30x faster)
3. ✅ Better consistency with Binance implementation
4. ✅ Reduces rate limiting issues
5. ✅ Current code is inefficient (fetches batch but uses only first result)

### Implementation Order

**Phase 6A - Quick Wins** (Recommended to do NOW):
1. ✅ TASK-054: Implement `fetch_kucoin_daily_klines_batch()`
2. ✅ TASK-055: Implement `fetch_kucoin_hourly_klines_batch()`
3. ✅ TASK-056: Implement `fetch_kucoin_fifteen_min_klines_batch()`
4. ✅ TASK-057: Update `price_checker.py` to dispatch to KuCoin batch functions
5. ✅ TASK-058: Test with KuCoin symbols (if any exist in database)
6. ✅ TASK-059: Measure performance improvement

**Phase 6B - Optimization** (Optional, later):
- Handle pagination for >1500 candles (unlikely for our use case)
- Add retry logic specific to KuCoin rate limits
- Optimize concurrent fetching for multiple symbols

## Test Symbols

**Question**: Do we have any KuCoin symbols in the database?

From Phase 5 testing:
```
⚠️  No KUCOIN symbols found - skipping test
```

**Action Required**: 
- Check if KuCoin symbols are needed for this project
- If yes, add KuCoin symbols to database before implementing Phase 6
- If no, Phase 6 can be implemented for future use

## Example Code Structure

### Batch Function (Daily)

```python
def fetch_kucoin_daily_klines_batch(
    symbol: Symbol, 
    start_date: date, 
    end_date: date
) -> list[Candle]:
    """Fetch multiple daily candles from KuCoin in a single API call.
    
    Args:
        symbol: Symbol object with kucoin_name
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
    
    Returns:
        List of Candle objects, sorted by date (oldest first)
        Empty list if no data or error
    
    Note:
        KuCoin API limit: 1500 candles per request
        For larger ranges, multiple API calls are needed
    """
    client = KucoinClient()
    
    start_time_int = int(datetime.combine(start_date, datetime.min.time()).timestamp())
    end_time_int = int(datetime.combine(end_date, datetime.max.time()).timestamp())
    
    try:
        klines = client.get_kline_data(
            symbol.kucoin_name,
            kline_type="1day",
            start=start_time_int,
            end=end_time_int,
        )
        
        if not klines:
            app_logger.warning(f"No kline data from KuCoin for {symbol.symbol_name}")
            return []
        
        candles = []
        for kline in klines:
            # Parse each kline into Candle object
            # kline format: [timestamp, open, close, high, low, volume, turnover]
            candle = Candle(
                end_date=datetime.fromtimestamp(int(kline[0]), UTC),
                source=SourceID.KUCOIN.value,
                symbol=symbol.symbol_name,
                open=float(kline[1]),
                close=float(kline[2]),
                high=float(kline[3]),
                low=float(kline[4]),
                last=float(kline[2]),
                volume=float(kline[5]),
                volume_quote=float(kline[6]),
            )
            candles.append(candle)
        
        app_logger.info(f"✓ Fetched {len(candles)} daily candles for {symbol.symbol_name} from KuCoin in single API call")
        return sorted(candles, key=lambda c: c.end_date)
        
    except Exception as e:
        app_logger.error(f"Error fetching KuCoin daily batch for {symbol.symbol_name}: {e!s}")
        return []
```

## Conclusion

✅ **Phase 6 is HIGHLY RECOMMENDED and EASY to implement**

KuCoin's API already supports batch fetching with excellent limits (1500 candles). Our current code is inefficient - it fetches batches but only uses the first result. Implementing KuCoin batch functions will:

1. Make KuCoin fetching **15-30x faster**
2. Achieve **consistency** with Binance implementation
3. **Reduce API calls by 97%** (30 calls → 1 call)
4. Require only **2-3 hours of development time**

**Next Step**: Implement Phase 6A tasks to add KuCoin batch support.
