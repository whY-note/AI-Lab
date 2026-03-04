import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import matplotlib.pyplot as plt
import numpy as np
import os

# 基础参数
epochs=30  # 迭代次数
batch_size = 16  # 批处理规模
learning_rate=0.001  # 学习率

out1_size=16
out2_size=32
out3_size=64

class CNN(nn.Module):
    def __init__(self,num_classes):
        super().__init__()
        self.conv1=nn.Sequential(
            nn.Conv2d(in_channels=3,out_channels=out1_size,kernel_size=3,stride=1,padding=1),
            nn.BatchNorm2d(out1_size),
            nn.ReLU(),
            nn.MaxPool2d(2)
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(in_channels=out1_size, out_channels=out2_size, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(out2_size),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.conv3=nn.Sequential(
            nn.Conv2d(in_channels=out2_size, out_channels=out3_size, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(out3_size),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.AdaptiveAvgPool2d((10, 10))
        )

        self.classifier=nn.Sequential(
            nn.Flatten(),

            nn.Linear(out3_size*10*10,512),
            nn.ReLU(),
            nn.Dropout(0.3),  # 随机丢弃30%的神经元，防止过拟合
            nn.Linear(512, num_classes) # output
        )

    def forward(self,x):
        x=self.conv1(x)
        x=self.conv2(x)
        x=self.conv3(x)

        x=self.classifier(x)
        return x

def main():
    '''----------------------------------导入数据----------------------------------'''
    # 数据预处理
    # transform = transforms.Compose([
    #     transforms.Resize((224, 224)),
    #     transforms.ToTensor(),
    #     transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])  # RGB三个通道归一化，处理后 图像tensor 会在 [-1, 1] 区间内
    # ])
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.5] * 3, [0.5] * 3)
    ])

    # 数据集路径
    base_path = r'D:\Python_code\作业\HW7\cnn图片'  # 我的路径
    train_path = os.path.join(base_path, 'train')  # 训练集
    test_path = os.path.join(base_path, 'test')  # 测试集

    # 加载数据集
    train_dataset = datasets.ImageFolder(train_path, transform=transform)
    test_dataset = datasets.ImageFolder(test_path, transform=transform)
    print(f"训练集类别: {train_dataset.class_to_idx}")
    print(f"测试集类别: {test_dataset.class_to_idx}")

    # 创建数据加载器
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=2
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0
    )

    '''--------------------------------初始化模型--------------------------------'''
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = CNN(num_classes=len(train_dataset.classes)).to(device)
    criterion = nn.CrossEntropyLoss()  # 交叉熵
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    train_losses = []
    train_accuracies = []
    test_accuracies = []


    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

    for epoch in range(epochs):
        model.train()
        train_loss=0
        # 训练阶段
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * inputs.size(0)

        epoch_loss = train_loss/len(train_dataset)
        train_losses.append(epoch_loss)

        # 计算训练集准确率
        model.eval()
        train_correct = 0
        train_total = 0
        with torch.no_grad():
            for inputs, labels in train_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                _, predicted = torch.max(outputs.data, 1)
                train_total += labels.size(0)
                train_correct += (predicted == labels).sum().item()
        train_acc = train_correct / train_total
        train_accuracies.append(train_acc)

        # 计算测试集准确率
        test_correct = 0
        test_total = 0
        with torch.no_grad():
            for inputs, labels in test_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                _, predicted = torch.max(outputs.data, 1)
                test_total += labels.size(0)
                test_correct += (predicted == labels).sum().item()
        test_acc = test_correct / test_total
        test_accuracies.append(test_acc)

        print(f'Epoch [{epoch + 1}/{epochs}] Loss: {epoch_loss:.4f} '
              f'Train Acc: {train_acc:.4f} Test Acc: {test_acc:.4f}')
        scheduler.step()

    # 绘制曲线
    plt.figure(figsize=(12, 4))
    plt.subplot(1, 2, 1)
    plt.plot(train_losses, label='Training Loss')
    plt.title('Training Loss Curve')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(train_accuracies, label='Training Accuracy')
    plt.plot(test_accuracies, label='Testing Accuracy')
    plt.title('Accuracy Curve')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.legend()

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    torch.multiprocessing.freeze_support()

    # 设置较低的内存限制
    os.environ['OMP_NUM_THREADS'] = '1'
    # 我的电脑没有GPU
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

    main()



