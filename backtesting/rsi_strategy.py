import pandas as pd

# Load and prepare data (replace with your CSV path)
df = pd.read_csv(r"C:\Users\5028lukgr\Downloads\BitcoinRSI.csv")
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)


# Generate trading signals
df['signal'] = (df['rsi'] <= 35) & (df['rsi'].shift(1) > 35)

trades = []
active_trade = False

for i in range(len(df)):
    if not active_trade and df.loc[i, 'signal'] and (i + 1 < len(df)):
        active_trade = True
        entry_date = df.loc[i+1, 'date']
        entry_price = df.loc[i+1, 'open']
        print(f"Started position on date {entry_date} with entry price {entry_price}")
        tp_price = entry_price * 1.1
        sl_price = entry_price * 0.9
        outcome = None
        days_taken = 0
        
        for j in range(i+1, len(df)):
            current_high = df.loc[j, 'high']
            current_low = df.loc[j, 'low']
            current_date = df.loc[j, 'date']
            
            if current_high >= tp_price:
                outcome = 'TP'
                days_taken = (current_date - entry_date).days
                print(f"Closed position ❤️ at date {current_date} with price {current_high}")
                break
            elif current_low <= sl_price:
                outcome = 'SL'
                days_taken = (current_date - entry_date).days
                print(f"Closed position 💀 at date {current_date} with price {current_low}")
                break
        
        if outcome:
            trades.append({
                'outcome': outcome,
                'days': days_taken
            })
        
        active_trade = False

# Analyze results
results_df = pd.DataFrame(trades)
summary = results_df.groupby('outcome').agg(
    count=('outcome', 'size'),
    avg_days=('days', 'mean')
)

print("Backtest Results:")
print(f"Total trades: {len(results_df)}")
print(f"Take Profit hits: {summary.loc['TP', 'count']}" if 'TP' in summary.index else "Take Profit hits: 0")
print(f"Stop Loss hits: {summary.loc['SL', 'count']}" if 'SL' in summary.index else "Stop Loss hits: 0")
print(f"Average days to TP: {summary.loc['TP', 'avg_days']:.1f}" if 'TP' in summary.index else "")
print(f"Average days to SL: {summary.loc['SL', 'avg_days']:.1f}" if 'SL' in summary.index else "")
