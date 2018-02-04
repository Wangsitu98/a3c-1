import threading
import multiprocessing
import argparse
import cv2
import gym
import copy
import os
import time
import numpy as np
import tensorflow as tf

from lightsaber.tensorflow.util import initialize
from lightsaber.tensorflow.log import TfBoardLogger
from actions import get_action_space
from network import make_network
from agent import Agent
from worker import Worker
from datetime import datetime

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', type=str, default='PongDeterministic-v4')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--threads', type=int, default=8)
    parser.add_argument('--final-step', type=int, default=10 ** 7)
    parser.add_argument('--load', type=str)
    parser.add_argument('--log', type=str, default=datetime.now().strftime('%Y%m%d%H%M%S'))
    args = parser.parse_args()

    sess = tf.Session()
    sess.__enter__()

    model = make_network(
        [[16, 8, 4, 0], [32, 4, 2, 0]])

    env_name = args.env
    actions = get_action_space(env_name)
    master = Agent(model, len(actions), final_step=args.final_step, name='global')

    global_step = tf.Variable(0, dtype=tf.int64, name='global_step')

    global_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, 'global')
    saver = tf.train.Saver(global_vars)
    if args.load:
        saver.restore(sess, args.load)

    workers = []
    for i in range(args.threads):
        render = False
        if args.render and i == 0:
            render = True
        worker = Worker('worker{}'.format(i), model,
                global_step, env_name, args.final_step, render=render)
        workers.append(worker)

    logdir = os.path.join(os.path.dirname(__file__), 'logs/{}'.format(args.log))
    summary_writer = tf.summary.FileWriter(logdir, sess.graph)

    logger = TfBoardLogger(summary_writer)
    logger.register('reward', dtype=tf.int8)

    if args.render:
        sample_worker = workers.pop(0)

    initialize()

    coord = tf.train.Coordinator()
    threads = []
    for i in range(len(workers)):
        worker_thread = lambda: workers[i].run(sess, saver, logger)
        thread = threading.Thread(target=worker_thread)
        thread.start()
        threads.append(thread)
        time.sleep(0.1)

    if args.render:
        sample_worker.run(sess, saver, logger)

    coord.join(threads)

if __name__ == '__main__':
    main()
