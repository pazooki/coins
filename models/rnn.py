import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout

# load data
df = pd.read_csv(
    '/home/mehrdadpazooki/TheVault/trading/code/darksteps/models/data/XBTUSD_1.csv', 
    names=['Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Trades'], 
    header=None,
    parse_dates=True
)
df = df.dropna()

# scale data
scaler = MinMaxScaler()
df['Close'] = scaler.fit_transform(np.array(df['Close']).reshape(-1, 1))

# convert data to expected data type
df = df.astype('float32')

# create train/test split
train_size = int(len(df) * 0.8)
train_data = df[:train_size].copy()
test_data = df[train_size:].copy()

# create sequences
def create_sequences(data, seq_length):
    X = []
    y = []
    for i in range(seq_length, len(data)):
        X.append(data[i-seq_length:i, 0])
        y.append(data[i, 0])
    return np.array(X), np.array(y)

seq_length = 60 # number of time steps to look back
X_train, y_train = create_sequences(train_data.values, seq_length)
X_test, y_test = create_sequences(test_data.values, seq_length)

# reshape input data for LSTM layer
X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))
X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))

# create RNN model
model = Sequential()
model.add(LSTM(units=50, return_sequences=True, input_shape=(X_train.shape[1], 1)))
model.add(Dropout(0.2))
model.add(LSTM(units=50, return_sequences=True))
model.add(Dropout(0.2))
model.add(LSTM(units=50))
model.add(Dropout(0.2))
model.add(Dense(units=1))

# compile model
model.compile(optimizer='adam', loss='mean_squared_error')

# train model
model.fit(X_train, y_train, epochs=50, batch_size=32)

with open('/home/mehrdadpazooki/TheVault/trading/code/darksteps/models/rrn_model.pkl', 'wb') as f:
    pickle.dump(model, f)

# make predictions
y_pred = model.predict(X_test)

# invert scaling
y_pred = scaler.inverse_transform(y_pred)
y_test = scaler.inverse_transform(y_test.reshape(-1, 1))

# plot results
plt.plot(y_test, label='actual')
plt.plot(y_pred, label='predicted')
plt.legend()
plt.show()
