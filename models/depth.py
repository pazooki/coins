import numpy as np

from decimal import Decimal
from sklearn.cluster import KMeans

def depth_kmeans(depth, n_clusters_limit=10):
    # preprocess the depth data
    bids = np.array(depth['bids'], dtype=Decimal)
    asks = np.array(depth['asks'], dtype=Decimal)
    # return asks, bids

    bids_n_clusters = min([len(bids), n_clusters_limit])
    asks_n_clusters = min([len(asks), n_clusters_limit])

    try:

        # apply K-Means clustering on bids and asks data separately
        kmeans_bids = KMeans(n_init='auto', n_clusters=bids_n_clusters, random_state=0).fit(bids.reshape(-1, 1))
        kmeans_asks = KMeans(n_init='auto', n_clusters=asks_n_clusters, random_state=0).fit(asks.reshape(-1, 1))

        # get the centroids of the clusters
        resistance_bids_centroids = kmeans_bids.cluster_centers_
        support_asks_centroids = kmeans_asks.cluster_centers_
    except Exception as e:
        print('FAILED # depth_kmeans received empty list: ', e)
        return [], []

    return support_asks_centroids, resistance_bids_centroids

'''
# plot the resistance and support lines
plt.scatter(bids_centroids[:, 0], bids_centroids[:, 1], color='red', label='Resistance')
plt.scatter(asks_centroids[:, 0], asks_centroids[:, 1], color='green', label='Support')
plt.xlabel('Price')
plt.ylabel('Volume')
plt.legend()
plt.show()

display(list(zip(asks_centroids[:, 0], asks_centroids[:, 1])))
'''