import numpy as np
import torch

class DQNTrainer:
    def __init__(
        self,
        env,
        model,
        episodes,
        max_steps,
        epsilon,
        alpha,
        gamma,
        buffer,
        batch_size,
        decay,
    ):

        self.env = env
        self.buffer = buffer
        self.model = model

        self.episodes = episodes
        self.max_steps = max_steps
        self.epsilon = epsilon
        self.alpha = alpha
        self.gamma = gamma
        self.decay = decay
        self.buffer=buffer
        self.batch_size=batch_size

        self.training_steps = []
        self.training_cumulative_reward = []
        self.greedy_steps = []
        self.greedy_cumulative_reward = []

        self.criterion = torch.nn.MSELoss()
        self.optimizer = torch.optim.SGD(model.parameters(), lr=alpha)

    def get_random_action(self):
        return self.env.action_space.sample()

    def get_greedy_action(self, state):
        with torch.no_grad():
            state_tensor = torch.tensor(state, dtype=torch.float)
            q_values = self.model.forward(state_tensor)
            action = q_values.abs().argmax().item()
        return action

    def choose_action(self, state):
        if np.random.rand() < self.epsilon:
            return self.get_random_action()
        return self.get_greedy_action(state)

    def update_model(self):
        if len(self.buffer) < self.batch_size:
            return
        
        for sample in self.buffer.sample_batch(self.batch_size):
            self.optimizer.zero_grad()

            q = self.model.forward(sample.state)[sample.action]
            q_next = self.model.forward(sample.next_state).max() if not sample.done else 0
            q_target = sample.reward + self.gamma*q_next

            loss = self.criterion(q, q_target)
            loss.backward()
            self.optimizer.step()

    def run_episode(self, is_train=True, is_greedy=False):
        state = self.env.reset()
        cumulative_reward = 0

        for step in range(self.max_steps):
            action = self.get_greedy_action(state) if is_greedy else self.choose_action(state)
            state_prime, reward, done, _ = self.env.step(action)
            cumulative_reward += reward

            if is_train:
                state_tensor =  torch.tensor(state, dtype=torch.float)
                state_prime_tensor =  torch.tensor(state_prime, dtype=torch.float)
                reward_tensor = torch.tensor(reward, dtype=torch.float)
                self.buffer.push(state_tensor, action, state_prime_tensor, reward_tensor, done)
                self.update_model()

            if done:
                break

            state = state_prime

            if (not is_greedy) & is_train:
                self.epsilon *= self.decay

        return step + 1, cumulative_reward

    def run_training_episode(self):
        n_steps, cumulative_reward = self.run_episode(is_train=True, is_greedy=False)
        self.training_steps.append(n_steps)
        self.training_cumulative_reward.append(cumulative_reward)

    def run_greedy_episode(self):
        n_steps, cumulative_reward = self.run_episode(is_train=False, is_greedy=True)
        self.greedy_steps.append(n_steps)
        self.greedy_cumulative_reward.append(cumulative_reward)

    def run_testing_episode(self):
        return self.run_episode(is_train=False, is_greedy=True)

    def train(self, run_greedy_frequency=None):
        if run_greedy_frequency:
            for episode in range(self.episodes):
                self.run_training_episode()

                if (episode % run_greedy_frequency) == 0:
                    self.run_greedy_episode()
        else:
            for _ in range(self.episodes):
                self.run_training_episode()
