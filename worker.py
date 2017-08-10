import cv2
import gym
import copy
import os
import numpy as np
import tensorflow as tf

from util import initialize, get_session
from actions import get_action_space
from network import make_network
from agent import Agent

class Worker:
    def __init__(self, name, model, global_step, env_name, render=False, training=True):
        self.training = training
        self.actions = get_action_space(env_name)
        self.env = gym.make(env_name)
        self.name = name
        self.render = render
        self.agent = Agent(model, len(self.actions), name=name)
        self.global_step = global_step
        self.inc_global_step = global_step.assign_add(1)

    def run(self, sess):
        with sess.as_default():
            local_step = 0

            while True:
                states = np.zeros((4, 84, 84), dtype=np.float32)
                reward = 0
                done = False
                clipped_reward = 0
                sum_of_rewards = 0
                step = 0
                state = self.env.reset()

                while True:
                    state = cv2.cvtColor(state, cv2.COLOR_RGB2GRAY)
                    state = cv2.resize(state, (84, 84))
                    states = np.roll(states, 1, axis=0)
                    states[0] = state

                    if done:
                        self.agent.stop_episode_and_train(states, clipped_reward, done=done)
                        break

                    if self.training:
                        action_index = self.agent.act_and_train(states, clipped_reward)
                    else:
                        action_index = self.agent.act(states)
                    action = self.actions[action_index]

                    state, reward, done, info = self.env.step(action)
                    if self.render:
                        self.env.render()

                    if reward > 0:
                        clipped_reward = 1
                    elif reward < 0:
                        clipped_reward = -1
                    else:
                        clipped_reward = 0
                    sum_of_rewards += reward
                    step += 1
                    local_step += 1 
                    get_session().run(self.inc_global_step)

                print('worker: {}, global: {}, local: {}, reward: {}'.format(
                        self.name, self.global_step.value().eval(), local_step, sum_of_rewards))