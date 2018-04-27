from torch.utils.data import Dataset
from functools import reduce
import numpy as np

class Data(Dataset):

    def __init__(self, noise=0.001, capacity = np.inf):
        super(Data, self).__init__()
        self.noise = noise
        self.capacity = capacity
        self.data_pushed = 0
        self.transitions = []
        self.statistics_need_calculating = True
    
    def pushTrajectory(self, trajectory):
        # trajectory is s0, a0, r0, s1, a1, r1.... r_{T-1}, S_T
        for state_idx in range(3, len(trajectory), 3):
            state = np.array(trajectory[state_idx-3], dtype = 'float32')
            action = np.array(trajectory[state_idx-2], dtype = 'float32')
            reward = float(trajectory[state_idx - 1])
            next_state = np.array(trajectory[state_idx], dtype = 'float32')
            transition = np.array([state, action, reward, next_state-state])
            self.pushTransition(transition)
    
    def pushTransition(self, transition):
        # transition is [state, action, reward, next_state]
        if len(self.transitions) < self.capacity:
            self.transitions.append(transition)
        else:
            self.transitions[self.data_pushed % self.capacity] = transition
        self.data_pushed+= 1
        self.statistics_need_calculating = True
            
    def calculate_statistics(self):
        if self.statistics_need_calculating:
            # check these statistics are as expected...
            self.means = [i for i in np.mean(self.transitions, 0)]
            self.stds = [np.clip(np.sqrt(i), 10e-9, np.inf) for i in np.var(self.transitions, 0)]
            self.statistics_need_calculating = False
    
    def __len__(self):
        return len(self.transitions)
    
    def __getitem__(self, idx):
        if idx >= self.__len__():
            return None
        transition = self.transitions[idx]
        transition = self.normalise_transition(transition)
        transition = self.add_noise(transition)
        transition = self.typecast(transition)
        return [*transition]
    
    def add_noise(self, transition):
        for i in [0, 1, 3]:
            transition[i] = transition[i] + np.random.normal(0, self.noise, transition[i].shape)
        return transition
        
    def normalise_transition(self, transition):
        self.calculate_statistics()
        transition = (transition - self.means)/self.stds
        return transition
    
    def typecast(self, transition):
        for i in [0, 1, 3]:
            transition[i] = np.array(transition[i], dtype='float32') 
        return transition
    
    def __add__(self, data):
        new_data = Data(capacity = data.capacity + self.capacity)
        new_data.data_pushed = data.data_pushed + self.data_pushed
        new_data.transitions = self.transitions + data.transitions
        return new_data
    
class AggregatedData(Dataset):
    
    def __init__(self, datasets, probabilities = None):
        super(AggregatedData, self).__init__()
        self.D = reduce((lambda x,y:x+y), datasets) # adds all the datasets together
        self.D.calculate_statistics()
        self.datasets = datasets
        self.calculate_statistics()
        self.n = len(datasets)
        if probabilities is None:
            probabilities = [1/self.n for _ in range(self.n)]
        self.probabilities = probabilities
    
    def calculate_statistics(self):
        for data in self.datasets:
            data.means = self.D.means
            data.stds = self.D.stds
            data.statistics_need_calculating = False
        self.means = self.D.means
        self.stds = self.D.stds
    
    def __len__(self):
        return self.D.__len__()
    
    def __getitem__(self, idx):
        dataset = []
        dataset_idx = np.random.choice(list(range(self.n)), p = self.probabilities)
        dataset = self.datasets[dataset_idx]
        idx = np.random.randint(0, len(dataset))
        return dataset[idx]
    
if __name__ == '__main__':
    data = Data(capacity = 5)
    get_array = lambda x : np.random.random((x,))
    trajectory = [get_array(2), get_array(3), 5, 
                  get_array(2), get_array(3), 2,
                  get_array(2)]
    data.pushTrajectory(trajectory)
    data.calculate_statistics()
    data[0]
    data2 = Data()
    data2.pushTrajectory(trajectory)
    data3 = AggregatedData([data, data2])
    data3[0]