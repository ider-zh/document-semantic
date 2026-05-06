# 什么是学习？

I compress, therefore I am.

--Anonymous+

# 摘要

所罗门诺夫在1964年发表了被后人称为所罗门诺夫归纳法（Solomonoff Induction）的重要工作。所罗门诺夫归纳法可以被视为广义学习机制。它可以被当作大语言模型的理论基础，可以解释GPT的核心机制next token prediction。最后，本文还讨论了SKC理论在人工智能领域中可能的应用以及哲学涵义。

# 1. 背景

我们由此总结出一种新的三个世界模型如下如所示。

<image id="1"/>

美国最原创的哲学家皮尔士（Charles Sanders Peirce，1839-1914）创立的实效主义（pragmatism，汉语一般译为“实用主义”，

<formula id="1">P _ {M} (x) = \sum_ {i = 0} ^ {\infty} 2 ^ {- | S _ {i} (x) |}</formula>

# 2. 历史：柯尔莫哥罗夫与复杂性

所罗门诺夫归纳法可以如下定义：给定序列<formula id="2">( \mathsf { x } _ { 1 } , \mathsf { x } _ { 2 } , \ldots , \mathsf { x } _ { \mathsf { n } } )</formula>）, 预测<formula id="3">x _ { n + 1 0 }</formula>。归纳推理就是力图找到一个最小的图灵机，可以为<formula id="4">( \mathsf { x } _ { 1 } , \mathsf { x } _ { 2 } , \ldots , \mathsf { x } _ { \mathsf { n } } )</formula>）建模，从而准确地预测后续序列。序列的描述长度就是图灵机的大小，这其实就是麦卡锡最初模糊地意识到的“有效”。例如，如果一个序列是<formula id="5">\mathsf { n }</formula>个1: （1, 1, 1,…）,那么我们可以写出如下程序输出该序列:

<code id="1"/>

这个序列的描述长度就是O(log(n))。

# 3. 历史：蔡廷与随机性

他独立地把所罗门诺夫归纳法和柯尔莫哥罗夫信息量的思想又以新的方式重新发明了一遍。审稿人已经知道柯尔莫哥罗夫的工作并告知蔡廷，他不懂俄文，但还是在论文发表时以脚注形式承认了柯氏的工作（见Chaitin-1966）。

<image id="2">所罗门诺夫与蔡廷，2003</image>

蔡廷的出发点是贝里悖论（Berry Paradox）。贝里悖论用英文说就是"The smallest positive integer not definable in under sixty letters"，用中文说是“不可能用少于十九个汉字命名的最小正整数”。这是一种命名悖论。因为贝里悖论和所用的语言载体有关，蔡廷于是决定用函数式编程语言LISP以避免混淆。所谓命名一个整数就是给出一个可以输出这个整数的程序。蔡廷的命名就是柯尔莫哥罗夫的描述。

# 4. 所罗门诺夫归纳与一种新的三个世界哲学

所罗门诺夫归纳法的科普版或者哲学版（philosophical formulation）可描述如下：

1. 观察结果以数据方式输入归纳过程.
2. 形成新假设以解释目前所有的数据. 假设就是图灵机。
3. 新的数据输入，检测数据是否证实假设。
4. 如果数据证伪假设，返回第 2 步。

5. 如果数据证实假设，持续接受假设，并返回第3步。

所罗门诺夫最重要文章（Solomonoff, 1964）的3.2节讨论了在科学哲学中的应用，这节名为“模型形式的系统解释被观察宇宙中所有规律”（SYSTEM IN THE FORM OF A MODEL TO ACCOUNT FOR ALL REGULARITIES IN THE OBSERVED UNIVERSe），其中有言“已发现的科学定律可被看作是关于宇宙的大量经验数据的总结。”（The laws of science that have been discovered can be viewed as summaries of large amounts of empirical data about the universe.） 观察数据和科学理论之间的关系类似于输出数据与程序的关系。换句话说，科学理论/假设/程序就是从观察数据中总结出来的规律。

# 5. 历史：列文与通用搜索过程

列文的L-search在柯尔莫哥罗夫复杂性的基础上加了一个时间的限制，可定义如下:

<formula id="6">\operatorname {K t} (\mathrm {x}) = \min  \left\{\ell (\mathrm {p}) + \log (\text {t i m e} (\mathrm {p})) \colon \mathrm {U} (\mathrm {p}) = \mathrm {x} \right\}</formula>

这样列文的复杂性就是可计算的了，也就是说，如果逆函数存在，总可以通过列文的通用搜索过程找到。这和所罗门诺夫更早获得的收敛性定理契合。

<image id="3"/>

列文1973年文章第二页。参考文献前是一句鸣谢，鸣谢前即是定理2的陈述。

鸣谢. 作者受惠于同李明老师的讨论，本文写作过程还得到白硕、刘卓军、马少平、毛德操和赵伟等诸位师友的指点和帮助，特此感谢。

# 参考文献

1. Bennett, Charles H. (1988), "Logical Depth and Physical Complexity", in Herken, Rolf (ed.), The Universal Turing Machine: a Half-Century Survey, Oxford U. Press, pp. 227–25
2. Bennett, Charles H，Peter Gacs, Ming Li, Paul Vitanyi & Wojciech H. Zurek (1993), “Thermodynamics of Computation and Information Distance”, STOC, 1993
3. Calude C.S. (2007), (ed.) Randomness and Complexity, from Leibniz to Chaitin
