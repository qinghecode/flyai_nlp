# coding=utf-8
# author=yphacker

import numpy as np
import argparse
import tensorflow as tf
from flyai.dataset import Dataset
from model import Model
from path import MODEL_PATH, LOG_PATH

# 超参
vocab_size = 18781  # 总词汇量
embedding_dim = 64  # 嵌入层大小
hidden_dim = 128  # Dense层大小
max_seq_len = 33  # 最大句长
num_filters = 256  # 卷积核数目
kernel_size = 5  # 卷积核尺寸
learning_rate = 1e-3  # 学习率
numclass = 2  # 类别数

# 传值空间
input_x = tf.placeholder(tf.int32, shape=[None, max_seq_len], name='input_x')
input_y = tf.placeholder(tf.int32, shape=[None, numclass], name='input_y')
keep_prob = tf.placeholder(tf.float32, name='keep_prob')

# define embedding layer
with tf.variable_scope('embedding'):
    # 标准正态分布初始化
    input_embedding = tf.Variable(
        tf.truncated_normal(shape=[vocab_size, embedding_dim], stddev=0.1),
        name='encoder_embedding')

with tf.name_scope("cnn"):
    # CNN layer
    x_input_embedded = tf.nn.embedding_lookup(input_embedding, input_x)
    conv = tf.layers.conv1d(x_input_embedded, num_filters, kernel_size, name='conv')
    # global max pooling layer
    pooling = tf.reduce_max(conv, reduction_indices=[1], name='gmp')

with tf.name_scope("score"):
    # 全连接层，后面接dropout以及relu激活
    fc = tf.layers.dense(pooling, hidden_dim, name='fc1')
    fc = tf.contrib.layers.dropout(fc, keep_prob)
    fc = tf.nn.relu(fc)

    # 分类器
    logits = tf.layers.dense(fc, numclass, name='fc2')
    y_pred_cls = tf.argmax(tf.nn.softmax(logits), 1, name='y_pred')  # 预测类别

with tf.name_scope("optimize"):
    # 损失函数，交叉熵
    cross_entropy = tf.nn.softmax_cross_entropy_with_logits(logits=logits, labels=input_y)
    loss = tf.reduce_mean(cross_entropy)
    # 优化器
    train_op = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(loss)

with tf.name_scope("accuracy"):
    # 准确率
    correct_pred = tf.equal(tf.argmax(input_y, 1), y_pred_cls)
    accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32), name='acc')


# best_score = 0
# with tf.Session() as sess:
#     sess.run(tf.global_variables_initializer())
#     train_writer = tf.summary.FileWriter(LOG_PATH, sess.graph)
#
#     # dataset.get_step() 获取数据的总迭代次数
#     for step in range(dataset.get_step()):
#         x_train, y_train = dataset.next_train_batch()
#         x_val, y_val = dataset.next_validation_batch()
#
#         fetches = [loss, accuracy, train_op]
#         feed_dict = {input_x: x_train, input_y: y_train, keep_prob: 1.0}
#         loss_, accuracy_, _ = sess.run(fetches, feed_dict=feed_dict)
#
#         summary = sess.run(merged_summary, feed_dict=feed_dict)
#         train_writer.add_summary(summary, step)
#         cur_step = str(step + 1) + "/" + str(dataset.get_step())
#         print('The Current step per total: {} | The Current loss: {} | The Current ACC: {}'.
#               format(cur_step, loss_, accuracy_))
#         if step % 100 == 0:
#             model.save_model(sess, MODEL_PATH, overwrite=True)

def evaluate(sess):
    x_val, y_val = dataset.get_all_validation_data()
    data_len = len(y_val)
    index = np.random.permutation(len(y_val))
    batch_len = 64
    n_batches = len(y_val) // batch_len + 1
    total_loss = 0.0
    total_acc = 0.0
    for batch_index in np.array_split(index, n_batches):
        feed_dict = {input_x: x_val[batch_index], input_y: y_val[batch_index], keep_prob: 1}
        _loss, _acc = sess.run([loss, accuracy], feed_dict=feed_dict)
        total_loss += _loss * batch_len
        total_acc += _acc * batch_len
    return total_loss / data_len, total_acc / data_len


print_per_batch = 50
best_acc_val = 0
with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())

    print('dataset.get_step:', dataset.get_step())
    for step in range(dataset.get_step()):
        x_train, y_train = dataset.next_train_batch()

        if step % print_per_batch == 0:
            fetches = [loss, accuracy]
            feed_dict = {input_x: x_train, input_y: y_train, keep_prob: 1}
            loss_train, acc_train = sess.run(fetches, feed_dict=feed_dict)
            loss_val, acc_val = evaluate(sess)
            if acc_val >= best_acc_val:
                best_acc_val = acc_val
                model.save_model(sess, MODEL_PATH, overwrite=True)
                improved_str = '*'
            else:
                improved_str = ''
            cur_step = str(step + 1) + "/" + str(dataset.get_step())
            msg = 'The Current step per total: {0:>6}, Train Loss: {1:>6.2}, Train Acc: {2:>7.2%},' \
                  + ' Val Loss: {3:>6.2}, Val Acc: {4:>7.2%} {5}'
            print(msg.format(cur_step, loss_train, acc_train, loss_val, acc_val, improved_str))
        fetches = [train_op]
        feed_dict = {input_x: x_train, input_y: y_train, keep_prob: 0.5}
        sess.run(fetches, feed_dict=feed_dict)