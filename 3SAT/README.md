ADMM 求解含三次项 Ising 模型问题的解决方案说明
一、问题背景与建模
1.1 含三次项的 Ising 模型
我们需要求解的 Ising 模型能量函数包含二次项与三次项，形式如下：
E(q)=fbase​(q)(i,j)∑​Jij​qi​qj​+i∑​hi​qi​​​+fcubic​(q)(i,j,k)∑​Kijk​qi​qj​qk​​​其中 qi​∈{−1,1} 为 Ising 自旋变量，Jij​,hi​ 分别为二次耦合系数与单粒子场，Kijk​ 为三次耦合系数。