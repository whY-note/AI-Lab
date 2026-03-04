import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import cm

# 数据预处理
df = pd.read_csv("MLP_data.csv")
df_choose = df.iloc[:, 2:]

X_data = df_choose.iloc[:, :2]
y_data = df_choose.iloc[:, 2:]

# 标准化
X_mean, X_std = np.mean(X_data, axis=0), np.std(X_data, axis=0)
y_mean, y_std = np.mean(y_data, axis=0), np.std(y_data, axis=0)

X_processed = (X_data - X_mean) / X_std
y_processed = (y_data - y_mean) / y_std

X = np.array(X_processed)
y = np.array(y_processed)

# 划分训练集、验证集和测试集
indices = np.random.permutation(len(X))
train_size = int(0.7 * len(X))
validate_size=int(0.15 * len(X))

X_train, y_train = X[indices[:train_size]], y[indices[:train_size]]
X_validate,y_validate=X[indices[train_size:train_size+validate_size]],y[indices[train_size:train_size+validate_size]]
X_test, y_test = X[indices[train_size+validate_size:]], y[indices[train_size+validate_size:]]

np.random.seed(10)

# 网络参数
input_size = 2
hidden_size = 16
output_size = 1

class MLP:
    def __init__(self,learning_rate):
        self.learning_rate=learning_rate
        self.b1 = np.zeros(hidden_size)
        self.W1 = np.random.rand(input_size, hidden_size)
        self.b2 = np.zeros(output_size)
        self.W2 = np.random.rand(hidden_size, output_size)
        self.best_params={}

        # 动量优化
        self.momentum_W1 = np.zeros_like(self.W1)
        self.momentum_b1 = np.zeros_like(self.b1)
        self.momentum_W2 = np.zeros_like(self.W2)
        self.momentum_b2 = np.zeros_like(self.b2)
        self.beta = 0.9

    def sigmod(self,X):
        return 1 / (1 + np.exp(-X))

    def forward(self, X):
        # 前向传播
        self.h_in = X @ self.W1 + self.b1
        self.h_out = self.sigmod(self.h_in)
        self.y_in = self.h_out @ self.W2 + self.b2
        self.y_out = self.y_in  # 线性输出

        return self.y_out

    def loss(self, y_pred, y):
        return 0.5 * np.mean((y_pred - y) ** 2)

    def backward(self,X,y):
        m=X.shape[0]

        # 输出层梯度（线性激活）
        dL_dy_out = (self.y_out - y)
        dW2=(self.h_out.T@dL_dy_out)/m
        db2=np.sum(dL_dy_out,axis=0)/m

        # 隐藏层梯度
        dL_dh_out = dL_dy_out @ self.W2.T
        dL_dh_in = dL_dh_out * self.h_out * (1 - self.h_out)
        dW1 = (X.T @ dL_dh_in) / m
        db1 = np.sum(dL_dh_in, axis=0) / m

        # 动量式更新
        # 动量更新
        self.momentum_W2 = self.beta * self.momentum_W2 + (1 - self.beta) * dW2
        self.momentum_b2 = self.beta * self.momentum_b2 + (1 - self.beta) * db2
        self.momentum_W1 = self.beta * self.momentum_W1 + (1 - self.beta) * dW1
        self.momentum_b1 = self.beta * self.momentum_b1 + (1 - self.beta) * db1

        # 参数更新
        self.W2 -= self.learning_rate * self.momentum_W2
        self.b2 -= self.learning_rate * self.momentum_b2
        self.W1 -= self.learning_rate * self.momentum_W1
        self.b1 -= self.learning_rate * self.momentum_b1

    def train(self,X_train,y_train,X_validate,y_validate,epochs=100, batch_size=32,patience_rate=0.5):

        all_train_loss=[]
        all_validate_loss=[]
        best_loss = np.inf
        no_improve = 0
        patience_size=patience_rate*epochs

        for epoch in range(epochs):
            # 训练
            permutation = np.random.permutation(len(X_train))
            X_shuffled = X_train[permutation]
            y_shuffled = y_train[permutation]
            for i in range(0, len(X_train), batch_size):
                batch_indices = permutation[i:i + batch_size]
                X_batch = X_shuffled[batch_indices]
                y_batch = y_shuffled[batch_indices]

                self.forward(X_batch)
                self.backward(X_batch,y_batch)

            y_train_pred=self.forward(X_train)
            train_loss=self.loss(y_train_pred,y_train)
            all_train_loss.append(train_loss)

            y_validate_pred=self.forward(X_validate)
            validate_loss=self.loss(y_validate_pred,y_validate)
            all_validate_loss.append(validate_loss)

            # 早停判断
            if validate_loss < best_loss:
                best_loss = validate_loss
                no_improve = 0
                # 保存最佳参数
                self.best_params['W1']=self.W1.copy()
                self.best_params['b1']= self.b1.copy()
                self.best_params['W2']= self.W2.copy()
                self.best_params['b2']=self.b2.copy()

            else:
                no_improve += 1
                if no_improve >= patience_size:
                    print(f"Early stopping at epoch {epoch}")

                    self.W1 = self.best_params['W1']
                    self.b1 = self.best_params['b1']
                    self.W2 = self.best_params['W2']
                    self.b2 = self.best_params['b2']
                    break

            print(f"Epoch {epoch + 1}/{epochs} | Train Loss: {train_loss:.4f} | Val Loss: {validate_loss:.4f}")

        return all_train_loss,all_validate_loss

    def predict(self,X):
        return self.forward(X)

def plot_3d_surface(ax, model, X):
    # 生成网格数据
    x_min, x_max = X[:, 0].min(), X[:, 0].max()
    y_min, y_max = X[:, 1].min(), X[:, 1].max()
    xx, yy = np.meshgrid(np.linspace(x_min, x_max, 50),
                         np.linspace(y_min, y_max, 50))

    # 预测网格点
    grid = np.c_[xx.ravel(), yy.ravel()]
    zz = model.predict(grid).reshape(xx.shape)

    # 绘制曲面
    surf = ax.plot_surface(xx, yy, zz, cmap=cm.coolwarm,
                           alpha=0.6, linewidth=0, antialiased=True)
    return surf


if __name__ == "__main__":
    # 初始化模型
    mlp = MLP(learning_rate=0.01)

    # 训练模型
    all_train_loss,all_validate_loss = mlp.train(X_train, y_train,X_validate,y_validate,
                                                 epochs=1000,
                                                 batch_size=32,
                                                 patience_rate=0.1
                                                 )

    y_pred=mlp.predict(X_test)
    y_pred=y_pred*np.array(y_std)+np.array(y_mean)

    y_test_real=y_test*np.array(y_std)+np.array(y_mean)

    predict_loss=np.sqrt(np.average((y_pred-y_test_real)**2))

    print("y_pred:\n",y_pred)
    print("predict_loss:\n",predict_loss)

    # 绘制损失曲线
    fig=plt.figure(figsize=(12, 6))
    ax1=fig.add_subplot(121)
    ax1.plot(all_train_loss)
    ax1.set_title("Training Loss")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("Loss")
    plt.grid(True)

    ax2 = fig.add_subplot(122)
    ax2.plot(all_validate_loss)
    ax2.set_title("Validating Loss")
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("Loss")
    plt.grid(True)
    plt.show()

    fig = plt.figure(figsize=(12, 6))

    # 训练集子图
    ax1 = fig.add_subplot(121, projection='3d')
    ax1.scatter(X_train[:, 0], X_train[:, 1], y_train, c='b', label='True', s=10)
    plot_3d_surface(ax1, mlp, X_train)
    ax1.set_xlabel("Housing Age (scaled)")
    ax1.set_ylabel("Income (scaled)")
    ax1.set_zlabel("Price (scaled)")
    ax1.set_title("Training Set")

    # 测试集子图
    ax2 = fig.add_subplot(122, projection='3d')
    ax2.scatter(X_test[:, 0], X_test[:, 1], y_test, c='r', label='True', s=10)
    plot_3d_surface(ax2, mlp, X_test)
    ax2.set_xlabel("Housing Age (scaled)")
    ax2.set_ylabel("Income (scaled)")
    ax2.set_zlabel("Price (scaled)")
    ax2.set_title("Test Set")

    plt.tight_layout()
    plt.show()