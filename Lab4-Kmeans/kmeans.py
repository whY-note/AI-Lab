import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = ['sans-serif']
plt.rcParams['font.sans-serif'] = ['SimHei']  # 散点图标签可以显示中文


def cal_eucli_distance(point1,point2):
    return np.sqrt(np.sum(np.power((point1-point2),2)))

def clustering(data,cluster_points,k):
    belong_to_cluster=[]
    for data_point in data:
        min_dist=np.inf
        min_cluster=0
        for i in range(k):
            dist=cal_eucli_distance(data_point,cluster_points[i,:])
            if(dist<min_dist):
                min_dist=dist
                min_cluster=i
        belong_to_cluster.append(min_cluster)
    return belong_to_cluster

def Kmeans_solve(data,k,data_dim=2):
    cluster_points=np.random.rand(k,data_dim)
    while True:
        belong_to_cluster=clustering(data,cluster_points,k)
        new_cluster_points=np.zeros((k,data_dim))
        cluster_sum=np.zeros((k,data_dim))
        num_in_cluster=np.ones(k)

        for i in range(len(data)):
            belong=belong_to_cluster[i]
            cluster_sum[belong,:]+=data[i,:]
            num_in_cluster[belong]+=1
        for kk in range(k):
            new_cluster_points[kk,:]=cluster_sum[kk,:]/num_in_cluster[kk]
        if (new_cluster_points==cluster_points).all():
            return belong_to_cluster,new_cluster_points
        cluster_points=new_cluster_points



if __name__=="__main__":
    '''1.首先创建一个明显分为2类20*2的例子
    （每一列为一个变量共2个变量，每一行为一个样本共20个样本）：'''
    np.random.seed(10)
    c1x = np.random.uniform(0.5, 1.5, (1, 10))
    c1y = np.random.uniform(0.5, 1.5, (1, 10))
    c2x = np.random.uniform(3.5, 4.5, (1, 10))
    c2y = np.random.uniform(3.5, 4.5, (1, 10))
    x = np.hstack((c1x, c2x))
    y = np.hstack((c2y, c2y))
    data = np.vstack((x, y)).T
    print(data)
    k_value = 3


    belong_to_cluster,cluster_centers_=Kmeans_solve(data,k_value,2)
    
    print(belong_to_cluster)
    print(cluster_centers_)

    point_color = belong_to_cluster
    # 绘图
    plt.scatter(data[:, 0], data[:, 1],c=point_color, marker='o')
    # 画出簇中心
    plt.scatter(cluster_centers_[:, 0], cluster_centers_[:, 1],
                marker='^', c='r',
                s=100, linewidth=2)
    print("簇中心:\n", cluster_centers_)
    plt.xlabel('x')
    plt.ylabel('y')
    plt.title(f"k={k_value}")
    plt.show()
