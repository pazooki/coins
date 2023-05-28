import pandas as pd
import numpy as np
import pickle
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# Load the dataset
df = pd.read_csv('./data/XBTUSD_1.csv', 
                 names=['Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Trades'], 
                 header=None,
                 parse_dates=True)

df.dropna(inplace=True)
df.set_index('Time', inplace=True, drop=False)
# df = df[-1000000:]

# Preprocessing
scaler = MinMaxScaler()
df['Close'] = scaler.fit_transform(df['Close'].values.reshape(-1, 1))

# Splitting into training and testing data
train_data = df.iloc[:int(0.8 * len(df)), :]
test_data = df.iloc[int(0.8 * len(df)):, :]

# Convert the dataset into sequences
def create_sequences(data, sequence_length):
    X = []
    y = []
    for i in range(len(data) - sequence_length - 1):
        X.append(data[i:i + sequence_length])
        y.append(data[i + sequence_length])
    return np.array(X), np.array(y)

sequence_length = 100  # Adjust this value as per your preference
X_train, y_train = create_sequences(train_data['Close'].values, sequence_length)
X_test, y_test = create_sequences(test_data['Close'].values, sequence_length)

# Reshape input data to fit the LSTM model
X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))
X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))

# Build and train the LSTM model
model = Sequential()
model.add(LSTM(units=50, return_sequences=True, input_shape=(sequence_length, 1)))
model.add(LSTM(units=50))
model.add(Dense(units=1))
model.compile(optimizer='adam', loss='mean_squared_error')
model.fit(X_train, y_train, epochs=50, batch_size=64)

# Predict on the test data
predicted_prices = model.predict(X_test)

# Rescale the predicted prices
predicted_prices = scaler.inverse_transform(predicted_prices)

# Compare the predicted prices with the actual prices
comparison_df = pd.DataFrame({'Actual': scaler.inverse_transform(y_test.reshape(-1, 1)).flatten(), 'Predicted': predicted_prices.flatten()})

print(comparison_df)

with open('./BTC_pattern_matching_model.pkl', 'wb') as f:
    print('Storing BTC_pattern_matching_model.pkl')
    pickle.dump(model, f)