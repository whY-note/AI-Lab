import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import cm  #导入cm模块

df=pd.read_csv("MLP_data.csv")
df_choose=df.iloc[:,2:]
print(df_choose)

def scalar(data):
    '''标准化'''
    mean=np.mean(data,axis=0)
    std=np.std(data,axis=0)
    return (data-mean)/std,mean,std

df_choose_processed,mean,std=scalar(df_choose)
X=np.array(df_choose_processed.iloc[:,:2])
y=np.array(df_choose_processed.iloc[:,2:])


# 划分测试集和训练集
indices = np.random.permutation(len(X)) # 打乱 0~len(X)的数
train_size = int(0.8 * len(X))
X_train, y_train = X[indices[:train_size]], y[indices[:train_size]]
X_test, y_test = X[indices[train_size:]], y[indices[train_size:]]


np.random.seed(10)

input_size = 2
hidden_size = 4
output_size = 1

class MLP:
    def __init__(self,X_train,y_train,learning_rate):
        self.X_train=X_train
        self.y_trains=y_train

        self.b1 = np.zeros(hidden_size)
        self.W1 = np.random.rand(input_size, hidden_size)
        self.b2 = np.zeros(output_size)
        self.W2 = np.random.rand(hidden_size, output_size)
        self.learning_rate=learning_rate
    def sigmod(self,X):
        return 1/(1+np.exp(-X))

    def forward(self,X):
        h_in=X@self.W1+self.b1
        h_out=self.sigmod(h_in)
        y_in=h_out@self.W2+self.b2
        y_out=self.sigmod(y_in)
        return h_out,y_out

    def loss(self,y_pred,y):
        return 1/2*(y_pred-y)**2

    def backward(self,X,h_out,y_pred,y):
        g2=0

        delta_W2=np.zeros((hidden_size,output_size))

        g2=(y_pred-y)*y_pred*(1-y_pred)

        delta_b2=-self.learning_rate*g2

        for i in range(hidden_size):
            delta_W2[i]=-self.learning_rate*g2*h_out[i]

        g1=np.zeros(hidden_size)
        # delta_b1=np.zeros(hidden_size)
        delta_W1=np.zeros((input_size,hidden_size))

        for i in range(hidden_size):
            g1[i]=g2*self.W2[i]
            g1[i]=g1[i]*h_out[i]*(1-h_out[i])

        delta_b1=-self.learning_rate*g1

        for l in range(input_size):
            for i in range(hidden_size):
                delta_W1[l][i]=-self.learning_rate*g1[i]*X[l]

        # update
        self.b1=self.b1+delta_b1
        self.W1=self.W1+delta_W1
        self.b2=self.b2+delta_b2
        self.W2=self.W2+delta_W2

    # def backward(self,X,h_out,y_pred,y):
    #     g2=np.zeros(output_size)
    #     # delta_b2=np.zeros(output_size)
    #     delta_W2=np.zeros((hidden_size,output_size))
    #     for j in range(output_size):
    #         g2[j]=(y_pred[j]-y[j])*y_pred[j]*(1-y_pred[j])
    #
    #     delta_b2=-self.learning_rate*g2
    #
    #     for i in range(hidden_size):
    #         for j in range(output_size):
    #             delta_W2[i][j]=-self.learning_rate*g2[j]*h_out[i]
    #
    #     g1=np.zeros(hidden_size)
    #     # delta_b1=np.zeros(hidden_size)
    #     delta_W1=np.zeros((input_size,hidden_size))
    #
    #     for i in range(hidden_size):
    #         for j in range(output_size):
    #             g1[i]+=g2[j]*self.W2[i][j]
    #         g1[i]=g1[i]*h_out[i]*(1-h_out[i])
    #
    #     delta_b1=-self.learning_rate*g1
    #
    #     for l in range(input_size):
    #         for i in range(hidden_size):
    #             delta_W1[l][i]=-self.learning_rate*g1[i]*X[l]
    #
    #     # update
    #     self.b1=self.b1+delta_b1
    #     self.W1=self.W1+delta_W1
    #     self.b2=self.b2+delta_b2
    #     self.W2=self.W2+delta_W2

    def solve(self,iter):
        E_list=[]
        sample_size=self.X_train.shape[0]
        for i in range(iter):
            for k in range(sample_size):
                h_out,y_out=self.forward(self.X_train[k])
                Ek=self.loss(y_out,y_train[k])

                E_list.append(Ek)
                self.backward(self.X_train[k],h_out,y_out,y_train[k])
        return E_list

    def predict(self,X_test):
        y_pred=np.zeros((X_test.shape[0],output_size))
        for i in range(X_test.shape[0]):
            _,y_out=self.forward(X_test[i,:])
            y_pred[i,:]=y_out
        return y_pred


X=np.array([[1,2],[1,2],[1,2]])
# print("y\n",forward(X))

if __name__=="__main__":
    mlp=MLP(X_train,y_train,0.01)
    E_list=mlp.solve(iter=10)
    print(E_list)
    plt.plot(E_list)
    plt.show()

    fig = plt.figure(figsize=(9, 6))
    ax1 = fig.add_subplot(111, projection='3d')
    ax1.scatter(X_train[:, 0], X_train[:, 1], y_train, c=y_train, cmap='viridis', s=10)
    # ax1.set_xlabel('Housing Age')
    # ax1.set_ylabel('Income (100k)')
    # ax1.set_zlabel('Price')
    # ax1.set_title('Housing Price Distribution')

    plt.show()

    y_pred=mlp.predict(X_test)
    fig = plt.figure(figsize=(9, 6))
    ax1 = fig.add_subplot(111, projection='3d')
    ax1.scatter(X_test[:, 0], X_test[:, 1], y_train, c=y_test, cmap='viridis', s=10)
    # ax1.set_xlabel('Housing Age')
    # ax1.set_ylabel('Income (100k)')
    # ax1.set_zlabel('Price')
    # ax1.set_title('Housing Price Distribution')

    plt.show()
