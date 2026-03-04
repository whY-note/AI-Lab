import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans,kmeans_plusplus
plt.rcParams['font.family'] = ['sans-serif']
plt.rcParams['font.sans-serif'] = ['SimHei']  # 散点图标签可以显示中文

k_value=3
df=pd.read_csv("data.csv")
print(df)
X=np.array(df.iloc[:,:2])

# 开始kmeans聚类
kmeans = KMeans(n_clusters=k_value)  # 设定k值
clusters = kmeans.fit_predict(X)  # 训练及预测
print("分类结果:",clusters)  # 分类结果

point_color=clusters
# 绘图
plt.scatter(X[:,0],X[:,1],c=point_color, marker='o')
# 画出簇中心
plt.scatter(kmeans.cluster_centers_[:,0],kmeans.cluster_centers_[:,1],
            marker='^',c='r',
            s=100,linewidth=2)
print("簇中心:\n",kmeans.cluster_centers_)
plt.xlabel('x')
plt.ylabel('y')
plt.title(f"k={k_value}")
plt.show()